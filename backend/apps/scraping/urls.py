from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.scraping.views import ScrapingJobViewSet, ScrapedDataViewSet

router = DefaultRouter()
router.register(r'scraping-jobs', ScrapingJobViewSet, basename='scraping-jobs')
router.register(r'scraped-data', ScrapedDataViewSet, basename='scraped-data')

urlpatterns = [
    path('', include(router.urls)),
]
