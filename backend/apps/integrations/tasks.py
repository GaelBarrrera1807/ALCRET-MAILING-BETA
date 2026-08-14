import logging

from celery import shared_task
from django.db import transaction

from apps.integrations.models import InboundSyncLog

logger = logging.getLogger(__name__)

CLIENTE_PREFIXES = ('cliente.', 'contacto.')
OPORTUNIDAD_PREFIXES = ('cotizacion.', 'oportunidad.', 'venta.', 'pedido.')
STOCK_PREFIXES = ('stock.', 'inventario.')

OPORTUNIDAD_STATUS_MAP = {
    'nueva': 'new',
    'cotizacion': 'proposal',
    'negociacion': 'negotiation',
    'ganada': 'won',
    'won': 'won',
    'perdida': 'lost',
    'lost': 'lost',
}

OPORTUNIDAD_STAGE_MAP = {
    'nueva': 'nuevo_lead',
    'cotizacion': 'cotizacion_enviada',
    'negociacion': 'mesa_credito',
    'ganada': 'ganado',
    'won': 'ganado',
    'perdida': 'perdido',
    'lost': 'perdido',
}

ESQUEMA_NORMALIZATION = {
    'contado': 'contado',
    'ap': 'arrendamiento_puro',
    'arrendamiento': 'arrendamiento_puro',
    'arrendamiento puro': 'arrendamiento_puro',
    'arrendamiento financiero': 'financiamiento',
    'leasing': 'financiamiento',
    'financiamiento': 'financiamiento',
    'credito': 'financiamiento',
    'crédito': 'financiamiento',
}


def _get(data, *keys, default=''):
    for key in keys:
        value = data.get(key)
        if value not in (None, ''):
            return str(value).strip()
    return default


def _get_evento_es_cliente(evento):
    return evento.startswith(CLIENTE_PREFIXES)


def _get_evento_es_oportunidad(evento):
    return evento.startswith(OPORTUNIDAD_PREFIXES)


def _get_evento_es_stock(evento):
    return evento.startswith(STOCK_PREFIXES)


def _normalizar_esquema(data):
    raw = _get(data, 'esquema', 'plan', 'modalidad', 'producto')
    key = raw.strip().lower()
    return ESQUEMA_NORMALIZATION.get(key)


def _parsear_monto(data):
    raw = _get(data, 'monto', 'importe', 'total')
    try:
        return float(raw.replace(',', ''))
    except (TypeError, ValueError, AttributeError):
        return None


def _resolver_organizacion(payload, log):
    from apps.users.models import Organization

    org_id = (
        log.organization_id
        or (payload.get('data') or {}).get('organizacion')
        or (payload.get('data') or {}).get('organization_id')
    )
    if not org_id:
        return None
    try:
        return Organization.objects.get(id=org_id)
    except (Organization.DoesNotExist, ValueError):
        return None


def _buscar_company(data, organization, nombre, rfc, email):
    from apps.core.models import Company

    qs = Company.objects.filter(organization=organization)
    if rfc:
        company = qs.filter(rfc=rfc).first()
        if company:
            return company
    if nombre:
        company = qs.filter(name__iexact=nombre).first()
        if company:
            return company
    if email:
        company = qs.filter(email__iexact=email).first()
        if company:
            return company
    return None


