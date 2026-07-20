import base64
import json
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_preprocessing(self, filename, file_content, threshold=30, job_id=None,
                       organization_id=None, use_ai_fallback=False,
                       auto_enrich_sql=False, **kwargs):
    from apps.preprocessing.models import PreprocessingJob, PreprocessingRule
    from apps.preprocessing.services.pipeline import PreprocessingPipeline

    if kwargs:
        logger.warning('run_preprocessing received unexpected kwargs: %s', kwargs)

    job = None

    try:
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

        # ── Calculate credits consumed ──
        # Basic: each row read = 1 credit
        credits_basic = result.total_records
        # AI: each row evaluated by Cerebras borderline = 5 additional credits
        credits_ai = sum(1 for r in result.relevant if r.get('_ai_reason', '')) * 5
        # Scraping: each SQL record auto-enriched = 15 additional credits
        enriched_count = 0

        # ── Auto-enrich SQL records ──
        if auto_enrich_sql and result.relevant:
            from apps.core.models import Company, CompanyContact
            from apps.scraping.models import ScrapingJob

            for record in result.relevant:
                priority = record.get('_preprocess_priority', '')
                score = record.get('_preprocess_score', 0)
                is_sql = priority in ('alta', 'high', 'sql') or score >= 60
                if not is_sql:
                    continue
                name = record.get('_name', '') or record.get('name', '')
                if not name:
                    continue
                try:
                    company = Company.objects.create(
                        name=name,
                        description=record.get('_description', '') or record.get('description', ''),
                        website=record.get('website', ''),
                        email=record.get('email', ''),
                        phone=record.get('phone', ''),
                        address=record.get('address', ''),
                        city=record.get('city', ''),
                        state=record.get('state', ''),
                        country=record.get('country', 'México'),
                        rfc=record.get('rfc', ''),
                        organization_id=organization_id or (job.organization_id if job_id else None),
                        source=filename,
                        status='pending',
                        detected_sector=record.get('_preprocess_industry', ''),
                        score=score,
                    )
                    contact_name = record.get('contact_name', '')
                    contact = None
                    if contact_name:
                        contact = CompanyContact.objects.create(
                            company=company,
                            name=contact_name,
                            email=record.get('contact_email', ''),
                            phone=record.get('contact_phone', ''),
                            is_primary=True,
                        )
                    # ── Bridge: SQL → Lead + Mailer ──
                    from apps.leads.tasks import create_lead_from_classification
                    create_lead_from_classification(
                        str(company.id),
                        score=score,
                        priority=priority,
                        detected_sector=record.get('_preprocess_industry', ''),
                        contact_id=str(contact.id) if contact else None,
                        organization_id=str(company.organization_id) if company.organization_id else None,
                        analysis_summary='',
                        reason='SQL - alta prioridad (auto-enrich)',
                        auto_enroll_campaign=True,
                    )
                    scraping_job = ScrapingJob.objects.create(
                        company=company,
                        organization=company.organization,
                        job_type='enrichment',
                        status='pending',
                    )
                    from apps.scraping.tasks import run_scraping_job as run_scraping
                    run_scraping.delay(str(scraping_job.id))
                    enriched_count += 1
                except Exception as e:
                    logger.error(f'Auto-enrich error for {name}: {e}')

        credits_consumed = credits_basic + credits_ai + (enriched_count * 15)

        job.total_records = result.total_records
        job.relevant_records = result.relevant_records
        job.filtered_records = result.filtered_records
        job.processing_time = result.processing_time
        job.credits_consumed = credits_consumed

        job.stats_json = {
            'total': result.stats.get('total', 0),
            'relevant': result.stats.get('relevant', 0),
            'discarded': result.stats.get('discarded', 0),
            'threshold': result.stats.get('threshold', threshold),
            'avg_score': result.stats.get('avg_score', 0),
            'by_priority': result.stats.get('by_priority', {}),
            'credits_consumed': credits_consumed,
            'enriched_count': enriched_count,
        }

        job.status = PreprocessingJob.Status.COMPLETED

        if result.cleaned_file_path:
            from django.core.files.base import File
            import os
            with open(result.cleaned_file_path, 'rb') as f:
                job.cleaned_file.save(
                    f'preprocessed_{filename}',
                    File(f),
                    save=True,
                )
            try:
                os.unlink(result.cleaned_file_path)
            except OSError:
                pass
        else:
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
            'credits_consumed': credits_consumed,
            'enriched_count': enriched_count,
        }

    except Exception as e:
        logger.exception(f'run_preprocessing failed: {e}')
        if job:
            try:
                job.status = PreprocessingJob.Status.ERROR
                job.error_message = str(e)
                job.save(update_fields=['status', 'error_message'])
            except Exception as save_err:
                logger.exception(f'Failed to save job error state: {save_err}')
        return {
            'job_id': str(job.id) if job else None,
            'status': 'error',
            'error': str(e),
        }


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_with_preprocessing(self, filename, file_content, sector_id=None,
                                organization_id=None, user_id=None, threshold=30,
                                use_ai_fallback=False, **kwargs):
    from apps.core.models import Company, CompanyContact
    from apps.preprocessing.models import PreprocessingRule
    from apps.preprocessing.services.pipeline import PreprocessingPipeline

    if kwargs:
        logger.warning('process_with_preprocessing received unexpected kwargs: %s', kwargs)

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

        from apps.core.models import Sector
        sector = None
        if sector_id:
            try:
                sector = Sector.objects.get(id=sector_id)
            except Sector.DoesNotExist:
                pass

        created = 0
        errors = 0
        company_ids = []
        sql_lead_count = 0
        original_columns = list(result.records[0].keys()) if result.records else []

        for record in result.relevant:
            try:
                name = record.get('name', '')
                if not name:
                    errors += 1
                    continue

                priority = record.get('_preprocess_priority', '')
                rec_score = record.get('_preprocess_score', 0)
                is_sql = priority in ('alta', 'high', 'sql') or rec_score >= 60

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
                    'score': rec_score,
                })

                contact = None
                contact_name = record.get('contact_name', '')
                if contact_name:
                    contact = CompanyContact.objects.create(
                        company=company,
                        name=contact_name,
                        email=record.get('contact_email', ''),
                        phone=record.get('contact_phone', ''),
                        is_primary=True,
                    )

                company_ids.append(company.id)
                created += 1

                # ── Auto-create Lead for SQL records ──
                if is_sql:
                    from apps.leads.tasks import create_lead_from_classification
                    create_lead_from_classification(
                        str(company.id),
                        score=rec_score,
                        priority=priority,
                        detected_sector=record.get('_preprocess_industry', ''),
                        contact_id=str(contact.id) if contact else None,
                        organization_id=organization_id,
                        analysis_summary='',
                        reason='SQL - alta prioridad',
                        auto_enroll_campaign=True,
                    )
                    sql_lead_count += 1

            except Exception as e:
                logger.error(f'Error creating company: {e}')
                errors += 1

        if sql_lead_count:
            logger.info(f'Created {sql_lead_count} SQL leads from pipeline')

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
            'sql_leads_created': sql_lead_count,
        }

    except Exception as e:
        logger.exception(f'process_with_preprocessing failed: {e}')
        return {
            'created': 0, 'errors': 0,
            'total': 0, 'filtered': 0,
            'error': str(e),
        }
