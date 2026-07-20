import base64

from rest_framework import viewsets, permissions, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.preprocessing.models import PreprocessingJob, PreprocessingRule
from apps.preprocessing.serializers import (
    PreprocessingJobListSerializer,
    PreprocessingJobDetailSerializer,
    PreprocessingFileSerializer,
    PreprocessingRuleSerializer,
)
from apps.preprocessing.tasks import run_preprocessing


class PreprocessingJobViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return PreprocessingJobListSerializer
        return PreprocessingJobDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = PreprocessingJob.objects.all()
        if user.organization:
            qs = qs.filter(organization=user.organization)
        return qs

    @action(detail=False, methods=['post'],
            parser_classes=[parsers.MultiPartParser, parsers.FormParser])
    def preprocess(self, request):
        serializer = PreprocessingFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['file']
        threshold = serializer.validated_data.get('threshold', 30)
        use_ai_fallback = serializer.validated_data.get('use_ai_fallback', False)
        auto_enrich_sql = serializer.validated_data.get('auto_enrich_sql', False)
        content = file.read()
        encoded = base64.b64encode(content).decode('ascii')
        job = PreprocessingJob.objects.create(
            organization=request.user.organization if request.user.organization else None,
            original_filename=file.name,
            status=PreprocessingJob.Status.PROCESSING,
            scoring_threshold=threshold,
            auto_enrich_sql=auto_enrich_sql,
        )
        task = run_preprocessing.delay(
            file.name, encoded,
            threshold=threshold,
            use_ai_fallback=use_ai_fallback,
            auto_enrich_sql=auto_enrich_sql,
            job_id=str(job.id),
        )
        return Response({
            'task_id': task.id,
            'job_id': str(job.id),
            'status': 'processing',
            'filename': file.name,
            'threshold': threshold,
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        job = self.get_object()
        if not job.cleaned_file:
            return Response(
                {'error': 'No hay archivo limpio disponible'},
                status=status.HTTP_404_NOT_FOUND,
            )
        from django.http import FileResponse
        return FileResponse(
            job.cleaned_file.open('rb'),
            as_attachment=True,
            filename=f'preprocessed_{job.original_filename}',
        )


class PreprocessingRuleViewSet(viewsets.ModelViewSet):
    queryset = PreprocessingRule.objects.all()
    serializer_class = PreprocessingRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'weight', 'rule_type']
