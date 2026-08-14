from rest_framework import serializers

from apps.integrations.models import InboundSyncLog


class InboundSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboundSyncLog
        fields = [
            'id', 'organization', 'evento', 'payload',
            'estado', 'error_message', 'created_at', 'updated_at',
        ]
        read_only_fields = fields
