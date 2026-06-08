from rest_framework import status
from rest_framework.test import APITestCase


class HealthCheckTests(APITestCase):
    def test_health_check_returns_ok(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(response.data['service'], 'industrial-prospecting-api')

    def test_health_check_allows_anonymous(self):
        response = self.client.get('/api/health/')
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
