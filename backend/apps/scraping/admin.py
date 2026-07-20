from django.contrib import admin

from apps.scraping.models import ScrapingJob, ScrapedData


@admin.register(ScrapingJob)
class ScrapingJobAdmin(admin.ModelAdmin):
    list_display = ['job_type', 'status', 'url', 'created_at']
    list_filter = ['job_type', 'status']
    search_fields = ['url']


@admin.register(ScrapedData)
class ScrapedDataAdmin(admin.ModelAdmin):
    list_display = ['company', 'source', 'data_type', 'created_at']
    list_filter = ['data_type']
    search_fields = ['company__name', 'source']
