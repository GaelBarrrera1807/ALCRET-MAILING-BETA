from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Fix Django 6.0 + DRF compatibility: prevent duplicate converter registration
from django.urls.converters import register_converter as _orig_rc
def _safe_rc(converter, type_name):
    try:
        _orig_rc(converter, type_name)
    except ValueError:
        pass
import django.urls.converters as _converters_mod
import rest_framework.urlpatterns as _drf_urlpatterns
_converters_mod.register_converter = _safe_rc
_drf_urlpatterns.register_converter = _safe_rc

from apps.mailer import views as apps_mailer_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.core.urls')),
    path('api/auth/', include('apps.users.urls')),
    path('api/', include('apps.companies.urls')),
    path('api/', include('apps.leads.urls')),
    path('api/', include('apps.ai_engine.urls')),
    path('api/', include('apps.scraping.urls')),
    path('api/', include('apps.analytics.urls')),
    path('api/', include('apps.reports.urls')),
    path('api/', include('apps.preprocessing.urls')),
    path('api/mailer/', include('apps.mailer.urls')),
    path('mailer/unsubscribe/<uuid:tracking_id>/', apps_mailer_views.unsubscribe, name='mailer-unsubscribe'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
