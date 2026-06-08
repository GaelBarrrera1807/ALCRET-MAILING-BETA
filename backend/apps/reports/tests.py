from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from apps.companies.models import Company
from apps.reports.models import Report, ReportTemplate
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


class ReportTests(BaseTest):
    def test_list_reports(self):
        Report.objects.create(
            organization=self.org, title='Test Report',
            report_type='leads', file_type='pdf',
        )
        response = self.client.get('/api/reports/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_report(self):
        Company.objects.create(name='Test Corp', organization=self.org)
        with patch('apps.reports.views.generate_report.delay') as mock_task:
            response = self.client.post('/api/reports/', {
                'title': 'Monthly Report',
                'report_type': 'leads',
                'file_type': 'pdf',
                'filters': {},
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['title'], 'Monthly Report')
            self.assertEqual(response.data['status'], 'generating')
            mock_task.assert_called_once()

    def test_create_report_with_filters(self):
        with patch('apps.reports.views.generate_report.delay'):
            response = self.client.post('/api/reports/', {
                'title': 'Filtered Report',
                'report_type': 'leads',
                'filters': {'status': 'won'},
            }, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['filters']['status'], 'won')
            self.assertIn('organization_id', response.data['filters'])

    def test_retrieve_report(self):
        report = Report.objects.create(
            organization=self.org, title='Test',
            report_type='leads', file_type='pdf',
        )
        response = self.client.get(f'/api/reports/{report.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test')

    def test_delete_report(self):
        report = Report.objects.create(
            organization=self.org, title='Delete',
            report_type='leads', file_type='pdf',
        )
        response = self.client.delete(f'/api/reports/{report.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_regenerate_report(self):
        report = Report.objects.create(
            organization=self.org, title='Regen',
            report_type='leads', file_type='pdf',
            status='completed',
        )
        with patch('apps.reports.views.generate_report.delay') as mock_task:
            response = self.client.post(f'/api/reports/{report.id}/regenerate/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'regenerating')
            mock_task.assert_called_once_with(report.id)

    def test_filter_by_report_type(self):
        Report.objects.create(organization=self.org, title='R1', report_type='leads', file_type='pdf')
        Report.objects.create(organization=self.org, title='R2', report_type='companies', file_type='pdf')
        response = self.client.get('/api/reports/?report_type=leads')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_multi_tenant_isolation(self):
        other_org = Organization.objects.create(name='Other Org')
        Report.objects.create(organization=other_org, title='Other', report_type='leads', file_type='pdf')
        response = self.client.get('/api/reports/')
        self.assertEqual(len(response.data['results']), 0)


class ReportTemplateTests(BaseTest):
    def test_list_templates(self):
        ReportTemplate.objects.create(name='Default', report_type='leads')
        response = self.client.get('/api/report-templates/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_template(self):
        response = self.client.post('/api/report-templates/', {
            'name': 'Custom Template',
            'report_type': 'leads',
            'config': {'header': 'Report'},
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Custom Template')

    def test_retrieve_template(self):
        tpl = ReportTemplate.objects.create(name='Test', report_type='leads')
        response = self.client.get(f'/api/report-templates/{tpl.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_template(self):
        tpl = ReportTemplate.objects.create(name='Old', report_type='leads')
        response = self.client.patch(f'/api/report-templates/{tpl.id}/', {'name': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated')

    def test_delete_template(self):
        tpl = ReportTemplate.objects.create(name='Delete', report_type='leads')
        response = self.client.delete(f'/api/report-templates/{tpl.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_only_active_templates_listed(self):
        ReportTemplate.objects.create(name='Active', report_type='leads', is_active=True)
        ReportTemplate.objects.create(name='Inactive', report_type='leads', is_active=False)
        response = self.client.get('/api/report-templates/')
        names = [t['name'] for t in response.data['results']]
        self.assertIn('Active', names)
        self.assertNotIn('Inactive', names)
