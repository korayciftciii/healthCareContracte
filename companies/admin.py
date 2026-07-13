from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import InsuranceCompany


@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(ModelAdmin):
    list_display = ("name", "code", "slug", "external_id", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "slug")
    ordering = ("name",)
