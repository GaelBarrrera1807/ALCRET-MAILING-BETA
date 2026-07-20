import csv
import io
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List
from urllib.parse import urlparse

from celery import shared_task
from django.db import transaction

from apps.scraping.models import ScrapingJob, ScrapedData
from apps.scraping.services import ScrapingService

logger = logging.getLogger(__name__)


@shared_task(name='run_scraping_job')
def run_scraping_job(job_id: str) -> Dict[str, Any]:
    logger.info(f'Iniciando trabajo de scraping {job_id}')

    from apps.core.models import Company

    try:
        job = ScrapingJob.objects.prefetch_related('companies').get(id=job_id)
    except ScrapingJob.DoesNotExist:
        logger.error(f'ScrapingJob {job_id} no encontrado en base de datos')
        return {'error': 'Job no encontrado'}

    service: ScrapingService = ScrapingService()
    job.status = 'processing'
    job.save(update_fields=['status'])

    try:
        company = job.companies.first()

        if job.job_type in ('social', 'enrichment'):
            clean_data: Dict[str, Any] = service.run_external_scraping(job_id)

            if company and clean_data.get('contacts'):
                service.enrich_company_contacts(
                    str(company.id), clean_data
                )

            scraped: ScrapedData = ScrapedData.objects.filter(
                company=company,
                source='apify',
                data_type='external_api',
                raw_data__isnull=False,
                processed_data__isnull=True,
            ).last()

            if scraped:
                scraped.processed_data = clean_data
                scraped.save(update_fields=['processed_data'])

            job.result = clean_data

        elif job.job_type == 'website' and job.url:
            result: Dict[str, Any] = service.scrape_website(job.url)

            if 'error' not in result:
                ScrapedData.objects.create(
                    company=company,
                    source=job.url,
                    data_type='website',
                    raw_data=result,
                    processed_data=result,
                )

                if company:
                    if result.get('description') and not company.description:
                        company.description = result['description'][:2000]
                    if result.get('emails'):
                        existing = set(
                            e.strip()
                            for e in company.email.split(';')
                            if e.strip()
                        )
                        existing.update(result['emails'])
                        company.email = ';'.join(existing)
                    if result.get('phones'):
                        existing = set(
                            p.strip()
                            for p in company.phone.split(';')
                            if p.strip()
                        )
                        existing.update(result['phones'])
                        company.phone = ';'.join(existing)
                    company.save(
                        update_fields=['description', 'email', 'phone']
                    )

            job.result = result

        elif job.job_type == 'MAPS_DISCOVERY' and job.url:
            parts = job.url.replace('maps:', '').split('|')
            sq = parts[0] if len(parts) > 0 else ''
            loc = parts[1] if len(parts) > 1 else ''
            lim = int(parts[2]) if len(parts) > 2 else 50
            org_id = str(job.organization_id) if job.organization_id else None
            return discover_companies_from_maps(
                sq, loc, limit=lim,
                organization_id=org_id, job_id=str(job.id),
            )

        elif job.job_type == 'phone' and company:
            result: Dict[str, Any] = service.scrape_website(company.website or '')

            if 'error' not in result:
                ScrapedData.objects.create(
                    company=company,
                    source=company.website or company.email,
                    data_type='phone',
                    raw_data=result,
                    processed_data=result,
                )

                if result.get('phones'):
                    existing = set(
                        p.strip()
                        for p in company.phone.split(';')
                        if p.strip()
                    )
                    existing.update(result['phones'])
                    company.phone = ';'.join(existing)
                    company.save(update_fields=['phone'])

            job.result = result

        else:
            raise ValueError(
                f'Tipo de trabajo no soportado: {job.job_type}'
            )

        if isinstance(job.result, dict) and 'error' in job.result:
            job.status = 'error'
            job.error_message = job.result['error']
        else:
            job.status = 'completed'

        job.save(update_fields=['status', 'result', 'error_message'])
        logger.info(
            f'Scraping job {job_id} finalizado: status={job.status}'
        )
        return {'job_id': str(job_id), 'status': job.status}

    except Exception as exc:
        try:
            job.refresh_from_db()
        except ScrapingJob.DoesNotExist:
            logger.error(
                f'ScrapingJob {job_id} eliminado durante la ejecución'
            )
            return {'error': 'Job eliminado'}

        job.status = 'error'
        job.error_message = str(exc)[:500]
        job.result = job.result or {}
        job.save(update_fields=['status', 'error_message', 'result'])
        logger.exception(
            f'Scraping job {job_id} falló con excepción: {exc}'
        )
        return {'error': str(exc)}


