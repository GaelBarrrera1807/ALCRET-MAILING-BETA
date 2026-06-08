from django.contrib import admin

from apps.preprocessing.models import PreprocessingJob, PreprocessingRule


@admin.register(PreprocessingJob)
class PreprocessingJobAdmin(admin.ModelAdmin):
    list_display = [
        'original_filename', 'status', 'total_records',
        'relevant_records', 'filtered_records', 'created_at',
    ]
    list_filter = ['status', 'scoring_threshold']
    search_fields = ['original_filename']
    readonly_fields = [
        'total_records', 'relevant_records', 'filtered_records',
        'stats_json', 'processing_time',
    ]


@admin.register(PreprocessingRule)
class PreprocessingRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'weight', 'is_active']
    list_filter = ['rule_type', 'is_active']
    search_fields = ['name', 'keywords']
