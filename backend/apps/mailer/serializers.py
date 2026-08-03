from django.conf import settings
from rest_framework import serializers

from apps.mailer.models import (
    EmailTemplate, EmailRecipient, EmailCampaign,
    CampaignSend, EmailEvent, TemplateImage,
)


class EmailEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailEvent
        fields = [
            'id', 'campaign_send', 'event_type',
            'user_agent', 'ip_address', 'url',
            'metadata', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CampaignSendSerializer(serializers.ModelSerializer):
    recipient_email = serializers.SerializerMethodField()
    recipient_name = serializers.SerializerMethodField()
    events = EmailEventSerializer(many=True, read_only=True)

    class Meta:
        model = CampaignSend
        fields = [
            'id', 'campaign', 'recipient', 'recipient_email',
            'recipient_name', 'tracking_id', 'status',
            'sent_at', 'opened_at', 'clicked_at',
            'error_message', 'events', 'created_at',
        ]
        read_only_fields = [
            'id', 'campaign', 'recipient', 'tracking_id',
            'status', 'sent_at', 'opened_at', 'clicked_at',
            'error_message', 'created_at',
        ]

    def get_recipient_email(self, obj):
        return obj.recipient.email if obj.recipient else ''

    def get_recipient_name(self, obj):
        return obj.recipient.first_name if obj.recipient else ''


class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'organization', 'name', 'template_type',
            'subject', 'body_html', 'variables',
            'description', 'is_active', 'use_count',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'use_count', 'created_at', 'updated_at']


class EmailTemplatePreviewSerializer(serializers.Serializer):
    subject = serializers.CharField(read_only=True)
    body_html = serializers.CharField(read_only=True)
    context = serializers.JSONField(default=dict)


class EmailRecipientSerializer(serializers.ModelSerializer):
    lead_status = serializers.CharField(source='lead.status', read_only=True, default='')

    class Meta:
        model = EmailRecipient
        fields = [
            'id', 'organization', 'lead',
            'lead_status',
            'email', 'first_name', 'last_name',
            'company_name', 'sector',
            'is_active', 'unsubscribed_at', 'source',
            'metadata', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'unsubscribed_at', 'created_at', 'updated_at']

    def validate_email(self, value):
        user = self.context['request'].user
        org = user.organization
        if org and EmailRecipient.objects.filter(
            email=value, organization=org
        ).exclude(id=getattr(self.instance, 'id', None)).exists():
            raise serializers.ValidationError('Este email ya existe como destinatario en tu organización')
        return value


class EmailRecipientBulkSerializer(serializers.Serializer):
    recipients = serializers.ListField(
        child=serializers.EmailField(),
        allow_empty=False,
    )
    source = serializers.CharField(default='manual')


class EmailCampaignSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True, default='')
    sends_count = serializers.SerializerMethodField()

    class Meta:
        model = EmailCampaign
        fields = [
            'id', 'organization', 'name', 'template', 'template_name',
            'subject', 'body_html', 'source_filter',
            'status', 'scheduled_at', 'sent_at',
            'total_recipients', 'sent_count',
            'open_count', 'click_count',
            'bounce_count', 'unsubscribe_count',
            'sends_count', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status', 'sent_at',
            'total_recipients', 'sent_count', 'open_count',
            'click_count', 'bounce_count', 'unsubscribe_count',
            'created_at', 'updated_at',
        ]

    def get_sends_count(self, obj):
        return CampaignSend.objects.filter(campaign=obj).count()


class EmailCampaignCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailCampaign
        fields = [
            'name', 'template', 'subject',
            'body_html', 'source_filter',
        ]


class TemplateImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = TemplateImage
        fields = [
            'id', 'url', 'image', 'alt_text',
            'file_size', 'created_at',
        ]
        read_only_fields = ['id', 'file_size', 'created_at']

    def get_url(self, obj):
        if obj.image:
            url = obj.image.url
            base_url = getattr(settings, 'BASE_URL', None)
            if base_url:
                return f"{base_url.rstrip('/')}{url}"
            return url
        return None
