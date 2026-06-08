from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.preprocessing.views import PreprocessingJobViewSet, PreprocessingRuleViewSet

router = DefaultRouter()
router.register(r'preprocess-jobs', PreprocessingJobViewSet, basename='preprocess-job')
router.register(r'preprocess-rules', PreprocessingRuleViewSet, basename='preprocess-rule')

urlpatterns = [
    path('', include(router.urls)),
    path('preprocess/',
         PreprocessingJobViewSet.as_view({'post': 'preprocess'}),
         name='preprocess-file'),
]
