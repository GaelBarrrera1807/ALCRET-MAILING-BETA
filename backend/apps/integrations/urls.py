from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.integrations.views import alcret_webhook, InboundSyncLogViewSet

router = DefaultRouter()
router.register(r'logs', InboundSyncLogViewSet, basename='inbound-logs')

urlpatterns = [
    path('alcret/webhook/', alcret_webhook, name='alcret-webhook'),
]

urlpatterns += router.urls
