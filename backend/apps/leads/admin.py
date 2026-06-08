from django.contrib import admin

from apps.leads.models import Lead, LeadNote


class LeadNoteInline(admin.TabularInline):
    model = LeadNote
    extra = 0
    readonly_fields = ['author', 'created_at']


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['company', 'score', 'priority', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'is_potential_client']
    search_fields = ['company__name', 'detected_sector']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [LeadNoteInline]


@admin.register(LeadNote)
class LeadNoteAdmin(admin.ModelAdmin):
    list_display = ['lead', 'author', 'created_at']
    readonly_fields = ['author', 'created_at']
