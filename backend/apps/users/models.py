from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel, TimeStampedModel


class Organization(BaseModel):
    name = models.CharField(max_length=255)
    tax_id = models.CharField('RFC', max_length=50, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Organización'
        verbose_name_plural = 'Organizaciones'

    def __str__(self):
        return self.name


class User(AbstractUser, TimeStampedModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        related_name='users', null=True, blank=True
    )
    phone = models.CharField(max_length=50, blank=True, default='')
    is_organization_admin = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f'{self.get_full_name() or self.username}'
