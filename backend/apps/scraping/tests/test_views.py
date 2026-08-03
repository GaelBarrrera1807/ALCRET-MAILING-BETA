from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from apps.companies.models import Company
from apps.scraping.models import ScrapingJob, ScrapedData
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
        self.company = Company.objects.create(name='Test Corp', organization=self.org)
        self._auth()

    def _auth(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser', 'password': 'testpass123',
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')


class ScrapingJobTests(BaseTest):
    def test_list_jobs(self):
        job = ScrapingJob.objects.create(organization=self.org, url='https://example.com')
        Company.objects.filter(id=self.company.id).update(scraping_job=job)
        response = self.client.get('/api/scraping-jobs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_job_with_url(self):
        with patch('apps.scraping.views.run_scraping_job.delay') as mock_task:
            response = self.client.post('/api/scraping-jobs/', {
                'company_id': str(self.company.id),
                'url': 'https://example.com',
                'job_type': 'website',
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(response.data['job_type'], 'website')
            mock_task.assert_called_once()

    def test_create_job_with_company(self):
        with patch('apps.scraping.views.run_scraping_job.delay') as mock_task:
            response = self.client.post('/api/scraping-jobs/', {
                'company_id': str(self.company.id),
                'job_type': 'website',
            })
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_task.assert_called_once()

    def test_retrieve_job(self):
        job = ScrapingJob.objects.create(organization=self.org, url='https://example.com')
        response = self.client.get(f'/api/scraping-jobs/{job.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retry_job(self):
        job = ScrapingJob.objects.create(
            organization=self.org, url='https://example.com',
            status='error', error_message='Failed',
        )
        with patch('apps.scraping.views.run_scraping_job.delay') as mock_task:
            response = self.client.post(f'/api/scraping-jobs/{job.id}/retry/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'retrying')
            mock_task.assert_called_once_with(job.id)

    def test_delete_job(self):
        job = ScrapingJob.objects.create(organization=self.org, url='https://example.com')
        response = self.client.delete(f'/api/scraping-jobs/{job.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_multi_tenant_isolation(self):
        other_org = Organization.objects.create(name='Other Org')
        ScrapingJob.objects.create(organization=other_org, url='https://other.com')
        response = self.client.get('/api/scraping-jobs/')
        self.assertEqual(len(response.data['results']), 0)


class ScrapedDataTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.data = ScrapedData.objects.create(
            company=self.company,
            source='https://example.com',
            data_type='website',
            raw_data={'title': 'Test'},
        )

    def test_list_scraped_data(self):
        response = self.client.get('/api/scraped-data/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_filter_by_company(self):
        response = self.client.get(f'/api/scraped-data/?company={self.company.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_scraped_data(self):
        response = self.client.get(f'/api/scraped-data/{self.data.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['source'], 'https://example.com')
