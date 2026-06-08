from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.scraping.models import ScrapingJob, ScrapedData
from apps.scraping.serializers import (
    ScrapingJobSerializer, ScrapedDataSerializer, ScrapingRequestSerializer,
)
from apps.scraping.tasks import run_scraping_job


class ScrapingJobViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return ScrapingRequestSerializer
        return ScrapingJobSerializer

    def get_queryset(self):
        user = self.request.user
        qs = ScrapingJob.objects.select_related('company')
        if user.organization:
            qs = qs.filter(organization=user.organization)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ScrapingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        job = ScrapingJob.objects.create(
            organization=request.user.organization,
            company_id=data.get('company_id'),
            url=data.get('url', ''),
            job_type=data.get('job_type'),
        )

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
