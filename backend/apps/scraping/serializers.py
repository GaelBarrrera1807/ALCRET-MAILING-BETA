from rest_framework import serializers

from apps.scraping.models import ScrapingJob, ScrapedData


class ScrapingJobSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True, default='')

    class Meta:
        model = ScrapingJob
        fields = [
            'id', 'organization', 'company', 'company_name',
            'url', 'job_type', 'status', 'result',
            'error_message', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'status', 'result', 'error_message', 'created_at', 'updated_at']


class ScrapedDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScrapedData
        fields = [
            'id', 'company', 'source', 'data_type',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScrapingRequestSerializer(serializers.Serializer):
    company_id = serializers.UUIDField()
    url = serializers.URLField(required=False, allow_blank=True)
    job_type = serializers.ChoiceField(choices=['website', 'phone', 'social', 'enrichment'])
