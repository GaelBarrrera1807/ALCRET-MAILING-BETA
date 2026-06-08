from django.db import models

from apps.core.models import BaseModel


class Lead(BaseModel):
    company = models.OneToOneField(
        'companies.Company', on_delete=models.CASCADE,
        related_name='lead'
    )
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='leads', null=True, blank=True
    )
    score = models.IntegerField(default=0)
    is_potential_client = models.BooleanField(default=False)
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
    detected_sector = models.CharField(max_length=255, blank=True, default='')
    recommended_products = models.TextField(blank=True, default='')
    analysis_summary = models.TextField(blank=True, default='')
    reason = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=50,
        choices=[
            ('new', 'Nuevo'),
            ('contacted', 'Contactado'),
            ('qualified', 'Calificado'),
            ('proposal', 'En Propuesta'),
            ('negotiation', 'En Negociación'),
            ('won', 'Ganado'),
            ('lost', 'Perdido'),
        ],
        default='new',
    )
    assigned_to = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_leads'
    )
    contacted_at = models.DateTimeField(null=True, blank=True)
    last_contact = models.DateTimeField(null=True, blank=True)
    next_follow_up = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['-score', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'priority']),
            models.Index(fields=['organization', 'score']),
        ]

    def __str__(self):
        return f'{self.company.name} - {self.score}'


class LeadNote(BaseModel):
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE,
        related_name='notes_list'
    )
    author = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    content = models.TextField()

    class Meta:
        verbose_name = 'Nota de Lead'
        verbose_name_plural = 'Notas de Leads'
        ordering = ['-created_at']

    def __str__(self):
        return f'Nota: {self.lead.company.name} - {self.created_at}'
