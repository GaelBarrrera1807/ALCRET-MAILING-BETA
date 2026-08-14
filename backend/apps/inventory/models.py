from django.db import models

from apps.core.models import BaseModel


class InventoryItem(BaseModel):
    organization = models.ForeignKey(
        'users.Organization', on_delete=models.CASCADE,
        related_name='inventory_items', null=True, blank=True,
    )
    almacen_id = models.CharField(max_length=255, blank=True, default='')
    producto_id = models.CharField(max_length=255, blank=True, default='')
    sku_o_vin = models.CharField(max_length=255, blank=True, default='', db_index=True)
    nombre_unidad = models.CharField(max_length=500, blank=True, default='')
    cantidad_disponible = models.IntegerField(default=0)
    tipo_movimiento = models.CharField(
        max_length=50, blank=True, default='',
        help_text='Tipo de movimiento del ERP (ej: entrada, salida, ajuste)',
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Unidad en Inventario'
        verbose_name_plural = 'Unidades en Inventario'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['organization', 'sku_o_vin']),
            models.Index(fields=['organization', 'producto_id', 'almacen_id']),
        ]

    def __str__(self):
        return self.nombre_unidad or self.sku_o_vin or self.producto_id
