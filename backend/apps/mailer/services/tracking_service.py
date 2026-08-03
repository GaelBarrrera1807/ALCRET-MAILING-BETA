import base64
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

from django.db import transaction
from django.db.models import F

from apps.mailer.models import CampaignSend, EmailEvent, EmailCampaign

logger = logging.getLogger(__name__)

TRACKING_URL = '/api/mailer/track'

TRANSPARENT_1X1_GIF_B64 = (
    'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
)


def generate_tracking_pixel():
    return base64.b64decode(TRANSPARENT_1X1_GIF_B64)


def _parse_tracking_id(tracking_id_str):
    try:
        from uuid import UUID
        return UUID(tracking_id_str)
    except (ValueError, AttributeError):
        logger.error(f'Tracking ID invalido: {tracking_id_str}')
        return None


@transaction.atomic
def process_open(tracking_id_str, metadata=None):
    tracking_id = _parse_tracking_id(tracking_id_str)
    if not tracking_id:
        return None

    try:
        campaign_send = CampaignSend.objects.select_for_update().get(tracking_id=tracking_id)
    except CampaignSend.DoesNotExist:
        logger.warning(f'Tracking ID no encontrado para open: {tracking_id_str}')
        return None

    now = datetime.now(timezone.utc)

    if campaign_send.opened_at is None:
        campaign_send.status = 'opened'
        campaign_send.opened_at = now
        campaign_send.save(update_fields=['status', 'opened_at'])

        EmailCampaign.objects.filter(id=campaign_send.campaign_id).update(open_count=F('open_count') + 1)

    EmailEvent.objects.create(
        campaign_send=campaign_send,
        event_type='open',
        user_agent=(metadata or {}).get('user_agent', ''),
        ip_address=(metadata or {}).get('ip_address'),
        metadata=metadata or {},
    )

    logger.info(f'Open registrado: {tracking_id_str}')
    return campaign_send


@transaction.atomic
def process_click(tracking_id_str, target_url, metadata=None):
    tracking_id = _parse_tracking_id(tracking_id_str)
    if not tracking_id:
        return None

    try:
        campaign_send = CampaignSend.objects.select_for_update().get(tracking_id=tracking_id)
    except CampaignSend.DoesNotExist:
        logger.warning(f'Tracking ID no encontrado para click: {tracking_id_str}')
        return None

    now = datetime.now(timezone.utc)

    if campaign_send.clicked_at is None:
        campaign_send.status = 'clicked'
        campaign_send.clicked_at = now
        campaign_send.save(update_fields=['status', 'clicked_at'])

        EmailCampaign.objects.filter(id=campaign_send.campaign_id).update(click_count=F('click_count') + 1)

    EmailEvent.objects.create(
        campaign_send=campaign_send,
        event_type='click',
        url=target_url,
        user_agent=(metadata or {}).get('user_agent', ''),
        ip_address=(metadata or {}).get('ip_address'),
        metadata=metadata or {},
    )

    logger.info(f'Click registrado: {tracking_id_str} -> {target_url}')
    return campaign_send


@transaction.atomic
def process_bounce(tracking_id_str, reason='', metadata=None):
    tracking_id = _parse_tracking_id(tracking_id_str)
    if not tracking_id:
        return None

    try:
        campaign_send = CampaignSend.objects.select_for_update().get(tracking_id=tracking_id)
    except CampaignSend.DoesNotExist:
        logger.warning(f'Tracking ID no encontrado para bounce: {tracking_id_str}')
        return None

    campaign_send.status = 'bounced'
    campaign_send.error_message = reason[:500]
    campaign_send.save(update_fields=['status', 'error_message'])

    EmailCampaign.objects.filter(id=campaign_send.campaign_id).update(bounce_count=F('bounce_count') + 1)

    EmailEvent.objects.create(
        campaign_send=campaign_send,
        event_type='bounce',
        metadata={'reason': reason, **(metadata or {})},
    )

    logger.info(f'Bounce registrado: {tracking_id_str} - {reason}')
    return campaign_send


