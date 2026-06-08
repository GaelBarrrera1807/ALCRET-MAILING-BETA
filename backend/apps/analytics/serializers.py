from rest_framework import serializers

from apps.analytics.models import DashboardMetric, ProcessingStats


class DashboardMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardMetric
        fields = ['id', 'organization', 'metric_type', 'value', 'date', 'created_at']
        read_only_fields = ['id', 'organization', 'created_at']


class ProcessingStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingStats
        fields = [
            'id', 'organization', 'total_companies', 'total_analyzed',
            'total_pending', 'total_errors', 'total_leads',
            'total_potential_clients', 'avg_score', 'date', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']
