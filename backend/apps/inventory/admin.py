from django.contrib import admin

from apps.inventory.models import InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('sku_o_vin', 'nombre_unidad', 'producto_id',
                    'almacen_id', 'cantidad_disponible', 'tipo_movimiento', 'updated_at')
    list_filter = ('tipo_movimiento', 'almacen_id')
    search_fields = ('sku_o_vin', 'nombre_unidad', 'producto_id')
    readonly_fields = ('created_at', 'updated_at')
