from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.ai_engine.views import AnalysisRequestViewSet, AnalysisResultViewSet, PromptTemplateViewSet

router = DefaultRouter()
router.register(r'analysis-requests', AnalysisRequestViewSet, basename='analysis-requests')
router.register(r'analysis-results', AnalysisResultViewSet, basename='analysis-results')
router.register(r'prompt-templates', PromptTemplateViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
