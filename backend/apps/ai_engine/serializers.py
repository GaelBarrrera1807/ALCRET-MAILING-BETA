from rest_framework import serializers

from apps.ai_engine.models import AnalysisRequest, AnalysisResult, PromptTemplate


class AnalysisRequestSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = AnalysisRequest
        fields = [
            'id', 'company', 'company_name', 'organization',
            'status', 'error_message', 'processing_time',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'organization', 'created_at', 'updated_at']


class AnalysisResultSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'company', 'company_name',
            'score', 'is_potential_client', 'detected_sector',
            'recommended_products', 'reason', 'priority', 'summary',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PromptTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = [
            'id', 'name', 'description', 'model',
            'temperature', 'max_tokens', 'is_active', 'version',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
