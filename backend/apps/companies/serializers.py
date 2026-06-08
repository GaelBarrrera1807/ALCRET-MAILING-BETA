import os

from rest_framework import serializers

from apps.companies.models import Sector, Product, Company, CompanyContact
from apps.leads.serializers import LeadSerializer

ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    sectors_detail = SectorSerializer(source='sectors', many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'sectors', 'sectors_detail', 'created_at']
        read_only_fields = ['id', 'created_at']


class CompanyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyContact
        fields = ['id', 'company', 'name', 'position', 'email', 'phone', 'is_primary']
        read_only_fields = ['id']


class CompanyListSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source='sector.name', read_only=True, default='')

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'sector', 'sector_name', 'detected_sector',
            'score', 'status', 'city', 'state', 'is_lead', 'is_client',
            'source', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CompanyDetailSerializer(serializers.ModelSerializer):
    contacts = CompanyContactSerializer(many=True, read_only=True)
    sector_name = serializers.CharField(source='sector.name', read_only=True, default='')
    analysis_score = serializers.IntegerField(read_only=True, default=0)
    analysis_priority = serializers.CharField(read_only=True, default='')
    analysis_reason = serializers.CharField(read_only=True, default='')
    analysis_summary = serializers.CharField(read_only=True, default='')
    analysis_products = serializers.ListField(child=serializers.CharField(), read_only=True, default=[])

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'business_name', 'rfc',
            'description', 'website', 'email', 'phone', 'address',
            'city', 'state', 'country', 'postal_code',
            'latitude', 'longitude',
            'sector', 'sector_name', 'detected_sector',
            'score', 'is_client', 'is_lead', 'status',
            'analysis_score', 'analysis_priority', 'analysis_reason',
            'analysis_summary', 'analysis_products',
            'notes', 'source', 'source_file',
            'contacts', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        result = instance.analysis_results.order_by('-created_at').first()
        if result:
            data['analysis_score'] = result.score
            data['analysis_priority'] = result.priority
            data['analysis_reason'] = result.reason
            data['analysis_summary'] = result.summary
            data['analysis_products'] = result.recommended_products
        return data


class CompanyUploadSerializer(serializers.Serializer):
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

    sector = serializers.PrimaryKeyRelatedField(
        queryset=Sector.objects.all(), required=False, allow_null=True
    )
    threshold = serializers.IntegerField(
        default=0, min_value=0, max_value=100, required=False,
    )
    use_ai_fallback = serializers.BooleanField(
        default=False, required=False,
    )
