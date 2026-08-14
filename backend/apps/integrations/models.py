from django.db import models

from apps.core.models import BaseModel


class InboundSyncLog(BaseModel):
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        PROCESADO = 'procesado', 'Procesado'
        ERROR = 'error', 'Error'

    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='inbound_sync_logs', null=True, blank=True,
    )
    evento = models.CharField(max_length=255, blank=True, default='')
    payload = models.JSONField(default=dict, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    error_message = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Bitácora Inbound'
        verbose_name_plural = 'Bitácoras Inbound'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['evento', 'estado']),
        ]

    def __str__(self):
        return f'{self.evento} - {self.get_estado_display()}'
