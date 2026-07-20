from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Province, District


class DistrictInline(TabularInline):
    model = District
    extra = 0
    fields = ("name", "is_active")


@admin.register(Province)
class ProvinceAdmin(ModelAdmin):
    list_display = ("plate_code", "name", "is_active")
    search_fields = ("name", "plate_code")
    ordering = ("plate_code",)
    list_filter = ("is_active",)
    inlines = [DistrictInline]


@admin.register(District)
class DistrictAdmin(ModelAdmin):
    list_display = ("name", "province", "is_active")
    list_filter = ("province", "is_active")
    search_fields = ("name", "province__name")
    autocomplete_fields = ("province",)
