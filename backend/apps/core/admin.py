from django.contrib import admin

from apps.core.models import Sector, Product, Company, CompanyContact


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'score', 'sector', 'city', 'created_at']
    list_filter = ['status', 'is_lead', 'is_client', 'sector']
    search_fields = ['name', 'business_name', 'email', 'rfc']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(CompanyContact)
class CompanyContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'email', 'is_primary']
    search_fields = ['name', 'email', 'company__name']
