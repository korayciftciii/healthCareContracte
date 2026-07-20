from django.db import models
from django.utils.text import slugify


class HealthInstitution(models.Model):
    """Şirketten bağımsız, saf sağlık kurumu kaydı.

    Aynı fiziksel kurumun birden fazla sigorta şirketiyle anlaşması olsa da
    burada TEK kayıt bulunur. Şirket/network/ürün bağlantıları
    InstitutionContract tablosunda tutulur.

    Dedup anahtarı: slug = slugify(name + "-" + city_name)
    Scraper her çalışmasında slug'a göre get_or_create yapar;
    varsa eksik alanları (adres, tel, koordinat) günceller.
    """

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

    name = models.CharField(max_length=255)
    # Global dedup anahtarı — slugify(name + "-" + city_name)
    # Kurumlar kalıcıdır; silinmez, sadece kontratları aktif/pasif olur.
    slug = models.SlugField(max_length=320, unique=True)

    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    is_active = models.BooleanField(default=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sağlık Kurumu"
        verbose_name_plural = "Sağlık Kurumları"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["city", "district"]),
            models.Index(fields=["institution_type"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        city_str = f" / {self.city.name}" if self.city_id else ""
        return f"{self.name}{city_str}"

    @classmethod
    def make_slug(cls, name: str, city_name: str, district_name: str = "") -> str:
        """Kurum için canonical slug üretir. Çakışma varsa district de eklenir."""
        base = slugify(f"{name}-{city_name}", allow_unicode=False)
        if len(base) > 300:
            base = base[:300]
        if cls.objects.filter(slug=base).exists():
            extended = slugify(f"{name}-{city_name}-{district_name}", allow_unicode=False)
            if len(extended) > 300:
                extended = extended[:300]
            return extended
        return base


class InstitutionContract(models.Model):
    """Bir kurumun belirli bir sigorta şirketi + ürün tipi kombinasyonundaki anlaşma kaydı.

    Scraper her çalışmasında bu tabloyu günceller:
    - Görülen kurumlar → is_active=True, last_seen_at=now
    - Artık görülmeyen kurumlar → is_active=False

    external_id: Şirketin kendi kurum ID'si (Örn. AXA için Kurumkodu).
    """

    institution = models.ForeignKey(
        HealthInstitution, on_delete=models.CASCADE, related_name="contracts",
    )
    company = models.ForeignKey(
        "companies.InsuranceCompany", on_delete=models.CASCADE, related_name="contracts",
    )
    product_type = models.ForeignKey(
        "products.ProductType", on_delete=models.PROTECT, related_name="contracts",
    )
    # Şirketin kendi ID'si — AXA=Kurumkodu(str), diğerleri=int str
    external_id = models.CharField(max_length=100)

    # Bu anlaşmada geçerli poliçe uygulamaları (network bilgisi buradan türetilir)
    policy_applications = models.ManyToManyField(
        "companies.PolicyApplication", blank=True, related_name="contracts",
    )
    # Performans için ayrı network M2M (policy_applications'dan otomatik set edilir)
    networks = models.ManyToManyField(
        "companies.Network", blank=True, related_name="contracts",
    )

    # Serbest metin anlaşma kapsamı — AXA: TamamlayiciUrunAnlasmaDurumu
    # Örn: "SADECE KARDİYOLOJİ, KALP DAMAR CERRAHİSİ"  ya da "TÜM BRANŞLAR"
    coverage_notes = models.TextField(blank=True)

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
        verbose_name = "Kurum Anlaşması"
        verbose_name_plural = "Kurum Anlaşmaları"
        ordering = ["company", "product_type", "institution"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "product_type", "external_id"],
                name="unique_contract_per_company_product_external",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "product_type", "is_active"]),
            models.Index(fields=["institution", "company"]),
            models.Index(fields=["is_active", "last_seen_at"]),
        ]

    def __str__(self):
        return f"{self.institution.name} ← {self.company.code}/{self.product_type.code}"
