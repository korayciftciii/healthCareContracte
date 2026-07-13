from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import InstitutionType, ProductType


@admin.register(ProductType)
class ProductTypeAdmin(ModelAdmin):
    list_display = ("name", "code", "external_id")
    search_fields = ("name", "code")


@admin.register(InstitutionType)
class InstitutionTypeAdmin(ModelAdmin):
    list_display = ("name", "code", "external_id")
    search_fields = ("name", "code")
