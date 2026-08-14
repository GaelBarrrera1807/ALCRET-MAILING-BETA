from rest_framework import permissions, viewsets

from apps.inventory.models import InventoryItem
from apps.inventory.serializers import InventoryItemSerializer


class InventoryItemViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InventoryItemSerializer
    search_fields = ['sku_o_vin', 'nombre_unidad', 'producto_id']
    ordering_fields = ['updated_at', 'cantidad_disponible', 'sku_o_vin']

    def get_queryset(self):
        qs = InventoryItem.objects.all()
        user = self.request.user
        if user and user.organization:
            qs = qs.filter(organization=user.organization)
        sku = self.request.query_params.get('sku_o_vin') or self.request.query_params.get('vin')
        almacen = self.request.query_params.get('almacen_id')
        producto = self.request.query_params.get('producto_id')
        if sku:
            qs = qs.filter(sku_o_vin__icontains=sku)
        if almacen:
            qs = qs.filter(almacen_id__icontains=almacen)
        if producto:
            qs = qs.filter(producto_id__icontains=producto)
        return qs
