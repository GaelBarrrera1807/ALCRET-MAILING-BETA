from django.db import models

from apps.core.models import BaseModel


class ScrapingJob(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='scraping_jobs', null=True, blank=True
    )
    url = models.URLField(blank=True, default='')
    job_type = models.CharField(
        max_length=50,
        choices=[
            ('website', 'Sitio web'),
            ('phone', 'Teléfono'),
            ('social', 'Redes sociales'),
            ('enrichment', 'Enriquecimiento'),
            ('MAPS_DISCOVERY', 'Descubrimiento Google Maps'),
        ],
        default='website',
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
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')
    credits_consumed = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Trabajo de Scraping'
        verbose_name_plural = 'Trabajos de Scraping'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.job_type}: {self.url}'


class ScrapedData(BaseModel):
    company = models.ForeignKey(
        'core.Company', on_delete=models.CASCADE,
        related_name='scraped_data',
        null=True, blank=True,
    )
    source = models.CharField(max_length=255, blank=True, default='')
    data_type = models.CharField(max_length=100, blank=True, default='')
    raw_data = models.JSONField(null=True, blank=True)
    processed_data = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'Datos Scrapeados'
        verbose_name_plural = 'Datos Scrapeados'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.source} - {self.company.name}'
