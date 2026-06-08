from rest_framework import serializers

from apps.reports.models import Report, ReportTemplate


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            'id', 'organization', 'title', 'report_type',
            'status', 'file', 'file_type', 'filters',
            'summary', 'error_message', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'status', 'file', 'error_message', 'created_at', 'updated_at']


class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = [
            'id', 'name', 'description', 'report_type',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ReportGenerateSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=['leads', 'scoring', 'commercial', 'processing', 'custom'])
    title = serializers.CharField(max_length=500)
    filters = serializers.JSONField(required=False, default=dict)
    file_type = serializers.ChoiceField(choices=['pdf', 'csv'], default='pdf')
