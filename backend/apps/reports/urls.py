from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.reports.views import ReportViewSet, ReportTemplateViewSet

router = DefaultRouter()
router.register(r'reports', ReportViewSet, basename='reports')
router.register(r'report-templates', ReportTemplateViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
