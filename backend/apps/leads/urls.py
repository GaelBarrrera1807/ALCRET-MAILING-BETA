from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.leads.views import LeadViewSet, LeadNoteViewSet

router = DefaultRouter()
router.register(r'leads', LeadViewSet, basename='leads')
router.register(r'lead-notes', LeadNoteViewSet, basename='lead-notes')

urlpatterns = [
    path('', include(router.urls)),
]
