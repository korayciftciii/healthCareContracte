from django.db import models


class InsuranceCompany(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    external_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    logo_url = models.URLField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sigorta Şirketi"
        verbose_name_plural = "Sigorta Şirketleri"
        ordering = ["name"]

    def __str__(self):
        return self.name
