import logging
from datetime import datetime, timezone

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import F

from apps.mailer.models import CampaignSend, EmailCampaign
from apps.mailer.services.template_service import render_template
from apps.mailer.services.tracking_service import TRACKING_URL

logger = logging.getLogger(__name__)


def send_single_email(campaign_send):
    try:
        campaign = campaign_send.campaign
        recipient = campaign_send.recipient
        template = campaign.template

        if not template:
            logger.error(f'Campaign {campaign.id} no tiene template asignado')
            campaign_send.status = 'bounced'
            campaign_send.error_message = 'Sin template asignado'
            campaign_send.save(update_fields=['status', 'error_message'])
            return False

        if not recipient.email:
            logger.warning(f'Recipient {recipient.id} sin email')
            campaign_send.status = 'bounced'
            campaign_send.error_message = 'Destinatario sin email'
            campaign_send.save(update_fields=['status', 'error_message'])
            return False

        context = {
            'first_name': recipient.first_name,
            'company': recipient.company_name,
            'sector': recipient.sector,
            'email': recipient.email,
            'tracking_id': str(campaign_send.tracking_id),
            'unsubscribe_url': f'{settings.BASE_URL}/mailer/unsubscribe/{campaign_send.tracking_id}/',
        }

        rendered = render_template(template, context)
        subject = campaign.subject or rendered['subject']
        body_html = campaign.body_html or rendered['body_html']

        tracking_pixel_url = f'{settings.BASE_URL}{TRACKING_URL}/open/{campaign_send.tracking_id}/'
        body_html_with_pixel = f'{body_html}<img src="{tracking_pixel_url}" alt="" width="1" height="1" style="display:none;" />'

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'prospeccion@industrialprospecting.com')
        to_email = [recipient.email]

        msg = EmailMultiAlternatives(
            subject=subject,
            body='',
            from_email=from_email,
            to=to_email,
            headers={
                'X-Campaign-ID': str(campaign.id),
                'X-Tracking-ID': str(campaign_send.tracking_id),
                'List-Unsubscribe': f'<{context["unsubscribe_url"]}>',
            },
        )
        msg.attach_alternative(body_html_with_pixel, 'text/html')

        msg.send(fail_silently=False)

        now = datetime.now(timezone.utc)
        campaign_send.status = 'sent'
        campaign_send.sent_at = now
        campaign_send.save(update_fields=['status', 'sent_at'])

        EmailCampaign.objects.filter(id=campaign.id).update(sent_count=F('sent_count') + 1)

        logger.info(f'Email enviado a {recipient.email} (tracking: {campaign_send.tracking_id})')
        return True

    except Exception as e:
        logger.error(f'Error enviando email a {campaign_send.recipient.email}: {e}', exc_info=True)
        campaign_send.status = 'bounced'
        campaign_send.error_message = str(e)[:500]
        campaign_send.save(update_fields=['status', 'error_message'])
        return False
