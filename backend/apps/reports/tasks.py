import logging

from celery import shared_task
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def generate_report(self, report_id):
    from apps.reports.models import Report
    from apps.reports.services import ReportService

    try:
        report = Report.objects.get(id=report_id)
    except Report.DoesNotExist:
        logger.error(f'Report {report_id} not found')
        return {'error': 'Report not found'}

    service = ReportService()

    try:
        if report.file_type == 'pdf':
            if report.report_type == 'leads':
                file_content = service.generate_leads_report(report.filters)
            elif report.report_type == 'scoring':
                file_content = service.generate_scoring_report(report.filters)
            else:
                file_content = service.generate_leads_report(report.filters)

            filename = f'{report.report_type}_{report.id}.pdf'
            report.file.save(filename, file_content, save=False)
            report.status = 'completed'
            report.save(update_fields=['file', 'status'])
        elif report.file_type == 'csv':
            if report.report_type == 'leads':
                file_content = service.generate_leads_csv(report.filters)
            elif report.report_type == 'scoring':
                file_content = service.generate_scoring_csv(report.filters)
            else:
                file_content = service.generate_leads_csv(report.filters)

            filename = f'{report.report_type}_{report.id}.csv'
            report.file.save(filename, file_content, save=False)
            report.status = 'completed'
            report.save(update_fields=['file', 'status'])
        else:
            report.status = 'completed'
            report.save(update_fields=['status'])

        return {'report_id': report_id, 'status': 'completed'}
    except Exception as e:
        logger.error(f'Error generating report {report_id}: {e}')
        report.status = 'error'
        report.error_message = str(e)
        report.save(update_fields=['status', 'error_message'])
        return {'error': str(e)}
