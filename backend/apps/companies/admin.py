from django.contrib import admin

from apps.companies.models import Sector, Product, Company, CompanyContact


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']
    filter_horizontal = ['sectors']


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'score', 'status', 'sector', 'city', 'state', 'is_lead', 'created_at']
    list_filter = ['status', 'is_lead', 'is_client', 'sector', 'state']
    search_fields = ['name', 'email', 'phone', 'rfc']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CompanyContact)
class CompanyContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'position', 'email', 'phone', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['name', 'email', 'company__name']
