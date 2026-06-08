from django.db import models

from apps.core.models import BaseModel


class DashboardMetric(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='metrics', null=True, blank=True
    )
    metric_type = models.CharField(
        max_length=100,
        choices=[
            ('total_companies', 'Total de empresas'),
            ('total_leads', 'Total de leads'),
            ('avg_score', 'Score promedio'),
            ('companies_by_sector', 'Empresas por sector'),
            ('leads_by_status', 'Leads por estado'),
            ('leads_by_priority', 'Leads por prioridad'),
            ('analysis_count', 'Análisis realizados'),
            ('conversion_rate', 'Tasa de conversión'),
        ],
    )
    value = models.JSONField()
    date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Métrica del Dashboard'
        verbose_name_plural = 'Métricas del Dashboard'
        ordering = ['-date']
        unique_together = ['organization', 'metric_type', 'date']

    def __str__(self):
        return f'{self.metric_type}: {self.date}'


class ProcessingStats(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='processing_stats', null=True, blank=True
    )
    total_companies = models.IntegerField(default=0)
    total_analyzed = models.IntegerField(default=0)
    total_pending = models.IntegerField(default=0)
    total_errors = models.IntegerField(default=0)
    total_leads = models.IntegerField(default=0)
    total_potential_clients = models.IntegerField(default=0)
    avg_score = models.FloatField(default=0)
    date = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = 'Estadística de Procesamiento'
        verbose_name_plural = 'Estadísticas de Procesamiento'
        ordering = ['-date']

    def __str__(self):
        return f'Stats: {self.date}'
