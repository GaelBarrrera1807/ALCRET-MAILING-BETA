import base64
import json
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_preprocessing(self, filename, file_content, threshold=30, job_id=None,
                       organization_id=None, use_ai_fallback=False):
    from apps.preprocessing.models import PreprocessingJob, PreprocessingRule
    from apps.preprocessing.services.pipeline import PreprocessingPipeline

    if job_id:
        job = PreprocessingJob.objects.get(id=job_id)
        job.status = PreprocessingJob.Status.PROCESSING
        job.save(update_fields=['status'])
    else:
        job = PreprocessingJob.objects.create(
            organization_id=organization_id,
            original_filename=filename,
            status=PreprocessingJob.Status.PROCESSING,
            scoring_threshold=threshold,
        )

    try:
        file_bytes = base64.b64decode(file_content)
        db_rules = list(
            PreprocessingRule.objects.filter(
                is_active=True
            ).values('id', 'name', 'rule_type', 'keywords', 'weight')
        ) if PreprocessingRule.objects.filter(is_active=True).exists() else []

        pipeline = PreprocessingPipeline(
            threshold=threshold, db_rules=db_rules, use_ai_fallback=use_ai_fallback,
        )
        result = pipeline.process(filename, file_bytes)

        if result.error:
            job.status = PreprocessingJob.Status.ERROR
            job.error_message = result.error
            job.save(update_fields=['status', 'error_message', 'processing_time'])
            return {
                'job_id': str(job.id),
                'status': 'error',
                'error': result.error,
            }

        job.total_records = result.total_records
        job.relevant_records = result.relevant_records
        job.filtered_records = result.filtered_records
        job.processing_time = result.processing_time

        job.stats_json = {
            'total': result.stats.get('total', 0),
            'relevant': result.stats.get('relevant', 0),
            'discarded': result.stats.get('discarded', 0),
            'threshold': result.stats.get('threshold', threshold),
            'avg_score': result.stats.get('avg_score', 0),
            'by_priority': result.stats.get('by_priority', {}),
        }

        if result.cleaned_file_path:
            from django.core.files.base import File
            import os
            with open(result.cleaned_file_path, 'rb') as f:
                job.cleaned_file.save(
                    f'preprocessed_{filename}',
                    File(f),
                    save=False,
                )
            try:
                os.unlink(result.cleaned_file_path)
            except OSError:
                pass

        job.status = PreprocessingJob.Status.COMPLETED
        job.save()

        return {
            'job_id': str(job.id),
            'status': 'completed',
            'total': result.total_records,
            'relevant': result.relevant_records,
            'filtered': result.filtered_records,
            'threshold': threshold,
            'processing_time': result.processing_time,
            'stats': job.stats_json,
        }

    except Exception as e:
        logger.exception(f'Preprocessing job {job.id} failed: {e}')
        job.status = PreprocessingJob.Status.ERROR
        job.error_message = str(e)
        job.save(update_fields=['status', 'error_message'])
        return {
            'job_id': str(job.id),
            'status': 'error',
            'error': str(e),
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_with_preprocessing(self, filename, file_content, sector_id=None,
                                organization_id=None, user_id=None, threshold=30,
                                use_ai_fallback=False):
    from apps.companies.models import Company, CompanyContact
    from apps.preprocessing.models import PreprocessingRule
    from apps.preprocessing.services.pipeline import PreprocessingPipeline

    try:
        file_bytes = base64.b64decode(file_content)
        db_rules = list(
            PreprocessingRule.objects.filter(
                is_active=True
            ).values('id', 'name', 'rule_type', 'keywords', 'weight')
        ) if PreprocessingRule.objects.filter(is_active=True).exists() else []

        pipeline = PreprocessingPipeline(
            threshold=threshold, db_rules=db_rules, use_ai_fallback=use_ai_fallback,
        )
        result = pipeline.process(filename, file_bytes)

        if result.error:
            logger.error(f'Preprocessing failed for {filename}: {result.error}')
            return {
                'created': 0, 'errors': 0, 'total': 0,
                'filtered': 0, 'error': result.error,
            }

        if not result.relevant:
            logger.info(f'No relevant records found in {filename}')
            return {
                'created': 0, 'errors': 0,
                'total': result.total_records,
                'filtered': result.filtered_records,
                'message': 'No relevant records found',
            }

        from apps.companies.models import Sector
        sector = None
        if sector_id:
            try:
                sector = Sector.objects.get(id=sector_id)
            except Sector.DoesNotExist:
                pass

        created = 0
        errors = 0
        company_ids = []
        original_columns = list(result.records[0].keys()) if result.records else []

        for record in result.relevant:
            try:
                name = record.get('name', '')
                if not name:
                    errors += 1
                    continue

                company = Company.objects.create(**{
                    'name': name,
                    'description': record.get('description', ''),
                    'website': record.get('website', ''),
                    'email': record.get('email', ''),
                    'phone': record.get('phone', ''),
                    'address': record.get('address', ''),
                    'city': record.get('city', ''),
                    'state': record.get('state', ''),
                    'country': record.get('country', 'México'),
                    'rfc': record.get('rfc', ''),
                    'sector': sector,
                    'organization_id': organization_id,
                    'source': filename,
                    'status': 'pending',
                    'detected_sector': record.get('_preprocess_industry', ''),
                    'score': record.get('_preprocess_score', 0),
                })

                contact_name = record.get('contact_name', '')
                if contact_name:
                    CompanyContact.objects.create(
                        company=company,
                        name=contact_name,
                        email=record.get('contact_email', ''),
                        phone=record.get('contact_phone', ''),
                        is_primary=True,
                    )

                company_ids.append(company.id)
                created += 1

            except Exception as e:
                logger.error(f'Error creating company: {e}')
                errors += 1

        if created > 0 and user_id:
            logger.info(
                f'Queuing Cerebras analysis for {created} preprocessed companies'
            )
            from apps.ai_engine.tasks import analyze_company
            for cid in company_ids:
                analyze_company.delay(cid)

        return {
            'created': created,
            'errors': errors,
            'total': result.total_records,
            'filtered': result.filtered_records,
            'relevant': result.relevant_records,
            'threshold': threshold,
            'avg_score': result.stats.get('avg_score', 0),
        }

    except Exception as e:
        logger.exception(f'process_with_preprocessing failed: {e}')
        return {
            'created': 0, 'errors': 0,
            'total': 0, 'filtered': 0,
            'error': str(e),
        }
