from django.db import models

from apps.core.models import BaseModel


class Report(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='reports', null=True, blank=True
    )
    title = models.CharField(max_length=500)
    report_type = models.CharField(
        max_length=50,
        choices=[
            ('leads', 'Reporte de Leads'),
            ('scoring', 'Reporte de Scoring'),
            ('commercial', 'Métricas Comerciales'),
            ('processing', 'Procesamiento'),
            ('custom', 'Personalizado'),
        ],
        default='leads',
    )
    status = models.CharField(
        max_length=50,
        choices=[
            ('generating', 'Generando'),
            ('completed', 'Completado'),
            ('error', 'Error'),
        ],
        default='generating',
    )
    file = models.FileField(upload_to='reports/', null=True, blank=True)
    file_type = models.CharField(max_length=20, default='pdf')
    filters = models.JSONField(null=True, blank=True, help_text='Filtros usados para generar el reporte')
    summary = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Reporte'
        verbose_name_plural = 'Reportes'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.report_type})'


class ReportTemplate(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    report_type = models.CharField(max_length=50, choices=Report.report_type.field.choices)
    config = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Plantilla de Reporte'
        verbose_name_plural = 'Plantillas de Reporte'

    def __str__(self):
        return self.name
