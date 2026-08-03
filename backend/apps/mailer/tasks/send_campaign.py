import logging

from celery import chord, shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_single_email_task(self, campaign_send_id):
    from apps.mailer.models import CampaignSend
    from apps.mailer.services.mail_service import send_single_email

    try:
        campaign_send = CampaignSend.objects.select_related(
            'campaign', 'campaign__template', 'recipient',
        ).get(id=campaign_send_id)
    except CampaignSend.DoesNotExist:
        logger.error(f'CampaignSend {campaign_send_id} no encontrado')
        return {'error': 'CampaignSend not found'}

    if self.request.retries == 0 and campaign_send.status != 'pending':
        logger.info(f'CampaignSend {campaign_send_id} en estado {campaign_send.status}, se omite')
        return {'status': 'skipped', 'reason': f'Estado: {campaign_send.status}'}

    sent = send_single_email(campaign_send)
    if sent:
        return {'campaign_send_id': campaign_send_id, 'sent': True}

    if self.request.retries < self.max_retries:
        logger.warning(
            f'CampaignSend {campaign_send_id} falló, reintento '
            f'{self.request.retries + 1}/{self.max_retries}: {campaign_send.error_message}'
        )
        raise self.retry(countdown=30 * (self.request.retries + 1))

    return {'campaign_send_id': campaign_send_id, 'sent': False, 'error': campaign_send.error_message}


@shared_task(bind=True)
def finalize_campaign_task(self, results, campaign_id):
    from apps.mailer.models import EmailCampaign, CampaignSend

    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        logger.error(f'EmailCampaign {campaign_id} no encontrada')
        return {'error': 'Campaign not found'}

    remaining = CampaignSend.objects.filter(campaign=campaign, status='pending').count()
    campaign.status = 'sent' if remaining == 0 else 'sending'
    update_fields = ['status']
    if remaining == 0:
        campaign.sent_at = timezone.now()
        update_fields.append('sent_at')
    campaign.save(update_fields=update_fields)

    logger.info(f'Campaign {campaign_id} finalizada: {campaign.sent_count} enviados, {remaining} pendientes')
    return {'campaign_id': str(campaign_id), 'status': campaign.status, 'remaining': remaining}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_campaign_task(self, campaign_id):
    from apps.mailer.models import EmailCampaign, CampaignSend

    try:
        campaign = EmailCampaign.objects.select_related('template').get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        logger.error(f'EmailCampaign {campaign_id} no encontrada')
        return {'error': 'Campaign not found'}

    if campaign.status not in ('draft', 'scheduled'):
        logger.warning(f'Campaign {campaign_id} en estado {campaign.status}, no se envía')
        return {'status': 'skipped', 'reason': f'Estado: {campaign.status}'}

    campaign.status = 'sending'
    campaign.save(update_fields=['status'])

    send_ids = list(
        CampaignSend.objects.filter(campaign=campaign, status='pending').values_list('id', flat=True)
    )
    total = len(send_ids)
    if total == 0:
        campaign.status = 'sent'
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=['status', 'sent_at'])
        return {'sent': 0, 'total': 0}

    dispatch_interval = getattr(settings, 'EMAIL_DISPATCH_INTERVAL', 0.0)
    tasks = []
    for idx, campaign_send_id in enumerate(send_ids):
        signature = send_single_email_task.si(campaign_send_id)
        if dispatch_interval > 0:
            signature = signature.set(countdown=idx * dispatch_interval)
        tasks.append(signature)

    chord(tasks)(finalize_campaign_task.s(campaign.id))

    logger.info(f'Campaign {campaign_id}: {total} tareas individuales encoladas')
    return {'dispatched': total, 'campaign_id': str(campaign.id)}


@shared_task(bind=True)
def retry_failed_sends(self):
    from apps.mailer.models import CampaignSend

    failed_ids = list(
        CampaignSend.objects.filter(
            status='bounced',
            campaign__status='sent',
        ).values_list('id', flat=True)[:50]
    )

    for campaign_send_id in failed_ids:
        send_single_email_task.delay(campaign_send_id)

    if failed_ids:
        logger.info(f'Reintentos encolados: {len(failed_ids)}')
    return {'retried': len(failed_ids)}