def _maps_results_to_csv_bytes(
    results: List[Dict[str, Any]], location: str
) -> bytes:
    output = io.StringIO()
    output.write('\ufeff')
    fieldnames = [
        'name', 'description', 'website', 'phone', 'address',
        'city', 'state', 'country', 'latitude', 'longitude',
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for item in results:
        name = item.get('title') or item.get('name') or ''
        cats = item.get('categories') or []
        cat_str = ' '.join(cats) if isinstance(cats, list) else str(cats)
        desc = (
            item.get('categoryName')
            or item.get('description')
            or item.get('category')
            or cat_str
            or ''
        )
        website = item.get('website') or ''
        phone = item.get('phone') or item.get('phoneUnformatted') or ''
        address = item.get('address') or ''
        lat = item.get('location', {}).get('lat') if isinstance(item.get('location'), dict) else item.get('latitude')
        lng = item.get('location', {}).get('lng') if isinstance(item.get('location'), dict) else item.get('longitude')
        writer.writerow({
            'name': name.strip(),
            'description': f'{desc} {cat_str}'.strip(),
            'website': website.strip(),
            'phone': phone.strip(),
            'address': address.strip(),
            'city': location.strip(),
            'state': item.get('state', ''),
            'country': 'México',
            'latitude': lat or '',
            'longitude': lng or '',
        })
    return output.getvalue().encode('utf-8')


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def discover_companies_from_maps(
    self, search_query: str, location: str, limit: int = 50,
    organization_id: str = None, job_id: str = None,
) -> Dict[str, Any]:
    logger.info(
        f'Lead Finder: discover_companies_from_maps iniciado — '
        f'query="{search_query}", location="{location}", limit={limit}'
    )
    if job_id:
        try:
            job = ScrapingJob.objects.get(id=job_id)
            job.status = 'processing'
            job.save(update_fields=['status'])
        except ScrapingJob.DoesNotExist:
            logger.error(f'Lead Finder: job {job_id} no encontrado, creando nuevo')
            job = ScrapingJob.objects.create(
                organization_id=organization_id,
                job_type='MAPS_DISCOVERY',
                url=f'maps:{search_query} {location}',
                status='processing',
            )
    else:
        job = ScrapingJob.objects.create(
            organization_id=organization_id,
            job_type='MAPS_DISCOVERY',
            url=f'maps:{search_query} {location}',
            status='processing',
        )
    try:
        service = ScrapingService()
        maps_result = service.discover_from_google_maps(
            search_query, location, limit
        )
        raw_results = maps_result.get('results', [])
        if not raw_results:
            job.status = 'completed'
            job.result = {
                'search_query': search_query,
                'location': location,
                'total_raw': 0,
                'created': 0,
                'note': 'Sin resultados de Google Maps',
            }
            job.save(update_fields=['status', 'result'])
            logger.info(f'Lead Finder: sin resultados para "{search_query} {location}"')
            return job.result

        csv_bytes = _maps_results_to_csv_bytes(raw_results, location)
        filename = f'maps_{search_query[:30]}_{location[:20]}.csv'

        from apps.preprocessing.models import PreprocessingRule
        from apps.preprocessing.services.pipeline import PreprocessingPipeline

        db_rules = list(
            PreprocessingRule.objects.filter(
                is_active=True
            ).values('id', 'name', 'rule_type', 'keywords', 'weight')
        ) if PreprocessingRule.objects.filter(is_active=True).exists() else []

        pipeline = PreprocessingPipeline(
            threshold=12, db_rules=db_rules, use_ai_fallback=True,
        )
        pipeline_result = pipeline.process(filename, csv_bytes)

        if pipeline_result.error:
            job.status = 'error'
            job.error_message = pipeline_result.error
            job.save(update_fields=['status', 'error_message'])
            logger.error(f'Lead Finder: pipeline error — {pipeline_result.error}')
            return {
                'search_query': search_query,
                'location': location,
                'status': 'error',
                'error': pipeline_result.error,
            }

        from apps.core.models import Company, CompanyContact

        raw_by_name = {}
        for item in raw_results:
            name = (item.get('name') or item.get('title') or '').strip().lower()
            if name:
                raw_by_name[name] = item
            else:
                address = item.get('address', '') or item.get('location', {}).get('address', '') or ''
                if address:
                    raw_by_name[address.strip().lower()] = item

        # ── Phase 1: Create all companies (fast, no external API) ──
        created = 0
        errors = 0
        company_ids = []
        companies_data = []
        snov_targets = []  # (company, domain, is_sql, rec_score, priority, sector) for parallel enrichment

        for record in pipeline_result.relevant:
            try:
                name = record.get('_name', '') or record.get('name', '')
                if not name:
                    errors += 1
                    continue

                priority = record.get('_preprocess_priority', '')
                rec_score = record.get('_preprocess_score', 0)
                is_sql = priority in ('alta', 'high', 'sql') or rec_score >= 60
                sector = record.get('_preprocess_industry', '')

                orig = raw_by_name.get(name.strip().lower(), {})
                address = orig.get('address', '') or record.get('address', '')

                loc = orig.get('location', {})
                if isinstance(loc, dict):
                    lat = loc.get('lat')
                    lng = loc.get('lng')
                else:
                    lat = orig.get('latitude') or orig.get('lat')
                    lng = orig.get('longitude') or orig.get('lng')

                categories = (
                    orig.get('categories')
                    or orig.get('subtypes')
                    or orig.get('categoryName')
                    or []
                )
                if isinstance(categories, str):
                    categories = [categories]
                elif not isinstance(categories, list):
                    categories = []

                oh = orig.get('openingHours') or {}
                if not isinstance(oh, dict):
                    oh = {}

                images = (
                    orig.get('titleAndReviewImages')
                    or orig.get('imageUrl')
                    or orig.get('image')
                    or []
                )
                photo = None
                if isinstance(images, list):
                    for img in images:
                        if isinstance(img, dict):
                            photo = img.get('reviewImageUrl') or img.get('titleImageUrl')
                        elif isinstance(img, str):
                            photo = img
                        if photo:
                            break
                elif isinstance(images, str):
                    photo = images

                google_rating = (
                    orig.get('totalScore')
                    or orig.get('stars')
                    or orig.get('rating')
                )
                google_reviews_count = (
                    orig.get('reviewsCount')
                    or orig.get('reviews')
                    or orig.get('reviewCount')
                )

                company = Company.objects.create(
                    name=name,
                    description=record.get('_description', '') or record.get('description', ''),
                    website=orig.get('website', '') or record.get('website', ''),
                    phone=orig.get('phone', '') or orig.get('phoneUnformatted', '') or record.get('phone', ''),
                    address=address,
                    city=location.strip(),
                    country='México',
                    latitude=lat or None,
                    longitude=lng or None,
                    google_rating=google_rating or None,
                    google_reviews_count=google_reviews_count or None,
                    maps_categories=categories,
                    opening_hours=oh,
                    main_photo_url=photo,
                    organization_id=organization_id,
                    source='MAPS_DISCOVERY',
                    status='pending',
                    detected_sector=sector,
                    score=rec_score,
                    scraping_job=job,
                )
                company_ids.append(str(company.id))
                created += 1

                raw_website = orig.get('website', '') or record.get('website', '')
                domain = ''
                if raw_website:
                    candidate = raw_website.strip()
                    if '://' not in candidate:
                        candidate = 'https://' + candidate
                    parsed = urlparse(candidate)
                    domain = parsed.hostname or ''
                    if domain.startswith('www.'):
                        domain = domain[4:]

                snov_targets.append((company, domain, is_sql, rec_score, priority, sector))
            except Exception as e:
                logger.error(f'Lead Finder: error creando Company: {e}')
                errors += 1

        # ── Phase 2: Parallel Snov.io enrichment ──
        snov_enriched_count = 0
        snov_contacts_total = 0
        sql_lead_count = 0
        contact_counts: Dict[str, int] = {}

        def _enrich_company(args):
            company, domain, is_sql, rec_score, priority, sector = args
            if not domain:
                return company, 0
            try:
                snov_result = service.fetch_contacts_by_domain(domain)
                snov_contacts = snov_result.get('contacts', [])
                if not snov_contacts:
                    return company, 0
                with transaction.atomic():
                    has_primary = CompanyContact.objects.filter(
                        company=company, is_primary=True
                    ).exists()
                    for contact in snov_contacts:
                        full_name = (
                            f"{contact.get('first_name', '')} "
                            f"{contact.get('last_name', '')}"
                        ).strip()
                        if not full_name:
                            full_name = contact.get('email', '').split('@')[0]
                        CompanyContact.objects.create(
                            company=company,
                            name=full_name,
                            position=contact.get('position', ''),
                            email=contact.get('email', ''),
                            is_primary=not has_primary,
                        )
                        if not has_primary:
                            has_primary = True
                return company, len(snov_contacts)
            except Exception as e:
                logger.error(f'Snov.io error for {company.name}: {e}')
                return company, 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_enrich_company, t): t for t in snov_targets}
            for future in as_completed(futures):
                company, count = future.result()
                contact_counts[str(company.id)] = count
                if count > 0:
                    snov_enriched_count += 1
                    snov_contacts_total += count

        # ── Phase 3: Async lead creation for SQL companies ──
        for company, domain, is_sql, rec_score, priority, sector in snov_targets:
            contact_count = contact_counts.get(str(company.id), 0)
            companies_data.append({
                'id': str(company.id),
                'name': company.name,
                'score': rec_score,
                'sector': sector,
                'website': company.website,
                'contacts_count': contact_count,
                'latitude': company.latitude,
                'longitude': company.longitude,
                'google_rating': company.google_rating,
                'google_reviews_count': company.google_reviews_count,
                'maps_categories': company.maps_categories,
                'main_photo_url': company.main_photo_url,
            })
            if is_sql:
                first_contact = CompanyContact.objects.filter(
                    company=company
                ).order_by('-is_primary', 'created_at').first()
                from apps.leads.tasks import create_lead_from_classification
                create_lead_from_classification.delay(
                    str(company.id),
                    score=rec_score,
                    priority=priority,
                    detected_sector=sector,
                    contact_id=str(first_contact.id) if first_contact else None,
                    organization_id=organization_id,
                    analysis_summary='',
                    reason='SQL - Lead Finder Google Maps',
                    auto_enroll_campaign=True,
                )
                sql_lead_count += 1

        ScrapedData.objects.create(
            company=None,
            source='google_maps',
            data_type='MAPS_DISCOVERY_raw',
            raw_data={
                'search_query': search_query,
                'location': location,
                'results': raw_results,
            },
            processed_data={
                'pipeline_stats': pipeline_result.stats,
                'companies_created': company_ids,
                'snov_enriched_count': snov_enriched_count,
                'snov_contacts_total': snov_contacts_total,
            },
        )

        credits_consumed = snov_enriched_count * 15
        if credits_consumed > 0:
            job.credits_consumed = credits_consumed

        if created > 0 and organization_id:
            from apps.ai_engine.tasks import analyze_company
            for i, cid in enumerate(company_ids):
                analyze_company.apply_async(args=[cid], countdown=i * 30)

        job.status = 'completed'
        job.result = {
            'search_query': search_query,
            'location': location,
            'total_raw': len(raw_results),
            'pipeline_total': pipeline_result.total_records,
            'pipeline_relevant': pipeline_result.relevant_records,
            'pipeline_filtered': pipeline_result.filtered_records,
            'created': created,
            'errors': errors,
            'company_ids': [str(cid) for cid in company_ids],
            'sql_leads_created': sql_lead_count,
            'snov_enriched_count': snov_enriched_count,
            'snov_contacts_total': snov_contacts_total,
            'credits_consumed': credits_consumed,
            'companies': companies_data,
        }
        job.save(update_fields=['status', 'result', 'credits_consumed'])
        logger.info(
            f'Lead Finder completado: {created} empresas creadas, '
            f'{sql_lead_count} SQL leads, '
            f'{snov_enriched_count} enriquecidas con Snov.io '
            f'({snov_contacts_total} contactos), {credits_consumed} créditos'
        )
        return job.result

    except Exception as exc:
        try:
            job.refresh_from_db()
        except ScrapingJob.DoesNotExist:
            pass
        job.status = 'error'
        job.error_message = str(exc)[:500]
        job.result = job.result or {
            'search_query': search_query,
            'location': location,
            'error': str(exc)[:500],
        }
        job.save(update_fields=['status', 'error_message', 'result'])
        logger.exception(f'Lead Finder: error fatal — {exc}')
        return {
            'search_query': search_query,
            'location': location,
            'status': 'error',
            'error': str(exc),
        }
