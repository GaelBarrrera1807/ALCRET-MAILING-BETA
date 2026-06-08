from django.contrib.auth import get_user_model
from rest_framework import status, viewsets, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.models import Organization
from apps.users.serializers import (
    OrganizationSerializer, UserSerializer, RegisterSerializer, ChangePasswordSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.organization:
            return User.objects.filter(organization=user.organization)
        return User.objects.filter(id=user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response({'old_password': 'Contraseña incorrecta'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Contraseña actualizada correctamente'})


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.organization:
            return Organization.objects.filter(id=user.organization.id)
        return Organization.objects.none()

    def perform_create(self, serializer):
        org = serializer.save()
        self.request.user.organization = org
        self.request.user.is_organization_admin = True
        self.request.user.save()
