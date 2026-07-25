from django.conf import settings
from django.db import models


class ScrapeJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Bekliyor"
        RUNNING = "RUNNING", "Çalışıyor"
        SUCCESS = "SUCCESS", "Başarılı"
        PARTIAL = "PARTIAL", "Kısmi Başarılı"
        FAILED = "FAILED", "Başarısız"

    class SourceKey(models.TextChoices):
        AXA = "axa", "AXA"
        ALLIANZ = "allianz", "Allianz"
        ANADOLU = "anadolu", "Anadolu"
        MAPFRE = "mapfre", "Mapfre"

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
    province = models.ForeignKey(
        "geo.Province", null=True, blank=True,
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

    # Hangi scraper plugin'inin kullandığı — "axa", "allianz" vb.
    source_key = models.CharField(
        max_length=50, choices=SourceKey.choices, default=SourceKey.AXA, blank=True,
        help_text="Scraper plugin anahtarı. Boş bırakılırsa 'axa' varsayılır.",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    pid = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Job'u çalıştıran worker process'in PID'i (log stream panelinde gösterilir).",
    )
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
    log_file_path = models.CharField("Log Dosyası", max_length=500, blank=True)

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
        import os
        from pathlib import Path
        from django.conf import settings
        from django.utils import timezone

        line = f"[{timezone.now().isoformat(timespec='seconds')}] {message}"
        self.log = f"{self.log}\n{line}" if self.log else line

        # Eğer log_file_path henüz atanmadıysa otomatik oluştur (logs/AXA/pid_tarih_jobId.log)
        if not self.log_file_path:
            company_code = (self.company.code.upper() if self.company else self.source_key.upper()) or "GENERAL"
            log_dir = Path(settings.BASE_DIR) / "logs" / company_code
            log_dir.mkdir(parents=True, exist_ok=True)
            pid = os.getpid()
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{pid}_{timestamp}_job{self.pk or 'new'}.log"
            self.log_file_path = str(log_dir / filename)

        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

