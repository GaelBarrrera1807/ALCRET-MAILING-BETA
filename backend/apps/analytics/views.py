from django.db.models import Count, Avg, Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.analytics.models import DashboardMetric, ProcessingStats
from apps.analytics.serializers import DashboardMetricSerializer, ProcessingStatsSerializer
from apps.core.models import Company
from apps.leads.models import Lead


class DashboardMetricViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DashboardMetricSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = DashboardMetric.objects.all()
        if user.organization:
            qs = qs.filter(organization=user.organization)
        metric_type = self.request.query_params.get('metric_type')
        if metric_type:
            qs = qs.filter(metric_type=metric_type)
        days = self.request.query_params.get('days')
        if days:
            from datetime import datetime, timedelta
            from django.utils import timezone
            cutoff = timezone.now().date() - timedelta(days=int(days))
            qs = qs.filter(date__gte=cutoff)
        return qs


class ProcessingStatsViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProcessingStatsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ProcessingStats.objects.all()
        if user.organization:
            qs = qs.filter(organization=user.organization)
        return qs


class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _get_org_filter(self, user):
        if user.organization:
            return {'organization': user.organization}
        return {}

    @action(detail=False, methods=['get'])
    def summary(self, request):
        user = request.user
        org_filter = self._get_org_filter(user)

        companies = Company.objects.filter(**org_filter)
        leads = Lead.objects.filter(**org_filter)

        data = {
            'total_companies': companies.count(),
            'total_analyzed': companies.filter(status='analyzed').count(),
            'total_pending': companies.filter(status='pending').count(),
            'total_errors': companies.filter(status='error').count(),
            'total_leads': leads.count(),
            'potential_clients': leads.filter(is_potential_client=True).count(),
            'avg_score': companies.filter(status='analyzed').aggregate(Avg('score'))['score__avg'] or 0,
            'by_sector': list(
                companies.values('detected_sector')
                .annotate(count=Count('id'))
                .order_by('-count')[:10]
            ),
            'by_status': list(
                leads.values('status')
                .annotate(count=Count('id'))
                .order_by('status')
            ),
            'by_priority': list(
                leads.values('priority')
                .annotate(count=Count('id'))
                .order_by('priority')
            ),
        }
        return Response(data)
