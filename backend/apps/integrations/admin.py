from django.contrib import admin

from apps.integrations.models import InboundSyncLog


@admin.register(InboundSyncLog)
class InboundSyncLogAdmin(admin.ModelAdmin):
    list_display = ('evento', 'estado', 'created_at')
    list_filter = ('estado', 'evento')
    search_fields = ('evento', 'error_message')
    readonly_fields = (
        'id', 'organization', 'evento', 'payload',
        'estado', 'error_message', 'created_at', 'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False