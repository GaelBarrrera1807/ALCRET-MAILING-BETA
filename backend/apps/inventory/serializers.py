from rest_framework import serializers

from apps.inventory.models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'organization', 'almacen_id', 'producto_id',
            'sku_o_vin', 'nombre_unidad', 'cantidad_disponible',
            'tipo_movimiento', 'updated_at',
        ]
        read_only_fields = fields
