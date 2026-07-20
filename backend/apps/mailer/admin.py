from django.contrib import admin

from apps.mailer.models import (
    EmailTemplate, EmailRecipient, EmailCampaign,
    CampaignSend, EmailEvent,
)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'use_count', 'created_at']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'subject']
    readonly_fields = ['use_count', 'created_at', 'updated_at']


@admin.register(EmailRecipient)
class EmailRecipientAdmin(admin.ModelAdmin):
    list_display = ['email', 'organization', 'first_name', 'company_name', 'is_active', 'source', 'created_at']
    list_filter = ['is_active', 'source']
    search_fields = ['email', 'first_name', 'last_name', 'company_name']
    readonly_fields = ['unsubscribed_at', 'created_at', 'updated_at']


class CampaignSendInline(admin.TabularInline):
    model = CampaignSend
    extra = 0
    readonly_fields = ['tracking_id', 'status', 'sent_at', 'opened_at', 'clicked_at', 'error_message']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'template', 'source_filter', 'total_recipients', 'sent_count', 'created_at']
    list_filter = ['status', 'source_filter']
    search_fields = ['name']
    readonly_fields = [
        'status', 'sent_at',
        'total_recipients', 'sent_count',
        'open_count', 'click_count',
        'bounce_count', 'unsubscribe_count',
        'created_at', 'updated_at',
    ]
    inlines = [CampaignSendInline]


@admin.register(CampaignSend)
class CampaignSendAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'recipient', 'tracking_id', 'status', 'sent_at', 'opened_at', 'created_at']
    list_filter = ['status']
    search_fields = ['recipient__email', 'tracking_id']
    readonly_fields = ['tracking_id', 'sent_at', 'opened_at', 'clicked_at', 'created_at']

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EmailEvent)
class EmailEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'campaign_send', 'ip_address', 'created_at']
    list_filter = ['event_type']
    readonly_fields = ['created_at']

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False
