from django.contrib import admin

from apps.ai_engine.models import AnalysisRequest, AnalysisResult, PromptTemplate


@admin.register(AnalysisRequest)
class AnalysisRequestAdmin(admin.ModelAdmin):
    list_display = ['company', 'status', 'processing_time', 'created_at']
    list_filter = ['status']
    search_fields = ['company__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['company', 'score', 'is_potential_client', 'priority', 'created_at']
    list_filter = ['is_potential_client', 'priority']
    search_fields = ['company__name', 'detected_sector']


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'model', 'is_active', 'version']
    list_filter = ['is_active']
    search_fields = ['name']
