from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model

from apps.users.models import Organization

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'organization', 'is_organization_admin', 'is_active']
    list_filter = ['organization', 'is_organization_admin', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información adicional', {'fields': ('organization', 'phone', 'is_organization_admin')}),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'tax_id', 'email', 'is_active', 'created_at']
    search_fields = ['name', 'tax_id', 'email']
