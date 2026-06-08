import os

from rest_framework import serializers

from apps.preprocessing.models import PreprocessingJob, PreprocessingRule

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class PreprocessingJobListSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreprocessingJob
        fields = [
            'id', 'original_filename', 'status',
            'total_records', 'relevant_records', 'filtered_records',
            'scoring_threshold', 'processing_time',
            'error_message', 'created_at',
        ]
        read_only_fields = fields


class PreprocessingJobDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreprocessingJob
        fields = [
            'id', 'organization', 'original_filename', 'status',
            'total_records', 'relevant_records', 'filtered_records',
            'scoring_threshold', 'cleaned_file', 'stats_json',
            'processing_time', 'error_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'organization', 'status',
            'total_records', 'relevant_records', 'filtered_records',
            'cleaned_file', 'stats_json', 'processing_time',
            'error_message', 'created_at', 'updated_at',
        ]


class PreprocessingFileSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, file):
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f'Tipo no permitido: {ext}. Solo: {", ".join(ALLOWED_EXTENSIONS)}'
            )
        if file.size > MAX_FILE_SIZE:
            raise serializers.ValidationError(
                f'Archivo demasiado grande ({file.size / 1024 / 1024:.1f}MB). Máx: {MAX_FILE_SIZE / 1024 / 1024}MB'
            )
        return file

    threshold = serializers.IntegerField(
        default=30, min_value=0, max_value=100, required=False,
    )
    use_ai_fallback = serializers.BooleanField(
        default=False, required=False,
    )


class PreprocessingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreprocessingRule
        fields = [
            'id', 'name', 'rule_type', 'keywords', 'weight',
            'sector', 'recommended_products', 'is_active', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
