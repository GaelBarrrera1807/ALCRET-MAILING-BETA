from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.users.models import Organization

User = get_user_model()


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'tax_id', 'phone', 'email', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    organization_detail = OrganizationSerializer(source='organization', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'organization', 'organization_detail',
            'is_organization_admin', 'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    organization_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'organization_name']

    def create(self, validated_data):
        org_name = validated_data.pop('organization_name', None)
        password = validated_data.pop('password')

        if org_name:
            org = Organization.objects.create(name=org_name)
            validated_data['organization'] = org
            validated_data['is_organization_admin'] = True

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
