from unittest import mock
from typing import Any, Dict

from django.conf import settings
from django.test import TestCase

from apps.companies.models import Company, CompanyContact
from apps.scraping.models import ScrapingJob, ScrapedData
from apps.scraping.services import ScrapingService
from apps.users.models import Organization


def _mock_response(json_data: Dict[str, Any], status_code: int = 200) -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


class RunExternalScrapingTests(TestCase):
    def setUp(self) -> None:
        self.org = Organization.objects.create(name='Test Org')
        self.company = Company.objects.create(
            name='Test Corp',
            organization=self.org,
            website='https://testcorp.com',
        )
        self.job = ScrapingJob.objects.create(
            organization=self.org,
            url='https://testcorp.com',
            job_type='enrichment',
            status='pending',
        )
        Company.objects.filter(id=self.company.id).update(scraping_job=self.job)
        self.service = ScrapingService()

    @mock.patch.object(settings, 'APIFY_API_KEY', 'test-apify-key', create=True)
    @mock.patch.object(settings, 'SNOV_CLIENT_ID', 'test-snov-client-id', create=True)
    @mock.patch.object(settings, 'SNOV_CLIENT_SECRET', 'test-snov-client-secret', create=True)
    @mock.patch('apps.scraping.services.httpx.Client')
    def test_run_external_scraping_success(
        self, mock_httpx_client: mock.MagicMock
    ) -> None:
        apify_start_resp = _mock_response({'data': {'id': 'run-success-123'}})
        apify_status_resp = _mock_response({'data': {'status': 'SUCCEEDED'}})
        apify_results_resp = _mock_response([
            {
                'fullName': 'Carlos Mendoza',
                'title': 'Gerente de Operaciones',
                'linkedinUrl': 'https://linkedin.com/in/carlos-mendoza',
                'companyName': 'Test Corp',
            },
        ])
        snov_oauth_resp = _mock_response({
            'access_token': 'test-snov-token',
            'expires_in': 3600,
        })
        snov_lookup_resp = _mock_response({
            'email': 'carlos.m@testcorp.com',
        })

        mock_client = mock.MagicMock(name='httpx_client_instance')
        mock_context = mock.MagicMock(name='httpx_context')
        mock_context.__enter__.return_value = mock_client
        mock_httpx_client.return_value = mock_context

        mock_client.post.side_effect = [
            apify_start_resp,
            snov_oauth_resp,
            snov_lookup_resp,
        ]
        mock_client.get.side_effect = [apify_status_resp, apify_results_resp]

        clean_data = self.service.run_external_scraping(str(self.job.id))

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'processing')

        scraped = ScrapedData.objects.filter(
            company=self.company, source='apify', data_type='external_api'
        ).first()
        self.assertIsNotNone(scraped, 'ScrapedData debe haberse creado')
        self.assertIn('apify_contacts', scraped.raw_data)
        self.assertIn('snov_enrichments', scraped.raw_data)

        self.assertIn('contacts', clean_data)
        self.assertEqual(len(clean_data['contacts']), 1)
        contact = clean_data['contacts'][0]
        self.assertEqual(contact['name'], 'Carlos Mendoza')
        self.assertEqual(contact['title'], 'Gerente de Operaciones')
        self.assertEqual(contact['email'], 'carlos.m@testcorp.com')
        self.assertEqual(contact['phone'], '')

        mock_client.post.assert_any_call(
            mock.ANY,
            params={'token': 'test-apify-key'},
            json=mock.ANY,
        )
        mock_client.post.assert_any_call(
            'https://api.snov.io/v1/oauth/access_token',
            json={
                'client_id': 'test-snov-client-id',
                'client_secret': 'test-snov-client-secret',
            },
        )
        mock_client.post.assert_any_call(
            'https://api.snov.io/v1/get-profile-by-name-and-domain',
            headers={'Authorization': 'Bearer test-snov-token'},
            json={
                'firstName': 'Carlos',
                'lastName': 'Mendoza',
                'domain': 'testcorp.com',
            },
        )

    @mock.patch.object(settings, 'APIFY_API_KEY', 'test-apify-key', create=True)
    @mock.patch('apps.scraping.services.time.sleep')
    @mock.patch('apps.scraping.services.httpx.Client')
    def test_run_external_scraping_apify_timeout(
        self, mock_httpx_client: mock.MagicMock, mock_sleep: mock.MagicMock
    ) -> None:
        apify_start_resp = _mock_response({'data': {'id': 'run-timeout-456'}})
        running_resp = _mock_response({'data': {'status': 'RUNNING'}})

        mock_client = mock.MagicMock(name='httpx_client_instance')
        mock_context = mock.MagicMock(name='httpx_context')
        mock_context.__enter__.return_value = mock_client
        mock_httpx_client.return_value = mock_context

        mock_client.post.return_value = apify_start_resp
        mock_client.get.return_value = running_resp

        with self.assertRaises(TimeoutError) as ctx:
            self.service.run_external_scraping(str(self.job.id))

        self.assertIn('no completó', str(ctx.exception))

        self.assertEqual(mock_sleep.call_count, 30)

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'processing')

    @mock.patch.object(settings, 'APIFY_API_KEY', '', create=True)
    def test_run_external_scraping_missing_api_keys(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            self.service.run_external_scraping(str(self.job.id))
        self.assertIn('APIFY_API_KEY', str(ctx.exception))


class EnrichCompanyContactsTests(TestCase):
    def setUp(self) -> None:
        self.org = Organization.objects.create(name='Test Org')
        self.company = Company.objects.create(
            name='Test Corp',
            organization=self.org,
        )
        self.service = ScrapingService()

    def test_enrich_company_contacts_avoid_duplicate_primary(self) -> None:
        CompanyContact.objects.create(
            company=self.company,
            name='Contacto Original',
            position='CEO',
            email='ceo@testcorp.com',
            phone='+520000000000',
            is_primary=True,
        )

        clean_data: Dict[str, Any] = {
            'contacts': [
                {
                    'name': 'Nuevo Contacto A',
                    'title': 'Gerente de Ventas',
                    'email': 'ventas@testcorp.com',
                    'phone': '+521111111111',
                },
                {
                    'name': 'Nuevo Contacto B',
                    'title': 'Desarrollador Senior',
                    'email': 'dev@testcorp.com',
                    'phone': '+522222222222',
                },
            ],
            'source': 'apify_snov',
        }

        self.service.enrich_company_contacts(
            str(self.company.id), clean_data
        )

        existing_primary = CompanyContact.objects.get(
            company=self.company, name='Contacto Original'
        )
        self.assertTrue(
            existing_primary.is_primary,
            'El contacto primario original no debe modificarse',
        )

        new_contacts = CompanyContact.objects.filter(
            company=self.company
        ).exclude(name='Contacto Original')
        self.assertEqual(
            new_contacts.count(), 2,
            'Deben haberse creado exactamente 2 contactos nuevos',
        )

        for contact in new_contacts:
            self.assertFalse(
                contact.is_primary,
                f'Ningún contacto nuevo debe ser primario: {contact.name}',
            )

    def test_enrich_company_contacts_no_existing_primary_sets_first(self) -> None:
        clean_data: Dict[str, Any] = {
            'contacts': [
                {
                    'name': 'Primer Contacto',
                    'title': 'CTO',
                    'email': 'cto@testcorp.com',
                    'phone': '+523333333333',
                },
                {
                    'name': 'Segundo Contacto',
                    'title': 'VP Engineering',
                    'email': 'vp@testcorp.com',
                    'phone': '+524444444444',
                },
            ],
            'source': 'apify_snov',
        }

        self.service.enrich_company_contacts(
            str(self.company.id), clean_data
        )

        contacts = CompanyContact.objects.filter(
            company=self.company
        ).order_by('email')
        self.assertEqual(contacts.count(), 2)

        first = contacts.get(email='cto@testcorp.com')
        self.assertTrue(first.is_primary, 'El primer contacto debe ser primario')

        second = contacts.get(email='vp@testcorp.com')
        self.assertFalse(second.is_primary, 'El segundo contacto no debe ser primario')

    def test_enrich_company_contacts_skip_empty_name(self) -> None:
        clean_data: Dict[str, Any] = {
            'contacts': [
                {'name': '', 'title': 'Unknown', 'email': '', 'phone': ''},
                {
                    'name': 'Contacto Válido',
                    'title': 'Analista',
                    'email': 'analista@testcorp.com',
                    'phone': '+525555555555',
                },
            ],
            'source': 'apify_snov',
        }

        self.service.enrich_company_contacts(
            str(self.company.id), clean_data
        )

        contacts = CompanyContact.objects.filter(company=self.company)
        self.assertEqual(contacts.count(), 1)
        self.assertEqual(contacts.first().name, 'Contacto Válido')

    def test_enrich_company_contacts_update_existing_by_email(self) -> None:
        CompanyContact.objects.create(
            company=self.company,
            name='Nombre Anterior',
            position='Junior',
            email='actualizar@testcorp.com',
            phone='+526666666666',
            is_primary=False,
        )

        clean_data: Dict[str, Any] = {
            'contacts': [
                {
                    'name': 'Nombre Nuevo',
                    'title': 'Senior',
                    'email': 'actualizar@testcorp.com',
                    'phone': '+527777777777',
                },
            ],
            'source': 'apify_snov',
        }

        self.service.enrich_company_contacts(
            str(self.company.id), clean_data
        )

        contact = CompanyContact.objects.get(
            company=self.company, email='actualizar@testcorp.com'
        )
        self.assertEqual(contact.name, 'Nombre Nuevo')
        self.assertEqual(contact.position, 'Senior')
        self.assertEqual(contact.phone, '+527777777777')

    def test_enrich_company_contacts_update_existing_by_name(self) -> None:
        CompanyContact.objects.create(
            company=self.company,
            name='Contacto Sin Email',
            position='Consultor',
            email='',
            phone='+528888888888',
            is_primary=False,
        )

        clean_data: Dict[str, Any] = {
            'contacts': [
                {
                    'name': 'Contacto Sin Email',
                    'title': 'Consultor Senior',
                    'email': '',
                    'phone': '+529999999999',
                },
            ],
            'source': 'apify_snov',
        }

        self.service.enrich_company_contacts(
            str(self.company.id), clean_data
        )

        contact = CompanyContact.objects.get(
            company=self.company, name='Contacto Sin Email'
        )
        self.assertEqual(contact.position, 'Consultor Senior')
        self.assertEqual(contact.phone, '+529999999999')
