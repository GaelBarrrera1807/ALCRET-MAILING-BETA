from rest_framework import serializers

from apps.scraping.models import ScrapingJob, ScrapedData


class ScrapingJobSerializer(serializers.ModelSerializer):
    companies_count = serializers.SerializerMethodField()
    search_query = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()

    class Meta:
        model = ScrapingJob
        fields = [
            'id', 'organization',
            'url', 'job_type', 'status', 'result',
            'error_message', 'created_at', 'updated_at',
            'companies_count', 'search_query', 'location',
        ]
        read_only_fields = ['id', 'organization', 'status', 'result', 'error_message', 'created_at', 'updated_at',
                            'companies_count', 'search_query', 'location']

    def get_companies_count(self, obj) -> int:
        return getattr(obj, '_companies_count', None) or obj.companies.count()

    def get_search_query(self, obj) -> str:
        if obj.result and isinstance(obj.result, dict):
            return obj.result.get('search_query', '')
        return ''

    def get_location(self, obj) -> str:
        if obj.result and isinstance(obj.result, dict):
            return obj.result.get('location', '')
        return ''


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
    job_type = serializers.ChoiceField(choices=['website', 'phone', 'social', 'enrichment', 'MAPS_DISCOVERY'])


class LeadFinderSerializer(serializers.Serializer):
    search_query = serializers.CharField(required=True, max_length=500)
    location = serializers.CharField(required=True, max_length=500)
    limit = serializers.IntegerField(required=False, default=50, min_value=1, max_value=500)