def _upsert_company(payload, log, es_cliente=False):
    from apps.core.models import Company

    data = payload.get('data', {}) or {}
    nombre = _get(data, 'nombre', 'razon_social', 'name', 'cliente', 'empresa')
    if not nombre:
        raise ValueError('El evento no incluye nombre/razón social del cliente')

    rfc = _get(data, 'rfc', 'clave_cliente', 'codigo_cliente')
    email = _get(data, 'email', 'correo', 'correo_electronico')
    organization = _resolver_organizacion(payload, log)

    company = _buscar_company(data, organization, nombre, rfc, email)
    if company is None:
        company = Company.objects.create(
            organization=organization,
            name=nombre,
            rfc=rfc,
            email=email,
            source='alcret',
            status='analyzed',
            is_lead=not es_cliente,
            is_client=es_cliente,
        )

    updates = {
        'rfc': rfc,
        'business_name': _get(data, 'razon_social', 'business_name', default=company.business_name),
        'email': email or company.email,
        'phone': _get(data, 'telefono', 'phone', default=company.phone),
        'address': _get(data, 'direccion', 'address', default=company.address),
        'city': _get(data, 'ciudad', 'city', default=company.city),
        'state': _get(data, 'estado', 'state', default=company.state),
        'country': _get(data, 'pais', 'country', default=company.country or 'México'),
        'website': _get(data, 'website', 'sitio_web', default=company.website),
        'source': 'alcret',
        'status': 'analyzed',
    }
    if es_cliente:
        updates['is_client'] = True
        updates['is_lead'] = False
    for field, value in updates.items():
        if value not in (None, ''):
            setattr(company, field, value)
    company.save()

    contact = _upsert_contact(company, data)
    return company, contact


def _upsert_contact(company, data):
    from apps.core.models import CompanyContact

    nombre_contacto = _get(data, 'contacto_nombre', 'contact_name', 'nombre_contacto')
    email_contacto = _get(data, 'contacto_email', 'contact_email', 'correo_contacto')
    if not nombre_contacto and not email_contacto:
        return None

    qs = CompanyContact.objects.filter(company=company)
    if email_contacto:
        contact = qs.filter(email__iexact=email_contacto).first()
    else:
        contact = qs.filter(name__iexact=nombre_contacto).first()
    if contact is None:
        contact = CompanyContact.objects.create(
            company=company,
            name=nombre_contacto or (email_contacto or 'Sin nombre'),
            email=email_contacto,
            phone=_get(data, 'contacto_telefono', 'contact_phone'),
            position=_get(data, 'cargo', 'position'),
            is_primary=True,
        )
    else:
        if nombre_contacto:
            contact.name = nombre_contacto
        if email_contacto:
            contact.email = email_contacto
        if _get(data, 'cargo', 'position'):
            contact.position = _get(data, 'cargo', 'position')
        contact.save()
    return contact


def _procesar_cliente(payload, log):
    company, contact = _upsert_company(payload, log, es_cliente=True)
    return {
        'tipo': 'cliente',
        'company_id': str(company.id),
        'contact_id': str(contact.id) if contact else None,
        'contacto': bool(contact),
    }


