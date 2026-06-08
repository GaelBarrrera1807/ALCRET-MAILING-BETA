from datetime import date, timedelta

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.analytics.models import DashboardMetric, ProcessingStats
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
        self._auth()

    def _auth(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'testpass123',
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')


class DashboardMetricTests(BaseTest):
    def test_list_metrics(self):
        DashboardMetric.objects.create(
            organization=self.org,
            metric_type='total_companies',
            value=100,
            date=date.today(),
        )
        response = self.client.get('/api/dashboard-metrics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_filter_by_metric_type(self):
        DashboardMetric.objects.create(
            organization=self.org, metric_type='total_leads', value=50, date=date.today(),
        )
        DashboardMetric.objects.create(
            organization=self.org, metric_type='total_analyzed', value=30, date=date.today(),
        )
        response = self.client.get('/api/dashboard-metrics/?metric_type=total_leads')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_days(self):
        DashboardMetric.objects.create(
            organization=self.org, metric_type='total_companies', value=10, date=date.today(),
        )
        old_date = date.today() - timedelta(days=30)
        DashboardMetric.objects.create(
            organization=self.org, metric_type='total_leads', value=20, date=old_date,
        )
        response = self.client.get('/api/dashboard-metrics/?days=7')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cutoff = str(date.today() - timedelta(days=7))
        for m in response.data['results']:
            self.assertGreaterEqual(m['date'], cutoff)

    def test_multi_tenant_isolation(self):
        other_org = Organization.objects.create(name='Other Org')
        DashboardMetric.objects.create(
            organization=other_org, metric_type='total_companies', value=999, date=date.today(),
        )
        response = self.client.get('/api/dashboard-metrics/')
        for m in response.data['results']:
            self.assertEqual(m['organization'], str(self.org.id))


class ProcessingStatsTests(BaseTest):
    def test_list_stats(self):
        ProcessingStats.objects.create(
            organization=self.org,
            total_companies=100,
            total_analyzed=90,
            total_pending=5,
            total_errors=5,
            total_leads=50,
            total_potential_clients=30,
            avg_score=75.0,
        )
        response = self.client.get('/api/processing-stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_multi_tenant_isolation(self):
        other_org = Organization.objects.create(name='Other Org')
        ProcessingStats.objects.create(
            organization=other_org,
            total_companies=999, total_analyzed=999,
            total_pending=0, total_errors=0,
            total_leads=500, total_potential_clients=300,
            avg_score=85.0,
        )
        response = self.client.get('/api/processing-stats/')
        for s in response.data['results']:
            self.assertEqual(s['organization'], str(self.org.id))


class AnalyticsSummaryTests(BaseTest):
    def test_summary_returns_all_keys(self):
        sector = Sector.objects.create(name='Transporte')
        company = Company.objects.create(
            name='Test Corp', organization=self.org,
            sector=sector, status='analyzed', score=80,
        )
        Lead.objects.create(company=company, organization=self.org, is_potential_client=True)

        response = self.client.get('/api/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_keys = [
            'total_companies', 'total_analyzed', 'total_pending',
            'total_errors', 'total_leads', 'potential_clients',
            'avg_score', 'by_sector', 'by_status', 'by_priority',
        ]
        for key in expected_keys:
            self.assertIn(key, response.data)

    def test_summary_counts(self):
        Company.objects.create(name='C1', organization=self.org, status='analyzed', score=80)
        Company.objects.create(name='C2', organization=self.org, status='pending', score=0)
        Company.objects.create(name='C3', organization=self.org, status='error', score=0)

        response = self.client.get('/api/summary/')
        self.assertEqual(response.data['total_companies'], 3)
        self.assertEqual(response.data['total_analyzed'], 1)
        self.assertEqual(response.data['total_pending'], 1)
        self.assertEqual(response.data['total_errors'], 1)

    def test_summary_empty(self):
        response = self.client.get('/api/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_companies'], 0)
        self.assertEqual(response.data['avg_score'], 0)
