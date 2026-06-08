from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.leads.models import Lead, LeadNote
from apps.leads.serializers import (
    LeadSerializer, LeadNoteSerializer, LeadBatchUpdateSerializer,
)


class LeadViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['company__name', 'detected_sector', 'notes']
    ordering_fields = ['score', 'priority', 'status', 'created_at']

    def get_serializer_class(self):
        return LeadSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Lead.objects.select_related('company', 'organization').prefetch_related('notes_list')
        if user.organization:
            qs = qs.filter(organization=user.organization)
        status_filter = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        min_score = self.request.query_params.get('min_score')
        assigned_to = self.request.query_params.get('assigned_to')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if priority:
            qs = qs.filter(priority=priority)
        if min_score:
            qs = qs.filter(score__gte=int(min_score))
        if assigned_to:
            qs = qs.filter(assigned_to_id=assigned_to)
        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        serializer = LeadBatchUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        if not user.organization:
            return Response({'error': 'Usuario sin organización'}, status=status.HTTP_403_FORBIDDEN)
        leads = Lead.objects.filter(
            id__in=data['lead_ids'], organization=user.organization
        )
        update_fields = {}
        if 'status' in data:
            update_fields['status'] = data['status']
        if 'priority' in data:
            update_fields['priority'] = data['priority']
        if 'assigned_to' in data:
            update_fields['assigned_to_id'] = data['assigned_to']
        if update_fields:
            leads.update(**update_fields)
        return Response({'updated': leads.count()})


class LeadNoteViewSet(viewsets.ModelViewSet):
    serializer_class = LeadNoteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return LeadNote.objects.none()
        qs = LeadNote.objects.select_related('author', 'lead').filter(
            lead__organization=user.organization
        )
        lead_id = self.request.query_params.get('lead')
        if lead_id:
            qs = qs.filter(lead_id=lead_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
