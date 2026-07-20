import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.mailer.models import (
    EmailTemplate, EmailRecipient, EmailCampaign,
    CampaignSend, EmailEvent,
)
from apps.mailer.services.template_service import render_template
from apps.users.models import Organization

User = get_user_model()


class BaseTest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name='Test Org')
        self.user = User.objects.create_user(
            username='testuser', password='testpass123',
            organization=self.org,
        )
        self._auth()

    def _auth(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'testpass123',
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')

    def _create_template(self, **kwargs):
        defaults = {
            'organization': self.org,
            'name': 'Plantilla Test',
            'template_type': 'cold_outreach',
            'subject': 'Hola {{ first_name }}',
            'body_html': '<p>Hola <strong>{{ first_name }}</strong>, bienvenido {{ company }}.</p>',
            'variables': ['first_name', 'company', 'sector'],
        }
        defaults.update(kwargs)
        return EmailTemplate.objects.create(**defaults)

    def _create_recipient(self, **kwargs):
        defaults = {
            'organization': self.org,
            'email': 'test@example.com',
            'first_name': 'Juan',
            'company_name': 'Empresa Test',
            'sector': 'Transporte',
            'source': 'manual',
        }
        defaults.update(kwargs)
        return EmailRecipient.objects.create(**defaults)

    def _create_campaign(self, **kwargs):
        template = self._create_template()
        defaults = {
            'organization': self.org,
            'name': 'Campaña Test',
            'template': template,
            'source_filter': 'all',
        }
        defaults.update(kwargs)
        return EmailCampaign.objects.create(**defaults)


class EmailTemplateTests(BaseTest):
    def test_create_template(self):
        response = self.client.post('/api/mailer/templates/', {
            'name': 'Nueva Plantilla',
            'template_type': 'cold_outreach',
            'subject': 'Oferta {{ first_name }}',
            'body_html': '<p>Hola {{ first_name }}</p>',
            'variables': ['first_name', 'company'],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Nueva Plantilla')

    def test_list_templates(self):
        self._create_template()
        response = self.client.get('/api/mailer/templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_render_template(self):
        template = self._create_template()
        context = {'first_name': 'Carlos', 'company': 'Logística SA'}
        result = render_template(template, context)
        self.assertIn('Carlos', result['body_html'])
        self.assertIn('Logística SA', result['body_html'])
        self.assertEqual(result['subject'], 'Hola Carlos')

    def test_preview_template(self):
        template = self._create_template()
        response = self.client.post(f'/api/mailer/templates/{template.id}/preview/', {
            'context': {'first_name': 'Ana', 'company': 'Constructora XYZ'},
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Ana', response.data['body_html'])

    def test_template_sanitizes_html(self):
        template = self._create_template(
            body_html='<p>Hola</p><script>alert("xss")</script>',
        )
        context = {'first_name': 'Test'}
        result = render_template(template, context)
        self.assertNotIn('<script>', result['body_html'])
        self.assertIn('<p>Hola</p>', result['body_html'])

    def test_update_template(self):
        template = self._create_template()
        response = self.client.patch(f'/api/mailer/templates/{template.id}/', {
            'name': 'Plantilla Actualizada',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Plantilla Actualizada')


class EmailRecipientTests(BaseTest):
    def test_create_recipient(self):
        response = self.client.post('/api/mailer/recipients/', {
            'email': 'contacto@ejemplo.com',
            'first_name': 'María',
            'source': 'manual',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'contacto@ejemplo.com')

    def test_duplicate_email_rejected(self):
        self._create_recipient(email='dup@example.com')
        response = self.client.post('/api/mailer/recipients/', {
            'email': 'dup@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_recipients(self):
        self._create_recipient()
        response = self.client.get('/api/mailer/recipients/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_unsubscribe_sets_inactive(self):
        recipient = self._create_recipient()
        response = self.client.delete(f'/api/mailer/recipients/{recipient.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        recipient.refresh_from_db()
        self.assertFalse(recipient.is_active)
        self.assertIsNotNone(recipient.unsubscribed_at)

    def test_bulk_create(self):
        response = self.client.post('/api/mailer/recipients/bulk/', {
            'recipients': ['a@test.com', 'b@test.com', 'c@test.com'],
            'source': 'manual',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created'], 3)

    def test_bulk_skips_duplicates(self):
        self._create_recipient(email='a@test.com')
        response = self.client.post('/api/mailer/recipients/bulk/', {
            'recipients': ['a@test.com', 'new@test.com'],
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['created'], 1)
        self.assertEqual(response.data['skipped'], 1)

    def test_filter_by_source(self):
        self._create_recipient(email='a@test.com', source='csv_upload')
        self._create_recipient(email='b@test.com', source='manual')
        response = self.client.get('/api/mailer/recipients/?source=manual')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_is_active(self):
        self._create_recipient(email='active@test.com', is_active=True)
        r2 = self._create_recipient(email='inactive@test.com', is_active=False)
        response = self.client.get('/api/mailer/recipients/?is_active=false')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['email'], r2.email)


class EmailCampaignTests(BaseTest):
    def test_create_campaign(self):
        template = self._create_template()
        response = self.client.post('/api/mailer/campaigns/', {
            'name': 'Campaña de Prueba',
            'template': str(template.id),
            'source_filter': 'all',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Campaña de Prueba')

    def test_list_campaigns(self):
        self._create_campaign()
        response = self.client.get('/api/mailer/campaigns/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    @patch('apps.mailer.tasks.send_campaign.send_campaign_task.delay')
    def test_send_campaign_creates_sends(self, mock_delay):
        campaign = self._create_campaign()
        self._create_recipient(email='destino@test.com')
        self._create_recipient(email='otro@test.com')

        response = self.client.post(f'/api/mailer/campaigns/{campaign.id}/send/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_recipients'], 2)
        mock_delay.assert_called_once_with(str(campaign.id))

        campaign.refresh_from_db()
        self.assertEqual(campaign.total_recipients, 2)
        self.assertEqual(campaign.status, 'scheduled')

    def test_send_campaign_rejects_non_draft(self):
        campaign = self._create_campaign()
        campaign.status = 'sent'
        campaign.save(update_fields=['status'])
        response = self.client.post(f'/api/mailer/campaigns/{campaign.id}/send/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_campaign_rejects_no_template(self):
        campaign = EmailCampaign.objects.create(
            organization=self.org, name='Sin Template',
        )
        response = self.client.post(f'/api/mailer/campaigns/{campaign.id}/send/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_campaign_no_recipients(self):
        campaign = self._create_campaign()
        response = self.client.post(f'/api/mailer/campaigns/{campaign.id}/send/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_campaign_stats(self):
        campaign = self._create_campaign()
        CampaignSend.objects.create(
            campaign=campaign,
            recipient=self._create_recipient(email='s1@test.com'),
            status='sent',
        )
        CampaignSend.objects.create(
            campaign=campaign,
            recipient=self._create_recipient(email='s2@test.com'),
            status='opened',
        )
        response = self.client.get(f'/api/mailer/campaigns/{campaign.id}/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('by_status', response.data)

    @patch('apps.mailer.tasks.send_campaign.send_campaign_task.delay')
    def test_send_campaign_filter_all(self, mock_delay):
        campaign = self._create_campaign(source_filter='manual')
        self._create_recipient(email='manual@test.com', source='manual')
        self._create_recipient(email='csv@test.com', source='csv_upload')
        response = self.client.post(f'/api/mailer/campaigns/{campaign.id}/send/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_recipients'], 1)


class CeleryTaskTests(BaseTest):
    @patch('apps.mailer.services.mail_service.send_single_email')
    def test_send_campaign_task_executes(self, mock_send):
        from apps.mailer.tasks.send_campaign import send_campaign_task

        campaign = self._create_campaign()
        r1 = self._create_recipient(email='a@test.com')
        r2 = self._create_recipient(email='b@test.com')

        CampaignSend.objects.create(campaign=campaign, recipient=r1)
        CampaignSend.objects.create(campaign=campaign, recipient=r2)

        mock_send.return_value = True
        result = send_campaign_task(str(campaign.id))

        self.assertEqual(result['sent'], 2)
        self.assertEqual(result['total'], 2)

        campaign.refresh_from_db()
        self.assertEqual(campaign.status, 'sent')

    @patch('apps.mailer.services.mail_service.send_single_email')
    def test_send_campaign_handles_errors(self, mock_send):
        from apps.mailer.tasks.send_campaign import send_campaign_task

        campaign = self._create_campaign()
        r = self._create_recipient(email='error@test.com')
        CampaignSend.objects.create(campaign=campaign, recipient=r)

        mock_send.side_effect = Exception('SMTP error')
        result = send_campaign_task(str(campaign.id))

        self.assertEqual(result['errors'], 1)

    def test_retry_failed_sends(self):
        from apps.mailer.tasks.send_campaign import retry_failed_sends

        campaign = self._create_campaign()
        campaign.status = 'sent'
        campaign.save(update_fields=['status'])

        r = self._create_recipient(email='fail@test.com')
        CampaignSend.objects.create(
            campaign=campaign, recipient=r, status='bounced',
        )
        result = retry_failed_sends()
        self.assertIn('retried', result)


class TrackingTests(BaseTest):
    def test_tracking_pixel_returns_gif(self):
        campaign = self._create_campaign()
        recipient = self._create_recipient()
        cs = CampaignSend.objects.create(campaign=campaign, recipient=recipient)

        self.client.logout()
        response = self.client.get(f'/api/mailer/track/open/{cs.tracking_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/gif')

        cs.refresh_from_db()
        self.assertEqual(cs.status, 'opened')
        self.assertIsNotNone(cs.opened_at)

    def test_tracking_click_redirects(self):
        campaign = self._create_campaign()
        recipient = self._create_recipient()
        cs = CampaignSend.objects.create(campaign=campaign, recipient=recipient)

        self.client.logout()
        target = 'https://ejemplo.com/producto'
        response = self.client.get(
            f'/api/mailer/track/click/{cs.tracking_id}/',
            {'url': target},
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.url, target)

        cs.refresh_from_db()
        self.assertEqual(cs.status, 'clicked')
        self.assertIsNotNone(cs.clicked_at)

    def test_tracking_creates_email_event(self):
        campaign = self._create_campaign()
        recipient = self._create_recipient()
        cs = CampaignSend.objects.create(campaign=campaign, recipient=recipient)

        self.client.get(f'/api/mailer/track/open/{cs.tracking_id}/')
        events = EmailEvent.objects.filter(campaign_send=cs, event_type='open')
        self.assertEqual(events.count(), 1)

    def test_tracking_unknown_id_returns_200(self):
        self.client.logout()
        response = self.client.get(f'/api/mailer/track/open/{uuid.uuid4()}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'image/gif')


class EmailDeliveryTests(BaseTest):
    @patch('apps.mailer.services.mail_service.send_single_email')
    def test_email_is_sent_via_celery(self, mock_send):
        from apps.mailer.tasks.send_campaign import send_campaign_task

        campaign = self._create_campaign()
        recipient = self._create_recipient()
        cs = CampaignSend.objects.create(campaign=campaign, recipient=recipient)

        mock_send.return_value = True
        send_campaign_task(str(campaign.id))

        mock_send.assert_called_once_with(cs)
        cs.refresh_from_db()
        self.assertEqual(cs.status, 'sent')

    @patch('apps.mailer.services.mail_service.send_single_email')
    def test_campaign_counts_updated(self, mock_send):
        from apps.mailer.tasks.send_campaign import send_campaign_task

        campaign = self._create_campaign()
        r1 = self._create_recipient(email='r1@test.com')
        r2 = self._create_recipient(email='r2@test.com')
        CampaignSend.objects.create(campaign=campaign, recipient=r1)
        CampaignSend.objects.create(campaign=campaign, recipient=r2)

        mock_send.return_value = True
        send_campaign_task(str(campaign.id))
        campaign.refresh_from_db()
        self.assertEqual(campaign.sent_count, 2)
