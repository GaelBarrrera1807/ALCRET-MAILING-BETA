from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.users.models import Organization

User = get_user_model()


class UserTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name='Test Org')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            organization=self.org,
            is_organization_admin=True,
        )

    def _auth(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def test_register_user(self):
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepass123',
            'first_name': 'New',
            'last_name': 'User',
        }
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['username'], 'newuser')

    def test_register_user_with_organization(self):
        data = {
            'username': 'orguser',
            'email': 'org@example.com',
            'password': 'securepass123',
            'organization_name': 'New Org',
        }
        response = self.client.post('/api/auth/register/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='orguser').exists())
        user = User.objects.get(username='orguser')
        self.assertIsNotNone(user.organization)
        self.assertTrue(user.is_organization_admin)

    def test_login_returns_tokens(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_invalid_credentials(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'wrongpass',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        login_resp = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123',
        })
        response = self.client.post('/api/auth/token/refresh/', {
            'refresh': login_resp.data['refresh'],
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_me_endpoint(self):
        self._auth()
        response = self.client.get('/api/auth/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_me_requires_auth(self):
        response = self.client.get('/api/auth/users/me/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_users(self):
        self._auth()
        User.objects.create_user(username='other', password='testpass123', organization=self.org)
        response = self.client.get('/api/auth/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_create_user(self):
        self._auth()
        data = {
            'username': 'created',
            'email': 'created@example.com',
            'password': 'testpass123',
        }
        response = self.client.post('/api/auth/users/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_user(self):
        self._auth()
        other = User.objects.create_user(username='updateable', password='testpass123', organization=self.org)
        response = self.client.patch(f'/api/auth/users/{other.id}/', {'first_name': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        other.refresh_from_db()
        self.assertEqual(other.first_name, 'Updated')

    def test_delete_user(self):
        self._auth()
        other = User.objects.create_user(username='deletable', password='testpass123', organization=self.org)
        response = self.client.delete(f'/api/auth/users/{other.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_change_password_success(self):
        self._auth()
        response = self.client.post('/api/auth/users/change_password/', {
            'old_password': 'testpass123',
            'new_password': 'newpass1234',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass1234'))

    def test_change_password_wrong_old(self):
        self._auth()
        response = self.client.post('/api/auth/users/change_password/', {
            'old_password': 'wrongpass',
            'new_password': 'newpass1234',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_short_new(self):
        self._auth()
        response = self.client.post('/api/auth/users/change_password/', {
            'old_password': 'testpass123',
            'new_password': 'short',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OrganizationTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name='Test Org')
        self.user = User.objects.create_user(
            username='admin', password='testpass123',
            organization=self.org, is_organization_admin=True,
        )
        self._auth()

    def _auth(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'admin', 'password': 'testpass123',
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')

    def test_list_organizations(self):
        response = self.client.get('/api/auth/organizations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_create_organization(self):
        response = self.client.post('/api/auth/organizations/', {'name': 'New Org'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Org')

    def test_retrieve_organization(self):
        response = self.client.get(f'/api/auth/organizations/{self.org.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Org')

    def test_update_organization(self):
        response = self.client.patch(f'/api/auth/organizations/{self.org.id}/', {'name': 'Updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, 'Updated')

    def test_delete_organization(self):
        response = self.client.delete(f'/api/auth/organizations/{self.org.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