def _procesar_oportunidad(payload, log):
    from apps.leads.models import Lead

    data = payload.get('data', {}) or {}
    evento = payload.get('evento', '') or payload.get('event_type', '')

    company, contact = _upsert_company(payload, log, es_cliente=False)

    etapa = _get(data, 'etapa', 'estatus', default=evento.split('.')[0])
    status = OPORTUNIDAD_STATUS_MAP.get(etapa, 'qualified')
    stage = OPORTUNIDAD_STAGE_MAP.get(etapa, 'nuevo_lead')

    monto = _get(data, 'monto', 'importe', 'total')
    try:
        score = min(100, 60 + int(float(monto)) // 10000)
    except (TypeError, ValueError):
        score = 60

    monto_total = _parsear_monto(data)
    esquema = _normalizar_esquema(data)
    unidad_interes = _get(data, 'unidad_interes', 'unidad', 'producto_interes', 'equipo')

    lead = Lead.objects.filter(company=company).first()
    if lead is None:
        lead = Lead.objects.create(
            company=company,
            contact=contact,
            organization=company.organization,
            score=score,
            priority='alta',
            status=status,
            stage=stage,
            detected_sector=_get(data, 'sector', 'giro'),
            reason='ERP ALCRET - sincronización inbound',
            auto_created=True,
        )
    else:
        lead.status = status
        lead.score = score
        lead.priority = 'alta'
        if contact and not lead.contact_id:
            lead.contact = contact
        lead.reason = 'ERP ALCRET - sincronización inbound'
        lead.save()

    if monto_total is not None:
        lead.monto_total = monto_total
    if esquema:
        lead.esquema = esquema
    if unidad_interes:
        lead.unidad_interes = unidad_interes
    lead.save()

    return {
        'tipo': 'oportunidad',
        'company_id': str(company.id),
        'lead_id': str(lead.id),
        'status': status,
        'stage': stage,
    }


def _procesar_stock(payload, log):
    from apps.inventory.models import InventoryItem

    data = payload.get('data', {}) or {}
    sku = _get(data, 'sku_o_vin', 'sku', 'vin')
    producto = _get(data, 'producto_id', 'producto', 'id_producto')
    almacen = _get(data, 'almacen_id', 'almacen', 'id_almacen')

    if not sku and not producto:
        return {
            'tipo': 'stock',
            'sincronizado': False,
            'nota': 'Inventario: falta sku_o_vin y producto_id',
        }

    nombre = _get(data, 'nombre_unidad', 'nombre', 'descripcion')
    try:
        cantidad = int(float(_get(data, 'cantidad_disponible', 'cantidad', default='0')))
    except (TypeError, ValueError):
        cantidad = 0
    tipo = _get(data, 'tipo_movimiento', 'movimiento', default='ajuste')

    organization = _resolver_organizacion(payload, log)

    item = None
    if sku:
        item = InventoryItem.objects.filter(
            organization=organization, sku_o_vin=sku,
        ).first()
    if item is None and producto:
        item = InventoryItem.objects.filter(
            organization=organization,
            producto_id=producto,
            almacen_id=almacen,
        ).first()

    if item is None:
        item = InventoryItem.objects.create(
            organization=organization,
            almacen_id=almacen,
            producto_id=producto,
            sku_o_vin=sku,
            nombre_unidad=nombre,
            cantidad_disponible=cantidad,
            tipo_movimiento=tipo,
        )
    else:
        if sku:
            item.sku_o_vin = sku
        if producto:
            item.producto_id = producto
        if almacen:
            item.almacen_id = almacen
        if nombre:
            item.nombre_unidad = nombre
        item.cantidad_disponible = cantidad
        item.tipo_movimiento = tipo
        item.save()

    return {
        'tipo': 'stock',
        'inventory_id': str(item.id),
        'sku_o_vin': sku or '',
        'producto_id': producto or '',
        'sincronizado': True,
    }


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def procesar_evento_alcret(self, log_id):
    try:
        log = InboundSyncLog.objects.get(id=log_id)
    except InboundSyncLog.DoesNotExist:
        logger.error(f'InboundSyncLog {log_id} no encontrado')
        return {'error': 'InboundSyncLog not found'}

    if log.estado == InboundSyncLog.Estado.PROCESADO:
        return {'log_id': str(log.id), 'estado': log.estado, 'skipped': True}

    log.estado = InboundSyncLog.Estado.PROCESADO
    log.error_message = ''
    log.save(update_fields=['estado', 'error_message'])

    evento = log.evento
    try:
        if _get_evento_es_cliente(evento):
            with transaction.atomic():
                resultado = _procesar_cliente(log.payload, log)
        elif _get_evento_es_oportunidad(evento):
            with transaction.atomic():
                resultado = _procesar_oportunidad(log.payload, log)
        elif _get_evento_es_stock(evento):
            resultado = _procesar_stock(log.payload, log)
        else:
            resultado = {
                'nota': f'Evento sin handler: {evento}',
                'procesado': False,
            }
        logger.info(f'InboundSyncLog {log.id} procesado: {resultado}')
        return {'log_id': str(log.id), 'estado': log.estado, **resultado}
    except Exception as e:
        logger.exception(f'Error procesando InboundSyncLog {log.id}: {e}')
        log.estado = InboundSyncLog.Estado.ERROR
        log.error_message = str(e)[:500]
        log.save(update_fields=['estado', 'error_message'])
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (self.request.retries + 1))
        return {
            'log_id': str(log.id),
            'estado': log.estado,
            'error': str(e)[:500],
        }
