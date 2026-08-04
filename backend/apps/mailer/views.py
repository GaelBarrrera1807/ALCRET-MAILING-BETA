import json
import logging

import requests
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import parsers, permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from apps.mailer.models import (
    EmailTemplate, EmailRecipient, EmailCampaign,
    CampaignSend, EmailEvent, TemplateImage,
)
from apps.mailer.serializers import (
    EmailTemplateSerializer, EmailTemplatePreviewSerializer,
    EmailRecipientSerializer, EmailRecipientBulkSerializer,
    EmailCampaignSerializer, EmailCampaignCreateSerializer,
    CampaignSendSerializer, EmailEventSerializer,
    TemplateImageSerializer,
)
from apps.mailer.services.template_service import render_template
from apps.mailer.services.tracking_service import (
    generate_tracking_pixel, process_open, process_click,
    process_unsubscribe, process_ses_notification,
)

logger = logging.getLogger(__name__)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'subject']
    ordering_fields = ['name', 'use_count', 'created_at']

    def get_serializer_class(self):
        return EmailTemplateSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return EmailTemplate.objects.none()
        return EmailTemplate.objects.filter(organization=user.organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        template = self.get_object()
        serializer = EmailTemplatePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        context = serializer.validated_data.get('context', {})
        try:
            result = render_template(template, context)
            return Response(result)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TemplateImageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TemplateImageSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return TemplateImage.objects.none()
        return TemplateImage.objects.filter(organization=user.organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class EmailRecipientViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['email', 'first_name', 'last_name', 'company_name']

    def get_serializer_class(self):
        if self.action == 'bulk':
            return EmailRecipientBulkSerializer
        return EmailRecipientSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return EmailRecipient.objects.none()
        qs = EmailRecipient.objects.filter(organization=user.organization)
        source = self.request.query_params.get('source')
        is_active = self.request.query_params.get('is_active')
        lead_id = self.request.query_params.get('lead_id')
        if source:
            qs = qs.filter(source=source)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == 'true')
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.unsubscribed_at = timezone.now()
        instance.save(update_fields=['is_active', 'unsubscribed_at'])

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        serializer = EmailRecipientBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        emails = serializer.validated_data['recipients']
        source = serializer.validated_data.get('source', 'manual')
        org = request.user.organization
        if not org:
            return Response(
                {'error': 'Usuario sin organización'},
                status=status.HTTP_403_FORBIDDEN,
            )

        created = []
        skipped = []
        for email in emails:
            _, was_created = EmailRecipient.objects.get_or_create(
                email=email,
                organization=org,
                defaults={'source': source},
            )
            if was_created:
                created.append(email)
            else:
                skipped.append(email)

        return Response({
            'created': len(created),
            'skipped': len(skipped),
            'total': len(emails),
        })


class EmailCampaignViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name']
    ordering_fields = ['name', 'status', 'created_at', 'sent_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return EmailCampaignCreateSerializer
        return EmailCampaignSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return EmailCampaign.objects.none()
        qs = EmailCampaign.objects.filter(organization=user.organization).select_related('template')
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        campaign = self.get_object()
        if campaign.status != 'draft':
            return Response(
                {'error': f'La campaña está en estado {campaign.status}, no se puede enviar'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not campaign.template:
            return Response(
                {'error': 'La campaña no tiene una plantilla asignada'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = request.user.organization
        if not org:
            return Response(
                {'error': 'Usuario sin organización'},
                status=status.HTTP_403_FORBIDDEN,
            )

        recipients = EmailRecipient.objects.filter(
            organization=org,
            is_active=True,
        )

        filter_map = {
            'all': lambda qs: qs,
            'internal': lambda qs: qs.filter(source__in=['lead_generation', 'csv_upload']),
            'external': lambda qs: qs.exclude(source__in=['lead_generation', 'csv_upload']),
            'manual': lambda qs: qs.filter(source='manual'),
        }
        filter_fn = filter_map.get(campaign.source_filter, filter_map['all'])
        recipients = filter_fn(recipients)

        total = recipients.count()
        if total == 0:
            return Response(
                {'error': 'No hay destinatarios activos que coincidan con el filtro'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaign.total_recipients = total
        campaign.status = 'scheduled'
        campaign.save(update_fields=['total_recipients', 'status'])

        sends = []
        for recipient in recipients:
            sends.append(CampaignSend(
                campaign=campaign,
                recipient=recipient,
            ))

        CampaignSend.objects.bulk_create(sends, ignore_conflicts=True)

        from apps.mailer.tasks.send_campaign import send_campaign_task
        send_campaign_task.delay(str(campaign.id))

        return Response({
            'status': 'scheduled',
            'campaign_id': str(campaign.id),
            'total_recipients': total,
        })

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        campaign = self.get_object()
        sends = CampaignSend.objects.filter(campaign=campaign)
        events = EmailEvent.objects.filter(campaign_send__campaign=campaign)

        status_counts = {}
        for s in sends.values('status').annotate(count=Count('id')):
            status_counts[s['status']] = s['count']

        events_by_type = {}
        for e in events.values('event_type').annotate(count=Count('id')):
            events_by_type[e['event_type']] = e['count']

        return Response({
            'campaign_id': str(campaign.id),
            'status': campaign.status,
            'total_recipients': campaign.total_recipients,
            'sent': campaign.sent_count,
            'opens': campaign.open_count,
            'clicks': campaign.click_count,
            'bounces': campaign.bounce_count,
            'unsubscribes': campaign.unsubscribe_count,
            'by_status': status_counts,
            'by_event': events_by_type,
        })

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        campaign = self.get_object()
        if not campaign.template:
            return Response(
                {'error': 'La campaña no tiene plantilla asignada'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        org = request.user.organization
        if not org:
            return Response(
                {'error': 'Usuario sin organización'},
                status=status.HTTP_403_FORBIDDEN,
            )

        sample = EmailRecipient.objects.filter(
            organization=org,
        ).order_by('?').first()

        if not sample:
            return Response({
                'subject': campaign.subject or campaign.template.subject,
                'body_html': campaign.body_html or campaign.template.body_html,
                'note': 'Sin destinatario de muestra',
            })

        context = {
            'first_name': sample.first_name,
            'company': sample.company_name,
            'sector': sample.sector,
            'email': sample.email,
            'tracking_id': 'preview-sample',
            'unsubscribe_url': '#',
        }

        try:
            result = render_template(campaign.template, context)
            return Response({
                'subject': campaign.subject or result['subject'],
                'body_html': campaign.body_html or result['body_html'],
                'sample_recipient': sample.email,
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def tracking_pixel(request, tracking_id):
    process_open(str(tracking_id), {
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'ip_address': request.META.get('REMOTE_ADDR'),
    })
    pixel = generate_tracking_pixel()
    return HttpResponse(pixel, content_type='image/gif')


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def tracking_click(request, tracking_id):
    target_url = request.query_params.get('url', '')
    if not target_url:
        return HttpResponse('Missing URL', status=400)

    result = process_click(str(tracking_id), target_url, {
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'ip_address': request.META.get('REMOTE_ADDR'),
    })

    if result is None:
        logger.warning(f'Click tracking falló para ID: {tracking_id}')

    return HttpResponseRedirect(redirect_to=target_url)


@csrf_exempt
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def ses_webhook(request):
    try:
        payload = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON body'}, status=400)

    message_type = payload.get('Type')

    if message_type == 'SubscriptionConfirmation':
        subscribe_url = payload.get('SubscribeURL')
        if not subscribe_url:
            return JsonResponse({'error': 'Missing SubscribeURL'}, status=400)
        try:
            response = requests.get(subscribe_url, timeout=30)
            response.raise_for_status()
            logger.info(f'SNS SubscriptionConfirmation confirmada: HTTP {response.status_code}')
            return JsonResponse({'status': 'subscription_confirmed'})
        except Exception as e:
            logger.error(f'Error confirmando suscripción SNS: {e}', exc_info=True)
            return JsonResponse({'error': 'Fallo al confirmar suscripción'}, status=500)

    if message_type == 'Notification':
        raw_message = payload.get('Message')
        try:
            notification = json.loads(raw_message) if isinstance(raw_message, str) else raw_message
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid Message JSON'}, status=400)
        result = process_ses_notification(notification)
        return JsonResponse({'status': 'processed', 'result': result})

    if message_type == 'UnsubscribeConfirmation':
        logger.info('SNS UnsubscribeConfirmation recibido')
        return JsonResponse({'status': 'unsubscribe_confirmation'})

    return JsonResponse({'error': f'Tipo SNS no soportado: {message_type}'}, status=400)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def unsubscribe(request, tracking_id):
    process_unsubscribe(str(tracking_id), {
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'ip_address': request.META.get('REMOTE_ADDR'),
    })
    html = (
        '<html><body style="font-family:sans-serif;text-align:center;padding:40px;">'
        '<h2>Has sido dado de baja correctamente</h2>'
        '<p>Ya no recibirás correos de esta lista.</p>'
        '</body></html>'
    )
    return HttpResponse(html, content_type='text/html; charset=utf-8')
