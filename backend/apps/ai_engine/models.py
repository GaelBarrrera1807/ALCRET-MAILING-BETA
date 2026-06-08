from django.db import models

from apps.core.models import BaseModel


class AnalysisRequest(BaseModel):
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='analysis_requests'
    )
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='analysis_requests', null=True, blank=True
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pendiente'),
            ('processing', 'Procesando'),
            ('completed', 'Completado'),
            ('error', 'Error'),
        ],
        default='pending',
    )
    prompt_used = models.TextField(blank=True, default='')
    raw_response = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    processing_time = models.FloatField(null=True, blank=True, help_text='Tiempo de procesamiento en segundos')

    class Meta:
        verbose_name = 'Solicitud de Análisis'
        verbose_name_plural = 'Solicitudes de Análisis'
        ordering = ['-created_at']

    def __str__(self):
        return f'Análisis: {self.company.name} - {self.status}'


class AnalysisResult(BaseModel):
    analysis_request = models.OneToOneField(
        AnalysisRequest, on_delete=models.CASCADE,
        related_name='result'
    )
    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='analysis_results'
    )
    score = models.IntegerField(default=0)
    is_potential_client = models.BooleanField(default=False)
    detected_sector = models.CharField(max_length=255, blank=True, default='')
    recommended_products = models.JSONField(default=list, blank=True)
    reason = models.TextField(blank=True, default='')
    priority = models.CharField(
        max_length=20,
        choices=[
            ('baja', 'Baja'),
            ('media', 'Media'),
            ('alta', 'Alta'),
            ('urgente', 'Urgente'),
        ],
        default='media',
    )
    summary = models.TextField(blank=True, default='')
    raw_json = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'Resultado de Análisis'
        verbose_name_plural = 'Resultados de Análisis'
        ordering = ['-score']

    def __str__(self):
        return f'Resultado: {self.company.name} - Score: {self.score}'


class PromptTemplate(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    system_prompt = models.TextField()
    user_prompt_template = models.TextField()
    model = models.CharField(max_length=255, default='cerebras/Llama-3.3-70B')
    temperature = models.FloatField(default=0.1)
    max_tokens = models.IntegerField(default=1000)
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)

    class Meta:
        verbose_name = 'Plantilla de Prompt'
        verbose_name_plural = 'Plantillas de Prompt'

    def __str__(self):
        return f'{self.name} v{self.version}'
