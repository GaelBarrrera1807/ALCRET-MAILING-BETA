import logging
import time

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_campaign_task(self, campaign_id):
    from apps.mailer.models import EmailCampaign, CampaignSend
    from apps.mailer.services.mail_service import send_single_email

    try:
        campaign = EmailCampaign.objects.select_related('template').get(id=campaign_id)
    except EmailCampaign.DoesNotExist:
        logger.error(f'EmailCampaign {campaign_id} no encontrada')
        return {'error': 'Campaign not found'}

    if campaign.status not in ('draft', 'scheduled'):
        logger.warning(f'Campaign {campaign_id} en estado {campaign.status}, no se envia')
        return {'status': 'skipped', 'reason': f'Estado: {campaign.status}'}

    campaign.status = 'sending'
    campaign.save(update_fields=['status'])

    pending_sends = CampaignSend.objects.filter(
        campaign=campaign,
        status='pending',
    ).select_related('recipient')

    total = pending_sends.count()
    if total == 0:
        campaign.status = 'sent'
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=['status', 'sent_at'])
        return {'sent': 0, 'total': 0}

    batch_size = getattr(settings, 'EMAIL_RATE_LIMIT', 50)
    batch_pause = getattr(settings, 'EMAIL_BATCH_PAUSE', 1)
    sent_count = 0
    error_count = 0

    send_ids = list(pending_sends.values_list('id', flat=True))

    for i in range(0, len(send_ids), batch_size):
        batch_ids = send_ids[i:i + batch_size]
        batch = CampaignSend.objects.filter(id__in=batch_ids).select_related(
            'recipient', 'campaign', 'campaign__template',
        )

        with transaction.atomic():
            for campaign_send in batch:
                try:
                    success = send_single_email(campaign_send)
                    if success:
                        campaign_send.status = 'sent'
                        campaign_send.save(update_fields=['status'])
                        sent_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    logger.error(f'Error en lote enviando a {campaign_send.recipient.email}: {e}')
                    campaign_send.status = 'bounced'
                    campaign_send.error_message = str(e)[:500]
                    campaign_send.save(update_fields=['status', 'error_message'])
                    error_count += 1

        campaign.refresh_from_db()
        campaign.sent_count = sent_count
        campaign.save(update_fields=['sent_count'])

        remaining = total - (i + batch_size)
        if remaining > 0 and batch_pause > 0:
            logger.info(f'Batch completado: {sent_count} enviados, {error_count} errores. '
                        f'Restan ~{remaining}. Pausa {batch_pause}s...')
            time.sleep(batch_pause)

    campaign.status = 'sent'
    campaign.sent_at = timezone.now()
    campaign.save(update_fields=['status', 'sent_at'])

    logger.info(f'Campaign {campaign_id} completada: {sent_count} enviados, {error_count} errores de {total}')
    return {'sent': sent_count, 'errors': error_count, 'total': total}


@shared_task(bind=True)
def retry_failed_sends(self):
    from apps.mailer.models import CampaignSend, EmailCampaign
    from apps.mailer.services.mail_service import send_single_email

    failed = CampaignSend.objects.filter(
        status='bounced',
        campaign__status='sent',
    ).select_related('recipient', 'campaign', 'campaign__template')[:50]

    retried = 0
    for campaign_send in failed:
        try:
            success = send_single_email(campaign_send)
            if success:
                retried += 1
        except Exception as e:
            logger.error(f'Error retry {campaign_send.id}: {e}')

    if retried:
        logger.info(f'Reintentos: {retried} reenviados')
    return {'retried': retried}
