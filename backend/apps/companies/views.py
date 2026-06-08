import logging

from rest_framework import viewsets, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.companies.models import Sector, Product, Company, CompanyContact
from apps.companies.serializers import (
    SectorSerializer, ProductSerializer, CompanyListSerializer,
    CompanyDetailSerializer, CompanyContactSerializer, CompanyUploadSerializer,
)
from apps.companies.tasks import process_company_upload

logger = logging.getLogger(__name__)


class SectorViewSet(viewsets.ModelViewSet):
    queryset = Sector.objects.all()
    serializer_class = SectorSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name']
    ordering_fields = ['name']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name']
    ordering_fields = ['name']


class CompanyViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'email', 'phone', 'city', 'state']
    ordering_fields = ['score', 'name', 'created_at', 'city']

    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyListSerializer
        return CompanyDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return Company.objects.none()
        qs = Company.objects.filter(organization=user.organization)
        status = self.request.query_params.get('status')
        sector = self.request.query_params.get('sector')
        is_lead = self.request.query_params.get('is_lead')
        min_score = self.request.query_params.get('min_score')
        if status:
            qs = qs.filter(status=status)
        if sector:
            qs = qs.filter(sector_id=sector)
        if is_lead is not None:
            qs = qs.filter(is_lead=is_lead.lower() == 'true')
        if min_score:
            qs = qs.filter(score__gte=int(min_score))
        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=False, methods=['post'], parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def upload(self, request):
        import base64
        serializer = CompanyUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']
        sector = serializer.validated_data.get('sector')
        threshold = serializer.validated_data.get('threshold', 30)
        use_ai_fallback = serializer.validated_data.get('use_ai_fallback', False)
        
        content = file.read()
        encoded = base64.b64encode(content).decode('ascii')
        task = process_company_upload.delay(
            file.name, encoded,
            sector_id=sector.id if sector else None,
            organization_id=request.user.organization.id if request.user.organization else None,
            user_id=request.user.id,
            threshold=threshold,
            use_ai_fallback=use_ai_fallback,
        )
        return Response({
            'task_id': task.id,
            'status': 'processing',
            'threshold': threshold,
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'])
    def analyze(self, request, pk=None):
        company = self.get_object()
        company.status = 'analyzing'
        company.save()
        from apps.ai_engine.tasks import analyze_company
        analyze_company.delay(company.id)
        return Response({'status': 'analyzing'})

    @action(detail=False, methods=['post'])
    def analyze_batch(self, request):
        company_ids = request.data.get('company_ids', [])
        if not company_ids:
            return Response({'error': 'Se requieren company_ids'}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        if not user.organization:
            return Response({'error': 'Usuario sin organización'}, status=status.HTTP_403_FORBIDDEN)
        valid_ids = Company.objects.filter(
            id__in=company_ids, organization=user.organization
        ).values_list('id', flat=True)
        if not valid_ids:
            return Response({'error': 'No se encontraron empresas válidas'}, status=status.HTTP_404_NOT_FOUND)
        from apps.ai_engine.tasks import analyze_company
        for cid in valid_ids:
            analyze_company.delay(cid)
        return Response({'status': f'{len(valid_ids)} companies queued for analysis'})


class CompanyContactViewSet(viewsets.ModelViewSet):
    serializer_class = CompanyContactSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return CompanyContact.objects.none()
        qs = CompanyContact.objects.filter(company__organization=user.organization)
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs
