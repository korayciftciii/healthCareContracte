from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import HealthInstitution


@admin.register(HealthInstitution)
class HealthInstitutionAdmin(ModelAdmin):
    list_display = (
        "name",
        "company",
        "product_type",
        "institution_type",
        "city",
        "district",
        "is_active",
        "last_seen_at",
    )
    list_filter = ("company", "product_type", "institution_type", "city", "is_active")
    search_fields = ("name", "address")
    list_select_related = ("company", "product_type", "institution_type", "city", "district")
    autocomplete_fields = ("city", "district")
    readonly_fields = ("raw_payload", "last_scrape_job", "last_seen_at", "created_at", "updated_at")
