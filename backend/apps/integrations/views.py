import json
import logging

from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.integrations.models import InboundSyncLog
from apps.integrations.security import require_alcret_signature
from apps.integrations.serializers import InboundSyncLogSerializer
from apps.integrations.tasks import procesar_evento_alcret

logger = logging.getLogger(__name__)


class InboundSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = InboundSyncLogSerializer
    search_fields = ['evento', 'error_message']
    ordering_fields = ['created_at', 'updated_at', 'evento']

    def get_queryset(self):
        qs = InboundSyncLog.objects.all()
        estado = self.request.query_params.get('estado')
        evento = self.request.query_params.get('evento')
        if estado:
            qs = qs.filter(estado=estado)
        if evento:
            qs = qs.filter(evento__icontains=evento)
        return qs


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@require_alcret_signature
def alcret_webhook(request):
    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return Response(
            {'error': 'JSON inválido en el body'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not isinstance(payload, dict):
        return Response(
            {'error': 'El payload debe ser un objeto JSON'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    evento = payload.get('evento') or payload.get('event_type') or ''
    if not evento:
        return Response(
            {'error': 'El campo "evento" es requerido'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = payload.get('data', {}) or {}
    organization_id = (
        payload.get('organizacion')
        or data.get('organizacion')
        or data.get('organization_id')
    )

    log = InboundSyncLog.objects.create(
        organization_id=organization_id if organization_id else None,
        evento=evento,
        payload=payload,
        estado=InboundSyncLog.Estado.PENDIENTE,
    )

    procesar_evento_alcret.delay(str(log.id))

    return Response({
        'status': 'recibido',
        'log_id': str(log.id),
        'evento': evento,
    }, status=status.HTTP_200_OK)