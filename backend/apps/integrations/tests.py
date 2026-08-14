import json
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.core.models import Company, CompanyContact
from apps.integrations.models import InboundSyncLog
from apps.integrations.security import compute_signature
from apps.integrations.tasks import procesar_evento_alcret
from apps.inventory.models import InventoryItem
from apps.leads.models import Lead
from apps.users.models import Organization

User = get_user_model()

WEBHOOK_URL = '/api/v1/integrations/alcret/webhook/'
SECRET = 'test-hmac-secret'


@override_settings(ALCRET_HMAC_SECRET=SECRET)
class AlcretWebhookSignatureTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def _headers(self, signature, timestamp=None):
        headers = {'HTTP_X_SIGNATURE': signature}
        if timestamp is not None:
            headers['HTTP_X_TIMESTAMP'] = str(timestamp)
        return headers

    def test_rechaza_firma_hmac_invalida(self):
        payload = json.dumps({'evento': 'cliente.creado', 'data': {'nombre': 'ACME'}})
        response = self.client.post(
            WEBHOOK_URL,
            data=payload,
            content_type='application/json',
            **self._headers('firma-incorrecta', int(time.time())),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(InboundSyncLog.objects.count(), 0)

    def test_rechaza_ausencia_de_headers(self):
        payload = json.dumps({'evento': 'cliente.creado', 'data': {'nombre': 'ACME'}})
        response = self.client.post(
            WEBHOOK_URL,
            data=payload,
            content_type='application/json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_acepta_firma_valida_y_registra_payload(self):
        payload = {
            'evento': 'cliente.creado',
            'data': {'nombre': 'ACME Industrial', 'email': 'contacto@acme.mx'},
        }
        raw = json.dumps(payload)
        signature = compute_signature(SECRET, raw.encode('utf-8'))

        with patch('apps.integrations.views.procesar_evento_alcret.delay') as mock_task:
            response = self.client.post(
                WEBHOOK_URL,
                data=raw,
                content_type='application/json',
                **self._headers(signature, int(time.time())),
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'recibido')

        log = InboundSyncLog.objects.get()
        self.assertEqual(log.evento, 'cliente.creado')
        self.assertEqual(log.estado, InboundSyncLog.Estado.PENDIENTE)
        self.assertEqual(log.payload['data']['nombre'], 'ACME Industrial')
        mock_task.assert_called_once_with(str(log.id))

    def test_rechaza_timestamp_fuera_de_ventana(self):
        payload = json.dumps({'evento': 'cliente.creado', 'data': {'nombre': 'ACME'}})
        signature = compute_signature(SECRET, payload.encode('utf-8'))
        response = self.client.post(
            WEBHOOK_URL,
            data=payload,
            content_type='application/json',
            **self._headers(signature, int(time.time()) - 3600),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


@override_settings(ALCRET_HMAC_SECRET=SECRET)
class ProcesarEventoAlcretTests(APITestCase):
    def setUp(self):
        self.org = Organization.objects.create(name='ERP ALCRET')

    def _crear_log(self, evento, data):
        return InboundSyncLog.objects.create(
            organization=self.org,
            evento=evento,
            payload={'evento': evento, 'data': data},
            estado=InboundSyncLog.Estado.PENDIENTE,
        )

    def test_cliente_creado_crea_company_y_contacto(self):
        log = self._crear_log('cliente.creado', {
            'nombre': 'Fabrica de Tractores SA',
            'rfc': 'FTS920101AB1',
            'email': 'ventas@tractores.mx',
            'telefono': '5551234567',
            'contacto_nombre': 'Juan Perez',
            'contacto_email': 'juan@tractores.mx',
        })
        resultado = procesar_evento_alcret.apply(args=[str(log.id)]).get()

        self.assertEqual(resultado['tipo'], 'cliente')
        company = Company.objects.get(rfc='FTS920101AB1')
        self.assertTrue(company.is_client)
        contact = CompanyContact.objects.get(company=company)
        self.assertEqual(contact.email, 'juan@tractores.mx')
        log.refresh_from_db()
        self.assertEqual(log.estado, InboundSyncLog.Estado.PROCESADO)

    def test_cotizacion_registrada_crea_oportunidad(self):
        log = self._crear_log('cotizacion.registrada', {
            'nombre': 'Maquilas del Norte',
            'rfc': 'MDN980101AB1',
            'etapa': 'cotizacion',
            'monto': '2,500,000',
            'esquema': 'arrendamiento puro',
            'unidad_interes': 'Tractocamión Kenworth T880',
        })
        resultado = procesar_evento_alcret.apply(args=[str(log.id)]).get()

        self.assertEqual(resultado['tipo'], 'oportunidad')
        self.assertEqual(resultado['stage'], 'cotizacion_enviada')
        lead = Lead.objects.get(company__rfc='MDN980101AB1')
        self.assertEqual(lead.status, 'proposal')
        self.assertEqual(lead.stage, 'cotizacion_enviada')
        self.assertEqual(lead.esquema, 'arrendamiento_puro')
        self.assertEqual(lead.unidad_interes, 'Tractocamión Kenworth T880')
        self.assertEqual(float(lead.monto_total), 2500000.0)
        self.assertEqual(lead.organization, self.org)

    def test_venta_ganada_actualiza_oportunidad(self):
        log1 = self._crear_log('cotizacion.registrada', {
            'nombre': 'Maquilas del Norte',
            'rfc': 'MDN980101AB1',
            'etapa': 'cotizacion',
        })
        procesar_evento_alcret.apply(args=[str(log1.id)]).get()

        log2 = self._crear_log('venta.ganada', {
            'nombre': 'Maquilas del Norte',
            'rfc': 'MDN980101AB1',
            'etapa': 'ganada',
        })
        procesar_evento_alcret.apply(args=[str(log2.id)]).get()

        lead = Lead.objects.get(company__rfc='MDN980101AB1')
        self.assertEqual(lead.status, 'won')
        self.assertEqual(Lead.objects.filter(company__rfc='MDN980101AB1').count(), 1)

    def test_stock_actualizado_persiste_inventario(self):
        log = self._crear_log('stock.actualizado', {
            'almacen_id': 'ALM-01',
            'producto_id': 'TRAC-VNL860',
            'sku_o_vin': 'VIN1234567890',
            'nombre_unidad': 'Tractocamión Volvo VNL 860',
            'cantidad_disponible': 1,
            'tipo_movimiento': 'entrada',
        })
        resultado = procesar_evento_alcret.apply(args=[str(log.id)]).get()

        self.assertEqual(resultado['tipo'], 'stock')
        self.assertTrue(resultado['sincronizado'])
        item = InventoryItem.objects.get(sku_o_vin='VIN1234567890')
        self.assertEqual(item.cantidad_disponible, 1)
        self.assertEqual(item.almacen_id, 'ALM-01')
        self.assertEqual(item.tipo_movimiento, 'entrada')
        log.refresh_from_db()
        self.assertEqual(log.estado, InboundSyncLog.Estado.PROCESADO)

    def test_stock_actualizado_hace_upsert(self):
        log1 = self._crear_log('inventario.actualizado', {
            'sku_o_vin': 'VIN999', 'producto_id': 'P1',
            'cantidad_disponible': 5, 'tipo_movimiento': 'entrada',
        })
        procesar_evento_alcret.apply(args=[str(log1.id)]).get()

        log2 = self._crear_log('inventario.actualizado', {
            'sku_o_vin': 'VIN999', 'producto_id': 'P1',
            'cantidad_disponible': 3, 'tipo_movimiento': 'salida',
        })
        procesar_evento_alcret.apply(args=[str(log2.id)]).get()

        self.assertEqual(InventoryItem.objects.count(), 1)
        item = InventoryItem.objects.get(sku_o_vin='VIN999')
        self.assertEqual(item.cantidad_disponible, 3)
        self.assertEqual(item.tipo_movimiento, 'salida')

    def test_evento_desconocido_no_falla(self):
        log = self._crear_log('nomina.emitida', {})
        resultado = procesar_evento_alcret.apply(args=[str(log.id)]).get()
        self.assertIn('nota', resultado)
        log.refresh_from_db()
        self.assertEqual(log.estado, InboundSyncLog.Estado.PROCESADO)


class InboundSyncLogEndpointTests(APITestCase):
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

    def test_requiere_usuario_staff(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/integrations/logs/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_lista_logs_con_paginacion(self):
        self.client.force_authenticate(user=self.admin)
        for i in range(3):
            InboundSyncLog.objects.create(
                evento='cliente.creado', payload={}, estado='pendiente',
            )
        response = self.client.get('/api/v1/integrations/logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 3)

    def test_filtra_por_estado(self):
        self.client.force_authenticate(user=self.admin)
        InboundSyncLog.objects.create(
            evento='cliente.creado', payload={}, estado='pendiente',
        )
        InboundSyncLog.objects.create(
            evento='cotizacion.registrada', payload={}, estado='error',
        )
        response = self.client.get('/api/v1/integrations/logs/?estado=error')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['estado'], 'error')

    def test_filtra_por_evento(self):
        self.client.force_authenticate(user=self.admin)
        InboundSyncLog.objects.create(
            evento='cliente.creado', payload={}, estado='pendiente',
        )
        InboundSyncLog.objects.create(
            evento='stock.actualizado', payload={}, estado='pendiente',
        )
        response = self.client.get('/api/v1/integrations/logs/?evento=stock')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['evento'], 'stock.actualizado')
