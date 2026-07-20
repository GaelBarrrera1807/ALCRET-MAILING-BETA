from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.mailer.views import (
    EmailTemplateViewSet, EmailRecipientViewSet,
    EmailCampaignViewSet, TemplateImageViewSet,
    tracking_pixel, tracking_click,
)

router = DefaultRouter()
router.register(r'templates', EmailTemplateViewSet, basename='email-templates')
router.register(r'recipients', EmailRecipientViewSet, basename='email-recipients')
router.register(r'campaigns', EmailCampaignViewSet, basename='email-campaigns')
router.register(r'images', TemplateImageViewSet, basename='template-images')

urlpatterns = [
    path('track/open/<uuid:tracking_id>/', tracking_pixel, name='tracking-open'),
    path('track/click/<uuid:tracking_id>/', tracking_click, name='tracking-click'),
]

urlpatterns += router.urls
