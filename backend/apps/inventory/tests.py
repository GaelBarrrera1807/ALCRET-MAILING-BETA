from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.inventory.models import InventoryItem
from apps.users.models import Organization

User = get_user_model()


class InventoryItemEndpointTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.org = Organization.objects.create(name='Org Test')
        self.admin = User.objects.create_superuser(
            username='admin', password='testpass123', email='admin@test.mx',
        )
        self.user = User.objects.create_user(
            username='regular', password='testpass123',
            organization=self.org,
        )

    def test_requiere_staff(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/inventory/items/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_lista_inventario_con_paginacion(self):
        self.client.force_authenticate(user=self.admin)
        InventoryItem.objects.create(
            organization=self.org, sku_o_vin='VIN-A', producto_id='P1',
            nombre_unidad='Caja', cantidad_disponible=3, tipo_movimiento='entrada',
        )
        response = self.client.get('/api/v1/inventory/items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['sku_o_vin'], 'VIN-A')

    def test_filtra_por_almacen(self):
        self.client.force_authenticate(user=self.admin)
        InventoryItem.objects.create(
            organization=self.org, sku_o_vin='VIN-A', almacen_id='ALM-1',
            producto_id='P1',
        )
        InventoryItem.objects.create(
            organization=self.org, sku_o_vin='VIN-B', almacen_id='ALM-2',
            producto_id='P2',
        )
        response = self.client.get('/api/v1/inventory/items/?almacen_id=ALM-1')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['sku_o_vin'], 'VIN-A')