import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def analyze_company(self, company_id):
    from apps.companies.models import Company
    from apps.ai_engine.models import AnalysisRequest, AnalysisResult
    from apps.ai_engine.services import CerebrasClient

    try:
        company = Company.objects.select_related('organization').get(id=company_id)
    except Company.DoesNotExist:
        logger.error(f'Company {company_id} not found')
        return {'error': 'Company not found'}

    analysis_request = AnalysisRequest.objects.create(
        company=company,
        organization=company.organization,
        status='processing',
    )

    client = CerebrasClient()
    company_data = {
        'name': company.name,
        'description': company.description,
        'website': company.website,
        'sector': company.sector.name if company.sector else '',
        'city': company.city,
        'state': company.state,
    }

    result = client.analyze_company(company_data)

    if (not result.get('is_potential_client')
            and company.score >= 20
            and company.detected_sector):
        logger.info(
            f'Company {company_id} rescatada por preclasificación: '
            f'score={company.score}, sector={company.detected_sector}'
        )
        result['is_potential_client'] = True
        result['score'] = max(result.get('score', 0), company.score)
        result['priority'] = 'media'

    if 'error' in result:
        analysis_request.status = 'error'
        analysis_request.error_message = result['error']
        analysis_request.processing_time = result.get('processing_time')
        analysis_request.save()

        company.status = 'error'
        company.save(update_fields=['status'])
        return {'error': result['error']}

    with transaction.atomic():
        analysis_request.status = 'completed'
        analysis_request.raw_response = result.get('raw_json')
        analysis_request.processing_time = result.get('processing_time')
        analysis_request.save()

        AnalysisResult.objects.create(
            analysis_request=analysis_request,
            company=company,
            score=result.get('score', 0),
            is_potential_client=result.get('is_potential_client', False),
            detected_sector=result.get('detected_sector', ''),
            recommended_products=result.get('recommended_products', []),
            reason=result.get('reason', ''),
            priority=result.get('priority', 'media'),
            summary=result.get('summary', ''),
            raw_json=result.get('raw_json'),
        )

        company.score = result.get('score', 0)
        company.detected_sector = result.get('detected_sector', '')
        company.status = 'analyzed'
        company.is_lead = result.get('is_potential_client', False)
        company.save(update_fields=['score', 'detected_sector', 'status', 'is_lead'])

    from apps.leads.models import Lead
    Lead.objects.update_or_create(
        company=company,
        defaults={
            'organization': company.organization,
            'score': result.get('score', 0),
            'is_potential_client': result.get('is_potential_client', False),
            'priority': result.get('priority', 'media'),
            'detected_sector': result.get('detected_sector', ''),
            'recommended_products': ', '.join(result.get('recommended_products', [])),
            'analysis_summary': result.get('summary', ''),
            'reason': result.get('reason', ''),
        }
    )

    return {
        'company_id': company_id,
        'score': result.get('score'),
        'is_potential_client': result.get('is_potential_client'),
    }
