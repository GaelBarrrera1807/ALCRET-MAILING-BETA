from rest_framework import serializers

from apps.leads.models import Lead, LeadNote


class LeadNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True, default='')

    class Meta:
        model = LeadNote
        fields = ['id', 'lead', 'author', 'author_name', 'content', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


class LeadSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_status = serializers.CharField(source='company.status', read_only=True)
    contact_name = serializers.CharField(source='contact.name', read_only=True, default='')
    contact_email = serializers.CharField(source='contact.email', read_only=True, default='')
    assigned_to_name = serializers.SerializerMethodField()
    esquema_display = serializers.CharField(source='get_esquema_display', read_only=True, default='')
    stage_display = serializers.CharField(source='get_stage_display', read_only=True, default='')
    notes = LeadNoteSerializer(source='notes_list', many=True, read_only=True)

    def get_assigned_to_name(self, obj):
        if not obj.assigned_to:
            return ''
        return obj.assigned_to.get_full_name() or obj.assigned_to.username

    class Meta:
        model = Lead
        fields = [
            'id', 'company', 'company_name', 'company_status',
            'contact', 'contact_name', 'contact_email',
            'organization', 'score', 'is_potential_client',
            'priority', 'detected_sector', 'recommended_products',
            'analysis_summary', 'reason', 'status', 'stage', 'stage_display',
            'esquema', 'esquema_display', 'monto_total', 'unidad_interes',
            'last_email_interaction',
            'assigned_to', 'assigned_to_name', 'auto_created',
            'contacted_at', 'last_contact',
            'next_follow_up', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'auto_created', 'created_at', 'updated_at']


class LeadBatchUpdateSerializer(serializers.Serializer):
    lead_ids = serializers.ListField(child=serializers.UUIDField())
    status = serializers.ChoiceField(
        choices=['new', 'contacted', 'qualified', 'proposal', 'negotiation', 'won', 'lost'],
        required=False
    )
    priority = serializers.ChoiceField(
        choices=['baja', 'media', 'alta', 'urgente'],
        required=False
    )
    assigned_to = serializers.UUIDField(required=False, allow_null=True)
