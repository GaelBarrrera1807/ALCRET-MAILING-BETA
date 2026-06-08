import json
from unittest.mock import patch, MagicMock

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from apps.ai_engine.models import AnalysisRequest, AnalysisResult, PromptTemplate
from apps.ai_engine.services import CerebrasClient
from apps.companies.models import Company, Sector
from apps.leads.models import Lead
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
        self.sector = Sector.objects.create(name='Transporte')
        self.company = Company.objects.create(
            name='Test Corp', organization=self.org, sector=self.sector,
        )
        self._auth()

    def _auth(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'testpass123',
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')


class AnalysisRequestTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.analysis_request = AnalysisRequest.objects.create(
            company=self.company, organization=self.org,
        )

    def test_list_requests(self):
        response = self.client.get('/api/analysis-requests/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_request(self):
        response = self.client.get(f'/api/analysis-requests/{self.analysis_request.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], 'Test Corp')

    def test_filter_by_company(self):
        c2 = Company.objects.create(name='C2', organization=self.org)
        AnalysisRequest.objects.create(company=c2, organization=self.org)
        response = self.client.get(f'/api/analysis-requests/?company={self.company.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class AnalysisResultTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.req = AnalysisRequest.objects.create(company=self.company, organization=self.org)
        self.result = AnalysisResult.objects.create(
            analysis_request=self.req, company=self.company,
            score=85, is_potential_client=True,
            detected_sector='Transporte',
            priority='alta',
        )

    def test_list_results(self):
        response = self.client.get('/api/analysis-results/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_result(self):
        response = self.client.get(f'/api/analysis-results/{self.result.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], 'Test Corp')

    def test_filter_by_company(self):
        response = self.client.get(f'/api/analysis-results/?company={self.company.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class PromptTemplateTests(BaseTest):
    def test_list_templates(self):
        PromptTemplate.objects.create(name='Default', system_prompt='test', user_prompt_template='test')
        response = self.client.get('/api/prompt-templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_template(self):
        response = self.client.post('/api/prompt-templates/', {
            'name': 'Custom Prompt',
            'system_prompt': 'You are an expert',
            'user_prompt_template': 'Analyze: {name}',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Custom Prompt')

    def test_retrieve_template(self):
        tpl = PromptTemplate.objects.create(name='Test', system_prompt='x', user_prompt_template='y')
        response = self.client.get(f'/api/prompt-templates/{tpl.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_template(self):
        tpl = PromptTemplate.objects.create(name='Old', system_prompt='x', user_prompt_template='y')
        response = self.client.patch(f'/api/prompt-templates/{tpl.id}/', {'name': 'New'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'New')

    def test_delete_template(self):
        tpl = PromptTemplate.objects.create(name='Delete', system_prompt='x', user_prompt_template='y')
        response = self.client.delete(f'/api/prompt-templates/{tpl.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_only_active_templates_listed(self):
        PromptTemplate.objects.create(name='Active', system_prompt='x', user_prompt_template='y', is_active=True)
        PromptTemplate.objects.create(name='Inactive', system_prompt='x', user_prompt_template='y', is_active=False)
        response = self.client.get('/api/prompt-templates/')
        names = [t['name'] for t in response.data['results']]
        self.assertIn('Active', names)
        self.assertNotIn('Inactive', names)


class CerebrasClientTests(APITestCase):
    def test_mock_analysis_high_score(self):
        client = CerebrasClient()
        result = client._mock_analysis({
            'name': 'Transportes Logística SA',
            'description': 'Empresa de transporte de carga pesada y contenedores',
        })
        self.assertGreater(result['score'], 0)
        self.assertIn('score', result)
        self.assertIn('priority', result)
        self.assertIn('detected_sector', result)
        self.assertIn('recommended_products', result)

    def test_mock_analysis_low_score(self):
        client = CerebrasClient()
        result = client._mock_analysis({
            'name': 'Cafetería El Buen Sabor',
            'description': 'Pequeña cafetería local',
        })
        self.assertLess(result['score'], 50)
        self.assertFalse(result['is_potential_client'])

    def test_analyze_company_without_api_key(self):
        client = CerebrasClient()
        client.client = None
        result = client.analyze_company({
            'name': 'Test Corp',
            'description': 'Transport company',
        })
        self.assertIn('score', result)
        self.assertIsNotNone(result.get('processing_time'))

    def test_is_available_false_without_key(self):
        client = CerebrasClient()
        client.client = None
        self.assertFalse(client.is_available())

    def test_mock_analysis_returns_structured_data(self):
        client = CerebrasClient()
        result = client._mock_analysis({
            'name': 'Transportes XYZ',
            'description': 'Empresa de transporte de carga',
            'website': '',
            'sector': 'Transporte',
            'city': 'CDMX',
            'state': 'CDMX',
        })
        required_keys = ['score', 'is_potential_client', 'detected_sector',
                         'recommended_products', 'priority', 'reason', 'summary',
                         'raw_json', 'processing_time']
        for key in required_keys:
            self.assertIn(key, result, f'Missing key: {key}')


class AnalyzeCompanyTaskTests(BaseTest):
    @patch('apps.ai_engine.services.CerebrasClient.is_available', return_value=True)
    @patch('apps.ai_engine.services.CerebrasClient.analyze_company')
    def test_analyze_company_task_creates_lead(self, mock_analyze, _mock_avail):
        mock_analyze.return_value = {
            'score': 90,
            'is_potential_client': True,
            'detected_sector': 'Transporte',
            'recommended_products': ['Cajas secas', 'Plataformas'],
            'priority': 'alta',
            'reason': 'Score alto',
            'summary': 'Cliente potencial',
            'raw_json': {},
            'processing_time': 1.5,
        }

        from apps.ai_engine.tasks import analyze_company
        analyze_company(self.company.id)

        self.company.refresh_from_db()
        self.assertEqual(self.company.status, 'analyzed')
        self.assertEqual(self.company.score, 90)
        self.assertTrue(self.company.is_lead)

        self.assertTrue(Lead.objects.filter(company=self.company).exists())
        lead = Lead.objects.get(company=self.company)
        self.assertEqual(lead.score, 90)
        self.assertEqual(lead.priority, 'alta')

    @patch('apps.ai_engine.services.CerebrasClient.is_available', return_value=True)
    @patch('apps.ai_engine.services.CerebrasClient.analyze_company')
    def test_analyze_company_task_handles_error(self, mock_analyze, _mock_avail):
        mock_analyze.return_value = {
            'error': 'API Error',
            'processing_time': 0.5,
        }

        from apps.ai_engine.tasks import analyze_company
        result = analyze_company(self.company.id)

        self.company.refresh_from_db()
        self.assertEqual(self.company.status, 'error')
        self.assertIn('error', result)
