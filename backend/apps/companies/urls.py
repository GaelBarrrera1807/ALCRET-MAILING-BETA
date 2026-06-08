from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.companies.views import SectorViewSet, ProductViewSet, CompanyViewSet, CompanyContactViewSet

router = DefaultRouter()
router.register(r'sectors', SectorViewSet)
router.register(r'products', ProductViewSet)
router.register(r'companies', CompanyViewSet, basename='companies')
router.register(r'contacts', CompanyContactViewSet, basename='contacts')

urlpatterns = [
    path('', include(router.urls)),
]
