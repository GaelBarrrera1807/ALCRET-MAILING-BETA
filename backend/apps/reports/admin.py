from django.contrib import admin

from apps.reports.models import Report, ReportTemplate


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'status', 'organization', 'created_at']
    list_filter = ['report_type', 'status']
    search_fields = ['title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'is_active']
    list_filter = ['report_type', 'is_active']
    search_fields = ['name']
