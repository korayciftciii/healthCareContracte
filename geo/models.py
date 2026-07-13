from django.db import models


class City(models.Model):
    name = models.CharField(max_length=60)
    plate_code = models.PositiveSmallIntegerField(unique=True)
    external_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "İl"
        verbose_name_plural = "İller"
        ordering = ["plate_code"]

    def __str__(self):
        return f"{self.plate_code} - {self.name}"


class District(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField(max_length=80)
    external_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "İlçe"
        verbose_name_plural = "İlçeler"
        ordering = ["city__plate_code", "name"]
        constraints = [
            models.UniqueConstraint(fields=["city", "name"], name="unique_district_per_city"),
        ]
        indexes = [
            models.Index(fields=["city", "external_id"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.city.name})"
