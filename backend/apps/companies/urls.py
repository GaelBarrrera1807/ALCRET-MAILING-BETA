from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.companies.views import CompanyViewSet, SectorViewSet, ProductViewSet

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='companies')
router.register(r'sectors', SectorViewSet, basename='sectors')
router.register(r'products', ProductViewSet, basename='products')

urlpatterns = [
    path('', include(router.urls)),
]
