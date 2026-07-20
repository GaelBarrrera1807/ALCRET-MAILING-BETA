from django.db import models

from apps.core.models import BaseModel


class PreprocessingJob(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendiente'
        PROCESSING = 'processing', 'Procesando'
        COMPLETED = 'completed', 'Completado'
        ERROR = 'error', 'Error'

    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        null=True, blank=True,
    )
    original_filename = models.CharField(max_length=500)
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.PENDING,
    )
    total_records = models.IntegerField(default=0)
    relevant_records = models.IntegerField(default=0)
    filtered_records = models.IntegerField(default=0)
    scoring_threshold = models.IntegerField(default=30)
    cleaned_file = models.FileField(
        upload_to='preprocessed/', max_length=500,
        null=True, blank=True,
    )
    stats_json = models.JSONField(default=dict, blank=True)
    processing_time = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    auto_enrich_sql = models.BooleanField(default=False)
    credits_consumed = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Trabajo de preprocesamiento'
        verbose_name_plural = 'Trabajos de preprocesamiento'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.original_filename} ({self.get_status_display()})'


class PreprocessingRule(BaseModel):
    class RuleType(models.TextChoices):
        INDUSTRY = 'industry', 'Industria'
        PRODUCT = 'product', 'Producto'
        EXCLUSION = 'exclusion', 'Exclusión'
        CUSTOM = 'custom', 'Personalizada'

    name = models.CharField(max_length=255)
    rule_type = models.CharField(
        max_length=20, choices=RuleType.choices,
        default=RuleType.INDUSTRY,
    )
    keywords = models.JSONField(default=list, blank=True)
    weight = models.IntegerField(default=5)
    sector = models.ForeignKey(
        'core.Sector', on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    recommended_products = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Regla de preprocesamiento'
        verbose_name_plural = 'Reglas de preprocesamiento'
        ordering = ['-weight', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_rule_type_display()}, peso: {self.weight})'
