from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.scraping.models import ScrapingJob, ScrapedData
from apps.scraping.serializers import (
    ScrapingJobSerializer, ScrapedDataSerializer,
    ScrapingRequestSerializer, LeadFinderSerializer,
)
from apps.scraping.tasks import run_scraping_job, discover_companies_from_maps


from django.db.models import Count


class ScrapingJobViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ScrapingRequestSerializer
        return ScrapingJobSerializer

    def get_queryset(self):
        user = self.request.user
        qs = ScrapingJob.objects.all()
        if user.organization:
            qs = qs.filter(organization=user.organization)
        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)
        if self.action == 'list':
            qs = qs.annotate(_companies_count=Count('companies'))
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ScrapingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        from apps.core.models import Company
        job = ScrapingJob.objects.create(
            organization=request.user.organization,
            url=data.get('url', ''),
            job_type=data.get('job_type'),
        )
        company_id = data.get('company_id')
        if company_id:
            Company.objects.filter(id=company_id).update(scraping_job=job)

        run_scraping_job.delay(job.id)

        return Response(
            ScrapingJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        job = self.get_object()
        job.status = 'pending'
        job.error_message = ''
        job.save(update_fields=['status', 'error_message'])
        run_scraping_job.delay(job.id)
        return Response({'status': 'retrying'})

    @action(detail=False, methods=['post'])
    def lead_finder(self, request):
        serializer = LeadFinderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        job = ScrapingJob.objects.create(
            organization=request.user.organization,
            job_type='MAPS_DISCOVERY',
            url=f'maps:{data["search_query"]}|{data["location"]}|{data["limit"]}',
            status='pending',
        )

        discover_companies_from_maps.delay(
            data['search_query'], data['location'], data['limit'],
            organization_id=request.user.organization.id if request.user.organization else None,
            job_id=str(job.id),
        )

        return Response(
            ScrapingJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )


class ScrapedDataViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScrapedDataSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.organization:
            return ScrapedData.objects.none()
        qs = ScrapedData.objects.select_related('company').filter(
            company__organization=user.organization
        )
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        return qs
