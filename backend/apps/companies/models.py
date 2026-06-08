from django.db import models

from apps.core.models import BaseModel


class Sector(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Sector'
        verbose_name_plural = 'Sectores'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default='')
    sectors = models.ManyToManyField(Sector, related_name='products', blank=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['name']

    def __str__(self):
        return self.name


class Company(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='companies', null=True, blank=True
    )
    name = models.CharField(max_length=500)
    business_name = models.CharField('Razón social', max_length=500, blank=True, default='')
    rfc = models.CharField('RFC', max_length=50, blank=True, default='')
    description = models.TextField(blank=True, default='')
    website = models.URLField(blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=100, blank=True, default='')
    address = models.TextField(blank=True, default='')
    city = models.CharField(max_length=255, blank=True, default='')
    state = models.CharField(max_length=255, blank=True, default='')
    country = models.CharField(max_length=255, default='México')
    postal_code = models.CharField(max_length=20, blank=True, default='')
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    sector = models.ForeignKey(
        Sector, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='companies'
    )
    detected_sector = models.CharField(max_length=255, blank=True, default='')
    score = models.IntegerField(default=0)
    is_client = models.BooleanField(default=False)
    is_lead = models.BooleanField(default=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('pending', 'Pendiente'),
            ('analyzing', 'Analizando'),
            ('analyzed', 'Analizado'),
            ('error', 'Error'),
        ],
        default='pending',
    )
    notes = models.TextField(blank=True, default='')
    source = models.CharField(max_length=255, blank=True, default='')
    source_file = models.CharField(max_length=500, blank=True, default='')

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'
        ordering = ['-score', 'name']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['organization', 'score']),
        ]

    def __str__(self):
        return self.name


class CompanyContact(BaseModel):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        related_name='contacts'
    )
    name = models.CharField(max_length=255)
    position = models.CharField(max_length=255, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Contacto'
        verbose_name_plural = 'Contactos'

    def __str__(self):
        return f'{self.name} - {self.company.name}'
