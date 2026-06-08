from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.views import RegisterView, UserViewSet, OrganizationViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'organizations', OrganizationViewSet, basename='organizations')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token-obtain'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('', include(router.urls)),
]
