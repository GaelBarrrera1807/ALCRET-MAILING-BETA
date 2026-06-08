from django.contrib import admin

from apps.analytics.models import DashboardMetric, ProcessingStats


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_type', 'organization', 'date', 'created_at']
    list_filter = ['metric_type', 'date']
    search_fields = ['organization__name']


@admin.register(ProcessingStats)
class ProcessingStatsAdmin(admin.ModelAdmin):
    list_display = ['date', 'organization', 'total_companies', 'total_analyzed', 'total_leads', 'avg_score']
    list_filter = ['date']
