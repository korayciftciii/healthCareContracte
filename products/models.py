from django.db import models


class ProductType(models.Model):
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10, unique=True)
    external_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ürün Tipi"
        verbose_name_plural = "Ürün Tipleri"
        ordering = ["name"]

    def __str__(self):
        return self.name


class InstitutionType(models.Model):
    name = models.CharField(max_length=60)
    code = models.CharField(max_length=20, unique=True)
    external_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Kurum Tipi"
        verbose_name_plural = "Kurum Tipleri"
        ordering = ["name"]

    def __str__(self):
        return self.name
