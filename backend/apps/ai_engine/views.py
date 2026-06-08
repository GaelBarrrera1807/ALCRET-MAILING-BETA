from rest_framework import viewsets, permissions

from apps.ai_engine.models import AnalysisRequest, AnalysisResult, PromptTemplate
from apps.ai_engine.serializers import (
    AnalysisRequestSerializer, AnalysisResultSerializer, PromptTemplateSerializer,
)


class AnalysisRequestViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnalysisRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        qs = AnalysisRequest.objects.select_related('company')
        if user.organization:
            qs = qs.filter(organization=user.organization)
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs


class AnalysisResultViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AnalysisResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['score', 'created_at']

    def get_queryset(self):
        user = self.request.user
        qs = AnalysisResult.objects.select_related('company')
        if user.organization:
            qs = qs.filter(company__organization=user.organization)
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs


class PromptTemplateViewSet(viewsets.ModelViewSet):
    queryset = PromptTemplate.objects.filter(is_active=True)
    serializer_class = PromptTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name']
