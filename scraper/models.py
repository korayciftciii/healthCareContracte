from django.conf import settings
from django.db import models


class ScrapeJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Bekliyor"
        RUNNING = "RUNNING", "Çalışıyor"
        SUCCESS = "SUCCESS", "Başarılı"
        PARTIAL = "PARTIAL", "Kısmi Başarılı"
        FAILED = "FAILED", "Başarısız"

    company = models.ForeignKey(
        "companies.InsuranceCompany", null=True, blank=True,
        on_delete=models.PROTECT, related_name="scrape_jobs",
        help_text="Boş bırakılırsa tüm şirketler için çalışır.",
    )
    product_type = models.ForeignKey(
        "products.ProductType", null=True, blank=True,
        on_delete=models.PROTECT, related_name="scrape_jobs",
        help_text="Boş bırakılırsa tüm ürün tipleri için çalışır.",
    )
    city = models.ForeignKey(
        "geo.City", null=True, blank=True,
        on_delete=models.PROTECT, related_name="scrape_jobs",
        help_text="Boş bırakılırsa tüm iller için çalışır.",
    )
    district = models.ForeignKey(
        "geo.District", null=True, blank=True,
        on_delete=models.PROTECT, related_name="scrape_jobs",
    )
    institution_type = models.ForeignKey(
        "products.InstitutionType", null=True, blank=True,
        on_delete=models.PROTECT, related_name="scrape_jobs",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="scrape_jobs",
    )
    request_params = models.JSONField(default=dict, blank=True)
    pages_fetched = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    result_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    log = models.TextField(blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Scrape İşi"
        verbose_name_plural = "Scrape İşleri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScrapeJob #{self.pk} ({self.status})"

    def append_log(self, message: str) -> None:
        from django.utils import timezone

        line = f"[{timezone.now().isoformat(timespec='seconds')}] {message}"
        self.log = f"{self.log}\n{line}" if self.log else line
