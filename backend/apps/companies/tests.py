import io
import json
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from apps.companies.models import Sector, Product, Company, CompanyContact
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


class SectorTests(BaseTest):
    def test_list_sectors(self):
        Sector.objects.create(name='Transporte')
        response = self.client.get('/api/sectors/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_create_sector(self):
        response = self.client.post('/api/sectors/', {'name': 'Construcción'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Construcción')

    def test_retrieve_sector(self):
        sector = Sector.objects.create(name='Agrícola')
        response = self.client.get(f'/api/sectors/{sector.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Agrícola')

    def test_update_sector(self):
        sector = Sector.objects.create(name='Old')
        response = self.client.patch(f'/api/sectors/{sector.id}/', {'name': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated')

    def test_delete_sector(self):
        sector = Sector.objects.create(name='Delete Me')
        response = self.client.delete(f'/api/sectors/{sector.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_search_sector(self):
        Sector.objects.create(name='Transporte')
        Sector.objects.create(name='Construcción')
        response = self.client.get('/api/sectors/?search=Transporte')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class ProductTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.sector = Sector.objects.create(name='Transporte')

    def test_list_products(self):
        Product.objects.create(name='Dolly')
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_product(self):
        response = self.client.post('/api/products/', {
            'name': 'Cajas secas',
            'sectors': [self.sector.id],
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Cajas secas')

    def test_retrieve_product(self):
        product = Product.objects.create(name='Plataformas')
        product.sectors.add(self.sector)
        response = self.client.get(f'/api/products/{product.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Plataformas')

    def test_update_product(self):
        product = Product.objects.create(name='Old')
        response = self.client.patch(f'/api/products/{product.id}/', {'name': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_product(self):
        product = Product.objects.create(name='Delete Me')
        response = self.client.delete(f'/api/products/{product.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CompanyTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.sector = Sector.objects.create(name='Transporte')

    def test_list_companies(self):
        Company.objects.create(name='Test Corp', organization=self.org)
        response = self.client.get('/api/companies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_create_company(self):
        response = self.client.post('/api/companies/', {
            'name': 'New Corp',
            'sector': self.sector.id,
            'city': 'Mexico City',
            'state': 'CDMX',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Corp')
        self.assertEqual(response.data['organization'], self.org.id)

    def test_retrieve_company(self):
        company = Company.objects.create(name='Detail Corp', organization=self.org)
        response = self.client.get(f'/api/companies/{company.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Detail Corp')

    def test_update_company(self):
        company = Company.objects.create(name='Old Corp', organization=self.org)
        response = self.client.patch(f'/api/companies/{company.id}/', {'name': 'Updated Corp'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Corp')

    def test_delete_company(self):
        company = Company.objects.create(name='Delete Corp', organization=self.org)
        response = self.client.delete(f'/api/companies/{company.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_filter_by_status(self):
        Company.objects.create(name='Pending', status='pending', organization=self.org)
        Company.objects.create(name='Analyzed', status='analyzed', organization=self.org)
        response = self.client.get('/api/companies/?status=analyzed')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Analyzed')

    def test_filter_by_sector(self):
        Company.objects.create(name='In Sector', sector=self.sector, organization=self.org)
        other = Sector.objects.create(name='Other')
        Company.objects.create(name='Other Sector', sector=other, organization=self.org)
        response = self.client.get(f'/api/companies/?sector={self.sector.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_min_score(self):
        Company.objects.create(name='High', score=80, organization=self.org)
        Company.objects.create(name='Low', score=20, organization=self.org)
        response = self.client.get('/api/companies/?min_score=50')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'High')

    def test_filter_by_is_lead(self):
        Company.objects.create(name='Lead True', is_lead=True, organization=self.org)
        Company.objects.create(name='Lead False', is_lead=False, organization=self.org)
        response = self.client.get('/api/companies/?is_lead=true')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_companies(self):
        Company.objects.create(name='Target Corp', organization=self.org)
        Company.objects.create(name='Other Corp', organization=self.org)
        response = self.client.get('/api/companies/?search=Target')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_upload_csv(self):
        csv_content = 'name,email,phone\nTest Corp,test@corp.com,555-0100\n'
        response = self.client.post('/api/companies/upload/', {
            'file': io.BytesIO(csv_content.encode()),
        }, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn('task_id', response.data)
        self.assertEqual(response.data['status'], 'processing')

    def test_analyze_company(self):
        company = Company.objects.create(name='Analyze Me', organization=self.org)
        with patch('apps.ai_engine.tasks.analyze_company.delay') as mock_task:
            response = self.client.post(f'/api/companies/{company.id}/analyze/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['status'], 'analyzing')
            mock_task.assert_called_once_with(company.id)

    def test_analyze_batch(self):
        c1 = Company.objects.create(name='C1', organization=self.org)
        c2 = Company.objects.create(name='C2', organization=self.org)
        with patch('apps.ai_engine.tasks.analyze_company.delay') as mock_task:
            response = self.client.post('/api/companies/analyze_batch/', {
                'company_ids': [str(c1.id), str(c2.id)],
            })
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(mock_task.called)

    def test_analyze_batch_no_ids(self):
        response = self.client.post('/api/companies/analyze_batch/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multi_tenant_isolation(self):
        other_org = Organization.objects.create(name='Other Org')
        Company.objects.create(name='Other Company', organization=other_org)
        response = self.client.get('/api/companies/')
        for c in response.data['results']:
            self.assertEqual(c['organization'], self.org.id)


class CompanyContactTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.company = Company.objects.create(name='Test Corp', organization=self.org)

    def test_create_contact(self):
        response = self.client.post('/api/contacts/', {
            'company': self.company.id,
            'name': 'John Doe',
            'email': 'john@corp.com',
            'is_primary': True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'John Doe')

    def test_list_contacts_by_company(self):
        CompanyContact.objects.create(company=self.company, name='John')
        response = self.client.get(f'/api/contacts/?company={self.company.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_update_contact(self):
        contact = CompanyContact.objects.create(company=self.company, name='John')
        response = self.client.patch(f'/api/contacts/{contact.id}/', {'position': 'Manager'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['position'], 'Manager')

    def test_delete_contact(self):
        contact = CompanyContact.objects.create(company=self.company, name='John')
        response = self.client.delete(f'/api/contacts/{contact.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
