import uuid

from django.db import models

from apps.core.models import BaseModel


class EmailTemplate(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='email_templates', null=True, blank=True,
    )
    name = models.CharField(max_length=255)
    template_type = models.CharField(
        max_length=50,
        choices=[
            ('cold_outreach', 'Prospección en Frío'),
            ('marketing', 'Marketing'),
            ('follow_up', 'Seguimiento'),
            ('newsletter', 'Boletín'),
            ('welcome', 'Bienvenida'),
            ('custom', 'Personalizada'),
        ],
        default='marketing',
    )
    subject = models.CharField(max_length=998)
    body_html = models.TextField(help_text='HTML con variables {{ first_name }}, {{ company }}, {{ sector }}')
    variables = models.JSONField(
        default=list, blank=True,
        help_text='Lista de variables disponibles (ej: ["first_name", "company", "sector"])',
    )
    description = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    use_count = models.IntegerField(default=0, help_text='Veces que se ha usado esta plantilla')

    class Meta:
        verbose_name = 'Plantilla de Email'
        verbose_name_plural = 'Plantillas de Email'
        ordering = ['name']

    def __str__(self):
        return self.name


class EmailRecipient(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='email_recipients', null=True, blank=True,
    )
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='email_recipients',
    )
    email = models.EmailField()
    first_name = models.CharField(max_length=255, blank=True, default='')
    last_name = models.CharField(max_length=255, blank=True, default='')
    company_name = models.CharField(max_length=500, blank=True, default='')
    sector = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=100, blank=True, default='',
        help_text='Origen del destinatario (ej: csv_upload, lead_generation, manual)',
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Destinatario'
        verbose_name_plural = 'Destinatarios'
        ordering = ['email']
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'organization'],
                name='unique_recipient_per_org',
            ),
        ]
        indexes = [
            models.Index(fields=['organization', 'is_active']),
        ]

    def __str__(self):
        return self.email


class EmailCampaign(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='email_campaigns', null=True, blank=True,
    )
    name = models.CharField(max_length=255)
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='campaigns',
    )
    subject = models.CharField(max_length=998, blank=True, default='')
    body_html = models.TextField(blank=True, default='')
    source_filter = models.CharField(
        max_length=20,
        choices=[
            ('all', 'Todos'),
            ('internal', 'Internos'),
            ('external', 'Externos'),
            ('manual', 'Manual'),
        ],
        default='all',
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Borrador'),
            ('scheduled', 'Programada'),
            ('sending', 'Enviando'),
            ('sent', 'Enviada'),
            ('paused', 'Pausada'),
            ('cancelled', 'Cancelada'),
        ],
        default='draft',
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    bounce_count = models.IntegerField(default=0)
    unsubscribe_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Campaña de Email'
        verbose_name_plural = 'Campañas de Email'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'status']),
        ]

    def __str__(self):
        return self.name


class CampaignSend(BaseModel):
    campaign = models.ForeignKey(
        EmailCampaign, on_delete=models.CASCADE,
        related_name='sends',
    )
    recipient = models.ForeignKey(
        EmailRecipient, on_delete=models.CASCADE,
        related_name='campaign_sends',
    )
    tracking_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    ses_message_id = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pendiente'),
            ('sent', 'Enviado'),
            ('delivered', 'Entregado'),
            ('opened', 'Abierto'),
            ('clicked', 'Click'),
            ('bounced', 'Rebotado'),
            ('complained', 'Reportado'),
            ('unsubscribed', 'Dado de baja'),
        ],
        default='pending',
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Envío de Campaña'
        verbose_name_plural = 'Envíos de Campañas'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['campaign', 'recipient'],
                name='unique_send_per_recipient',
            ),
        ]
        indexes = [
            models.Index(fields=['campaign', 'status']),
            models.Index(fields=['tracking_id']),
            models.Index(fields=['tracking_id', 'status']),
        ]

    def __str__(self):
        return f'{self.recipient.email} - {self.campaign.name}'


class TemplateImage(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='template_images', null=True, blank=True,
    )
    image = models.ImageField(
        upload_to='mailer/images/%Y/%m/',
        help_text='Imagen para usar en plantillas de email',
    )
    alt_text = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Texto alternativo para la imagen',
    )
    file_size = models.IntegerField(
        editable=False, default=0,
        help_text='Tamaño del archivo en bytes',
    )

    class Meta:
        verbose_name = 'Imagen de Plantilla'
        verbose_name_plural = 'Imágenes de Plantillas'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.image and not self.file_size:
            try:
                self.file_size = self.image.size
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        return self.alt_text or self.image.name


class EmailEvent(BaseModel):
    campaign_send = models.ForeignKey(
        CampaignSend, on_delete=models.CASCADE,
        related_name='events',
    )
    event_type = models.CharField(
        max_length=20,
        choices=[
            ('open', 'Apertura'),
            ('click', 'Click'),
            ('bounce', 'Rebote'),
            ('complaint', 'Reporte'),
            ('unsubscribe', 'Baja'),
        ],
    )
    user_agent = models.TextField(blank=True, default='')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    url = models.URLField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Evento de Email'
        verbose_name_plural = 'Eventos de Email'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['campaign_send', 'event_type']),
        ]

    def __str__(self):
        return f'{self.event_type} - {self.campaign_send.recipient.email}'
