from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import City, District


class DistrictInline(TabularInline):
    model = District
    extra = 0
    fields = ("name", "external_id")


@admin.register(City)
class CityAdmin(ModelAdmin):
    list_display = ("plate_code", "name", "external_id")
    search_fields = ("name",)
    ordering = ("plate_code",)
    inlines = [DistrictInline]


@admin.register(District)
class DistrictAdmin(ModelAdmin):
    list_display = ("name", "city", "external_id")
    list_filter = ("city",)
    search_fields = ("name", "city__name")
    autocomplete_fields = ("city",)
