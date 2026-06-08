from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.reports.models import Report, ReportTemplate
from apps.reports.serializers import (
    ReportSerializer, ReportTemplateSerializer, ReportGenerateSerializer,
)
from apps.reports.tasks import generate_report


class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ReportGenerateSerializer
        return ReportSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Report.objects.all()
        if user.organization:
            qs = qs.filter(organization=user.organization)
        report_type = self.request.query_params.get('report_type')
        if report_type:
            qs = qs.filter(report_type=report_type)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ReportGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        filters = data.get('filters', {})
        if request.user.organization:
            filters['organization_id'] = str(request.user.organization.id)

        report = Report.objects.create(
            organization=request.user.organization,
            title=data['title'],
            report_type=data['report_type'],
            file_type=data.get('file_type', 'pdf'),
            filters=filters,
        )

        generate_report.delay(report.id)

        return Response(
            ReportSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def regenerate(self, request, pk=None):
        report = self.get_object()
        report.status = 'generating'
        report.error_message = ''
        report.save(update_fields=['status', 'error_message'])
        generate_report.delay(report.id)
        return Response({'status': 'regenerating'})


class ReportTemplateViewSet(viewsets.ModelViewSet):
    queryset = ReportTemplate.objects.filter(is_active=True)
    serializer_class = ReportTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name']
