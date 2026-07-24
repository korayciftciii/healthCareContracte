from django.db import models


class InsuranceCompany(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
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
    """Bir sigorta şirketinin ürün tipi (örn. ÖSS) içindeki alt-kapsam/plan grubu (Örn: Network 1, Network 2, Network 3)."""

    company = models.ForeignKey(
        InsuranceCompany, on_delete=models.CASCADE, related_name="networks",
    )
    product_type = models.ForeignKey(
        "products.ProductType", on_delete=models.CASCADE, related_name="networks",
    )
    # Şirketin kendi network kodu — AXA/Allianz'da sayısal (ServiceId/networkType),
    # Anadolu'da metinsel (örn. "TSS_Tamamlayıcı", "AHN") olabildiği için CharField.
    external_id = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=120)
    shown_by_default = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Network / Plan Grubu"
        verbose_name_plural = "Network'ler / Plan Grupları"
        ordering = ["company", "product_type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "product_type", "external_id"],
                name="unique_network_per_company_product",
                condition=models.Q(external_id__isnull=False),
            ),
        ]

    def __str__(self):
        return f"{self.company.code}/{self.product_type.code} - {self.name}"


class PolicyApplication(models.Model):
    """Bir network altında tanımlı poliçe uygulaması.

    Her PolicyApplication, şirketin API'sinde bir ServiceId'ye karşılık gelir.
    Kurumlar bu ServiceId'ler ile sorgulanır ve InstitutionContract'a bağlanır.

    Örnekler (AXA):
      TSS → "Sağlığım Tamam"           ServiceId=17  (network=Sağlığım Tamam Network)
      TSS → "Tutumlu"                  ServiceId=24
      ÖSS Network 1 → ana              ServiceId=34
      ÖSS Network 1 → CHECK UP         ServiceId=56
      ÖSS Network 2 → Mamografi+USG    ServiceId=39
    """

    company = models.ForeignKey(
        InsuranceCompany, on_delete=models.CASCADE, related_name="policy_applications",
    )
    product_type = models.ForeignKey(
        "products.ProductType", on_delete=models.PROTECT, related_name="policy_applications",
    )
    # TSS'de her plan kendi network'ü; ÖSS'de bir network altında birden fazla uygulama
    network = models.ForeignKey(
        Network, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="policy_applications",
    )

    name = models.CharField(
        max_length=150,
        help_text="İnsan-okunabilir isim. Örn: 'Sağlığım Tamam Sigortası', 'CHECK UP'",
    )
    code = models.CharField(
        max_length=80,
        help_text="İç kod. Örn: 'AXA_TSS_17'. Otomatik üretilir veya manuel girilebilir.",
    )
    # Şirketin API'sindeki ID — AXA için "17", başka şirketlerde farklı format olabilir
    external_service_id = models.CharField(
        max_length=50,
        help_text="Şirket API'sindeki servis/filtre ID'si. Örn AXA için '17'.",
    )

    is_active = models.BooleanField(default=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Poliçe Uygulaması"
        verbose_name_plural = "Poliçe Uygulamaları"
        ordering = ["company", "product_type", "network", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "product_type", "external_service_id"],
                name="unique_policy_app_per_company_product_service",
            ),
        ]

    def __str__(self):
        network_str = f" / {self.network.name}" if self.network_id else ""
        return f"{self.company.code}/{self.product_type.code}{network_str} → {self.name}"