@transaction.atomic
def process_unsubscribe(tracking_id_str, metadata=None):
    tracking_id = _parse_tracking_id(tracking_id_str)
    if not tracking_id:
        return None

    try:
        campaign_send = CampaignSend.objects.select_for_update().get(tracking_id=tracking_id)
    except CampaignSend.DoesNotExist:
        logger.warning(f'Tracking ID no encontrado para unsubscribe: {tracking_id_str}')
        return None

    recipient = campaign_send.recipient
    recipient.is_active = False
    recipient.unsubscribed_at = datetime.now(timezone.utc)
    recipient.save(update_fields=['is_active', 'unsubscribed_at'])

    campaign_send.status = 'unsubscribed'
    campaign_send.save(update_fields=['status'])

    EmailCampaign.objects.filter(id=campaign_send.campaign_id).update(unsubscribe_count=F('unsubscribe_count') + 1)

    EmailEvent.objects.create(
        campaign_send=campaign_send,
        event_type='unsubscribe',
        metadata=metadata or {},
    )

    logger.info(f'Unsubscribe registrado: {tracking_id_str}')
    return campaign_send


@transaction.atomic
def process_delivery(tracking_id_str, metadata=None):
    tracking_id = _parse_tracking_id(tracking_id_str)
    if not tracking_id:
        return None

    try:
        campaign_send = CampaignSend.objects.select_for_update().get(tracking_id=tracking_id)
    except CampaignSend.DoesNotExist:
        logger.warning(f'Tracking ID no encontrado para delivery: {tracking_id_str}')
        return None

    if campaign_send.status in ('pending', 'sent'):
        campaign_send.status = 'delivered'
        campaign_send.save(update_fields=['status'])

    logger.info(f'Delivery registrado: {tracking_id_str}')
    return campaign_send


@transaction.atomic
def process_complaint(tracking_id_str, metadata=None):
    tracking_id = _parse_tracking_id(tracking_id_str)
    if not tracking_id:
        return None

    try:
        campaign_send = CampaignSend.objects.select_for_update().get(tracking_id=tracking_id)
    except CampaignSend.DoesNotExist:
        logger.warning(f'Tracking ID no encontrado para complaint: {tracking_id_str}')
        return None

    recipient = campaign_send.recipient
    recipient.is_active = False
    recipient.unsubscribed_at = datetime.now(timezone.utc)
    recipient.save(update_fields=['is_active', 'unsubscribed_at'])

    campaign_send.status = 'complained'
    campaign_send.save(update_fields=['status'])

    EmailCampaign.objects.filter(id=campaign_send.campaign_id).update(unsubscribe_count=F('unsubscribe_count') + 1)

    EmailEvent.objects.create(
        campaign_send=campaign_send,
        event_type='complaint',
        metadata=metadata or {},
    )

    logger.info(f'Complaint registrado: {tracking_id_str}')
    return campaign_send


def find_campaign_send_by_ses_message_id(message_id):
    if not message_id:
        return None
    return CampaignSend.objects.filter(ses_message_id=message_id).select_related('recipient').first()


def process_ses_notification(notification):
    notification_type = (notification or {}).get('notificationType')
    mail = (notification or {}).get('mail', {}) or {}
    message_id = mail.get('messageId')

    if not message_id:
        logger.warning('Notificación SES sin mail.messageId')
        return None

    campaign_send = find_campaign_send_by_ses_message_id(message_id)
    if not campaign_send:
        logger.warning(f'Notificación SES para messageId no registrado: {message_id}')
        return None

    tracking_id = str(campaign_send.tracking_id)

    if notification_type == 'Bounce':
        bounce = notification.get('bounce', {}) or {}
        bounce_type = bounce.get('bounceType', '')
        reason = bounce.get('bounceSubType', '')
        process_bounce(tracking_id, reason=reason, metadata=notification)
        if bounce_type == 'Permanent':
            recipient = campaign_send.recipient
            recipient.is_active = False
            recipient.save(update_fields=['is_active'])
        return {'event': 'bounce', 'bounce_type': bounce_type, 'campaign_send_id': str(campaign_send.id)}

    if notification_type == 'Complaint':
        process_complaint(tracking_id, metadata=notification)
        return {'event': 'complaint', 'campaign_send_id': str(campaign_send.id)}

    if notification_type == 'Delivery':
        process_delivery(tracking_id, metadata=notification)
        return {'event': 'delivery', 'campaign_send_id': str(campaign_send.id)}

    logger.info(f'notificationType no manejado: {notification_type}')
    return {'event': notification_type, 'ignored': True}
