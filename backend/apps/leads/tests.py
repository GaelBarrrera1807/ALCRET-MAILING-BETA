from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from apps.companies.models import Company
from apps.leads.models import Lead, LeadNote
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


class LeadTests(BaseTest):
    def test_list_leads(self):
        Lead.objects.create(company=self.company, organization=self.org)
        response = self.client.get('/api/leads/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_create_lead(self):
        response = self.client.post('/api/leads/', {
            'company': self.company.id,
            'score': 85,
            'priority': 'alta',
            'status': 'new',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['score'], 85)
        self.assertEqual(response.data['organization'], self.org.id)

    def test_retrieve_lead(self):
        lead = Lead.objects.create(company=self.company, organization=self.org)
        response = self.client.get(f'/api/leads/{lead.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], 'Test Corp')

    def test_update_lead(self):
        lead = Lead.objects.create(company=self.company, organization=self.org)
        response = self.client.patch(f'/api/leads/{lead.id}/', {'status': 'contacted'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'contacted')

    def test_delete_lead(self):
        lead = Lead.objects.create(company=self.company, organization=self.org)
        response = self.client.delete(f'/api/leads/{lead.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_filter_by_status(self):
        Lead.objects.create(company=self.company, organization=self.org, status='new')
        c2 = Company.objects.create(name='C2', organization=self.org)
        Lead.objects.create(company=c2, organization=self.org, status='won')
        response = self.client.get('/api/leads/?status=won')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_priority(self):
        Lead.objects.create(company=self.company, organization=self.org, priority='alta')
        c2 = Company.objects.create(name='C2', organization=self.org)
        Lead.objects.create(company=c2, organization=self.org, priority='baja')
        response = self.client.get('/api/leads/?priority=alta')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_min_score(self):
        Lead.objects.create(company=self.company, organization=self.org, score=80)
        c2 = Company.objects.create(name='C2', organization=self.org)
        Lead.objects.create(company=c2, organization=self.org, score=20)
        response = self.client.get('/api/leads/?min_score=50')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_filter_by_assigned(self):
        other = User.objects.create_user(username='other', password='testpass123')
        Lead.objects.create(company=self.company, organization=self.org, assigned_to=self.user)
        c2 = Company.objects.create(name='C2', organization=self.org)
        Lead.objects.create(company=c2, organization=self.org, assigned_to=other)
        response = self.client.get(f'/api/leads/?assigned_to={self.user.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_lead(self):
        Lead.objects.create(company=self.company, organization=self.org)
        response = self.client.get('/api/leads/?search=Test Corp')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_batch_update_status(self):
        lead1 = Lead.objects.create(company=self.company, organization=self.org)
        c2 = Company.objects.create(name='C2', organization=self.org)
        lead2 = Lead.objects.create(company=c2, organization=self.org)
        response = self.client.post('/api/leads/batch_update/', {
            'lead_ids': [str(lead1.id), str(lead2.id)],
            'status': 'qualified',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated'], 2)
        lead1.refresh_from_db()
        lead2.refresh_from_db()
        self.assertEqual(lead1.status, 'qualified')
        self.assertEqual(lead2.status, 'qualified')

    def test_batch_update_priority(self):
        lead = Lead.objects.create(company=self.company, organization=self.org)
        response = self.client.post('/api/leads/batch_update/', {
            'lead_ids': [str(lead.id)],
            'priority': 'urgente',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.priority, 'urgente')

    def test_batch_update_no_ids(self):
        response = self.client.post('/api/leads/batch_update/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lead_has_company_name(self):
        lead = Lead.objects.create(company=self.company, organization=self.org)
        response = self.client.get(f'/api/leads/{lead.id}/')
        self.assertIn('company_name', response.data)

    def test_multi_tenant_isolation(self):
        other_org = Organization.objects.create(name='Other Org')
        other_company = Company.objects.create(name='Other Co', organization=other_org)
        Lead.objects.create(company=other_company, organization=other_org)
        response = self.client.get('/api/leads/')
        for l in response.data['results']:
            self.assertEqual(l['organization'], str(self.org.id))


class LeadNoteTests(BaseTest):
    def setUp(self):
        super().setUp()
        self.lead = Lead.objects.create(company=self.company, organization=self.org)

    def test_create_note(self):
        response = self.client.post('/api/lead-notes/', {
            'lead': self.lead.id,
            'content': 'Nota de prueba',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Nota de prueba')

    def test_list_notes_by_lead(self):
        LeadNote.objects.create(lead=self.lead, author=self.user, content='Note 1')
        response = self.client.get(f'/api/lead-notes/?lead={self.lead.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 1)

    def test_update_note(self):
        note = LeadNote.objects.create(lead=self.lead, author=self.user, content='Old')
        response = self.client.patch(f'/api/lead-notes/{note.id}/', {'content': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Updated')

    def test_delete_note(self):
        note = LeadNote.objects.create(lead=self.lead, author=self.user, content='Delete')
        response = self.client.delete(f'/api/lead-notes/{note.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_note_has_author(self):
        response = self.client.post('/api/lead-notes/', {
            'lead': self.lead.id,
            'content': 'Author test',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.user.id)
