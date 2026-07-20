from rest_framework import serializers

from apps.core.models import Company, CompanyContact, Sector, Product


class SectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sector
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSerializer(serializers.ModelSerializer):
    sectors = serializers.PrimaryKeyRelatedField(many=True, queryset=Sector.objects.all())

    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'sectors', 'created_at']
        read_only_fields = ['id', 'created_at']


class CompanyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyContact
        fields = ['id', 'company', 'name', 'position', 'email', 'phone', 'is_primary']
        read_only_fields = ['id']


class CompanySerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source='sector.name', read_only=True, default='')
    contacts_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'sector', 'sector_name', 'detected_sector',
            'score', 'status', 'city', 'state', 'is_lead', 'is_client',
            'source', 'created_at', 'website',
            'google_rating', 'google_reviews_count', 'maps_categories',
            'main_photo_url', 'latitude', 'longitude', 'opening_hours',
            'contacts_count',
        ]
        read_only_fields = ['id', 'created_at']

    def get_contacts_count(self, obj) -> int:
        return obj.contacts.count()


class CompanyDetailSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source='sector.name', read_only=True, default='')
    contacts = CompanyContactSerializer(many=True, read_only=True)
    analysis_score = serializers.SerializerMethodField()
    analysis_priority = serializers.SerializerMethodField()
    analysis_reason = serializers.SerializerMethodField()
    analysis_summary = serializers.SerializerMethodField()
    analysis_products = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            'id', 'organization', 'name', 'business_name', 'rfc',
            'description', 'website', 'email', 'phone', 'address',
            'city', 'state', 'country', 'postal_code',
            'latitude', 'longitude',
            'sector', 'sector_name', 'detected_sector',
            'score', 'status', 'is_lead', 'is_client',
            'notes', 'source', 'source_file',
            'contacts', 'created_at', 'updated_at',
            'analysis_score', 'analysis_priority',
            'analysis_reason', 'analysis_summary', 'analysis_products',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _latest_result(self, obj):
        results = getattr(obj, '_latest_result', None)
        if results is not None:
            return results
        from apps.ai_engine.models import AnalysisResult
        result = AnalysisResult.objects.filter(company=obj).select_related('analysis_request').order_by('-created_at').first()
        obj._latest_result = result
        return result

    def get_analysis_score(self, obj):
        r = self._latest_result(obj)
        return r.score if r else None

    def get_analysis_priority(self, obj):
        r = self._latest_result(obj)
        return r.priority if r else None

    def get_analysis_reason(self, obj):
        r = self._latest_result(obj)
        return r.reason if r else ''

    def get_analysis_summary(self, obj):
        r = self._latest_result(obj)
        return r.summary if r else ''

    def get_analysis_products(self, obj):
        r = self._latest_result(obj)
        return r.recommended_products if r else []
