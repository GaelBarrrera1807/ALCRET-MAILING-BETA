from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.inventory.views import InventoryItemViewSet

router = DefaultRouter()
router.register(r'items', InventoryItemViewSet, basename='inventory-items')

urlpatterns = []

urlpatterns += router.urls
