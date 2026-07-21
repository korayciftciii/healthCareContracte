from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import HealthInstitution, InstitutionContract


class DistrictNullFilter(admin.SimpleListFilter):
    title = "İlçe"
    parameter_name = "district_null"

    def lookups(self, request, model_admin):
        return (("1", "İlçesi boş olanlar"),)

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(district__isnull=True)
        return queryset


class InstitutionContractInline(TabularInline):
    model = InstitutionContract
    extra = 0
    fields = ("company", "product_type", "external_id", "is_active", "coverage_notes", "last_seen_at")
    readonly_fields = ("last_seen_at", "last_scrape_job")
    autocomplete_fields = ("company", "product_type")
    show_change_link = True


@admin.register(HealthInstitution)
class HealthInstitutionAdmin(ModelAdmin):
    list_display = (
        "name",
        "institution_type",
        "province",
        "district",
        "is_active",
        "updated_at",
    )
    list_filter = ("institution_type", "province", "is_active", DistrictNullFilter)
    search_fields = ("name", "address", "slug")
    list_select_related = ("institution_type", "province", "district")
    autocomplete_fields = ("province", "district")
    readonly_fields = ("slug", "raw_payload", "created_at", "updated_at")
    inlines = [InstitutionContractInline]


@admin.register(InstitutionContract)
class InstitutionContractAdmin(ModelAdmin):
    list_display = (
        "institution",
        "company",
        "product_type",
        "external_id",
        "is_active",
        "last_seen_at",
    )
    list_filter = ("company", "product_type", "is_active", "networks")
    search_fields = ("institution__name", "external_id", "coverage_notes")
    list_select_related = ("institution", "company", "product_type")
    autocomplete_fields = ("institution", "company", "product_type")
    filter_horizontal = ("networks", "policy_applications")
    readonly_fields = (
        "raw_payload",
        "last_scrape_job",
        "last_seen_at",
        "created_at",
        "updated_at",
    )
