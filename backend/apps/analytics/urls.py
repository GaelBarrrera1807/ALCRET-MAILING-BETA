from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.analytics.views import DashboardMetricViewSet, ProcessingStatsViewSet, AnalyticsViewSet

router = DefaultRouter()
router.register(r'dashboard-metrics', DashboardMetricViewSet, basename='dashboard-metrics')
router.register(r'processing-stats', ProcessingStatsViewSet, basename='processing-stats')

urlpatterns = [
    path('', include(router.urls)),
    path('summary/', AnalyticsViewSet.as_view({'get': 'summary'}), name='analytics-summary'),
]
