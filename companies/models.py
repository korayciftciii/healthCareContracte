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


class Network(models.Model):
    """Bir sigorta şirketinin bir ürün tipi (TSS/ÖSS) içindeki alt-kapsam tier'ı
    (örn. AXA TSS için "Sağlığım Tamam Nw." vs "Tutumlu"; Türkiye TSS için
    "Altın"/"Platin"/"Bronz"). GET /internal-api/networks?companyIds[]=..&productTypeId=..
    'dan gelir. external_id, aynı şirketin farklı ürün tiplerinde farklı id/isim
    setleri kullanabiliyor (canlı doğrulandı — AXA TSS: 22/23/473, AXA ÖSS:
    3814/3815/3816, hiç ortak id yok) — bu yüzden company+product_type ile scope'lanır.
    Bazı şirketlerin (örn. Mapfre) hiç network'ü yok, bu normaldir."""

    company = models.ForeignKey(
        InsuranceCompany, on_delete=models.CASCADE, related_name="networks",
    )
    product_type = models.ForeignKey(
        "products.ProductType", on_delete=models.CASCADE, related_name="networks",
    )
    external_id = models.PositiveIntegerField()
    name = models.CharField(max_length=120)
    shown_by_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Network"
        verbose_name_plural = "Network'ler"
        ordering = ["company", "product_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "product_type", "external_id"],
                name="unique_network_per_company_product",
            ),
        ]

    def __str__(self):
        return f"{self.company.code}/{self.product_type.code} - {self.name}"
