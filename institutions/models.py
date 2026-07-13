from django.db import models


class HealthInstitution(models.Model):
    company = models.ForeignKey(
        "companies.InsuranceCompany", on_delete=models.CASCADE, related_name="institutions",
    )
    product_type = models.ForeignKey(
        "products.ProductType", on_delete=models.PROTECT, related_name="institutions",
    )
    institution_type = models.ForeignKey(
        "products.InstitutionType", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="institutions",
    )
    city = models.ForeignKey(
        "geo.City", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="institutions",
    )
    district = models.ForeignKey(
        "geo.District", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="institutions",
    )

    external_id = models.PositiveIntegerField()
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_scrape_job = models.ForeignKey(
        "scraper.ScrapeJob", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )
    raw_payload = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sağlık Kurumu"
        verbose_name_plural = "Sağlık Kurumları"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "product_type", "external_id"],
                name="unique_institution_per_company_product",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "city", "product_type"]),
            models.Index(fields=["city", "district"]),
            models.Index(fields=["institution_type"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.company.code})"
