import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def run_scraping_job(self, job_id):
    from apps.scraping.models import ScrapingJob
    from apps.scraping.services import ScrapingService

    try:
        job = ScrapingJob.objects.select_related('company').get(id=job_id)
    except ScrapingJob.DoesNotExist:
        logger.error(f'ScrapingJob {job_id} not found')
        return {'error': 'Job not found'}

    job.status = 'processing'
    job.save(update_fields=['status'])

    service = ScrapingService()

    if job.job_type == 'website' and job.url:
        result = service.scrape_website(job.url)
    elif job.job_type == 'phone' and job.company:
        result = service.scrape_phone(job.company)
    elif job.job_type == 'social' and job.company:
        result = service.scrape_social(job.company)
    elif job.job_type == 'enrichment' and job.company:
        result = service.scrape_enrichment(job.company)
    else:
        result = {'error': f'Unsupported job type: {job.job_type}'}

    if 'error' in result:
        job.status = 'error'
        job.error_message = result['error']
        job.result = result
        job.save(update_fields=['status', 'error_message', 'result'])
        return {'error': result['error']}

    job.status = 'completed'
    job.result = result
    job.save(update_fields=['status', 'result'])

    if job.company:
        company = job.company
        if result.get('description') and not company.description:
            company.description = result['description'][:2000]
        if result.get('emails'):
            existing = set(e.strip() for e in company.email.split(';') if e.strip())
            existing.update(result['emails'])
            company.email = ';'.join(existing)
        if result.get('phones'):
            existing = set(p.strip() for p in company.phone.split(';') if p.strip())
            existing.update(result['phones'])
            company.phone = ';'.join(existing)
        company.save(update_fields=['description', 'email', 'phone'])

    return {'job_id': job_id, 'status': 'completed'}
