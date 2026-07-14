from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import InsuranceCompany, Network


@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(ModelAdmin):
    list_display = ("name", "code", "slug", "external_id", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "slug")
    ordering = ("name",)


@admin.register(Network)
class NetworkAdmin(ModelAdmin):
    list_display = ("name", "company", "product_type", "external_id", "shown_by_default")
    list_filter = ("company", "product_type", "shown_by_default")
    search_fields = ("name",)
    ordering = ("company", "product_type", "name")
