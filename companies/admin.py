from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import InsuranceCompany, Network, PolicyApplication


@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(ModelAdmin):
    list_display = ("name", "code", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "slug")
    ordering = ("name",)


@admin.register(Network)
class NetworkAdmin(ModelAdmin):
    list_display = ("name", "company", "product_type", "shown_by_default")
    list_filter = ("company", "product_type", "shown_by_default")
    search_fields = ("name",)
    ordering = ("company", "product_type", "name")


@admin.register(PolicyApplication)
class PolicyApplicationAdmin(ModelAdmin):
    list_display = ("name", "code", "company", "product_type", "network", "external_service_id", "is_active")
    list_filter = ("company", "product_type", "network", "is_active")
    search_fields = ("name", "code", "external_service_id")
    ordering = ("company", "product_type", "name")
