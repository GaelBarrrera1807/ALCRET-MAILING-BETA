import base64

from rest_framework import viewsets, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import Company, Sector, Product
from apps.companies.serializers import (
    CompanySerializer, CompanyDetailSerializer,
    SectorSerializer, ProductSerializer,
)


class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'description']
    ordering_fields = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'description']
    ordering_fields = ['name']


class CompanyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'business_name', 'email', 'detected_sector']
    ordering_fields = ['score', 'name', 'status', 'created_at']

    def get_serializer_class(self):
        if self.action in ('retrieve', 'update', 'partial_update'):
            return CompanyDetailSerializer
        return CompanySerializer

    def get_queryset(self):
        user = self.request.user
        qs = Company.objects.all()
        if user.organization:
            qs = qs.filter(organization=user.organization)
        status_filter = self.request.query_params.get('status')
        sector_filter = self.request.query_params.get('sector')
        search = self.request.query_params.get('search')
        scraping_job = self.request.query_params.get('scraping_job')
        if status_filter:
            qs = qs.filter(status=status_filter)
        if sector_filter:
            qs = qs.filter(sector_id=sector_filter)
        if search:
            qs = qs.filter(name__icontains=search)
        if scraping_job:
            qs = qs.filter(scraping_job_id=scraping_job)
        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        company = self.get_object()
        from apps.ai_engine.tasks import analyze_company
        task = analyze_company.delay(str(company.id))
        return Response({
            'task_id': task.id,
            'status': 'triggered',
            'company_id': str(company.id),
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'],
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        threshold = int(request.data.get('threshold', 30))
        use_ai_fallback = request.data.get('use_ai_fallback', 'false').lower() in ('true', '1')
        content = file.read()
        encoded = base64.b64encode(content).decode('ascii')
        from apps.preprocessing.tasks import process_with_preprocessing
        task = process_with_preprocessing.delay(
            file.name, encoded,
            threshold=threshold,
            use_ai_fallback=use_ai_fallback,
            organization_id=str(request.user.organization_id) if request.user.organization_id else None,
            user_id=str(request.user.id),
        )
        return Response({
            'task_id': task.id,
            'status': 'processing',
            'threshold': threshold,
        }, status=status.HTTP_202_ACCEPTED)
