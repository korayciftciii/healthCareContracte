"""HDI Sigorta scraper eklentisi.

Tarama mantığı:
  for province in provinces:                     # 81 il
    districts = client.get_districts(plate_code)   # HDI'dan ilçe listesi alınır
    for district in districts:                     # ilçe başına istek
      for product_type in [OSS, TSS]:
        for policy_app in policy_apps[product_type]:  # her productId
          for inst_type_id, inst_type_code in HDI_INSTITUTION_TYPES:
            items = client.get_institutions(...)
            for item in items:
              _upsert_institution(...)
              _upsert_contract(...)  # hibrit ürün (538) → 2x çağrı

Gecikme (anti-bot):
  Her API isteğinden sonra MIN_DELAY_SECONDS..MAX_DELAY_SECONDS arası random sleep.
  İlçe listesi (GET) için ek gecikme uygulanmaz (hafif endpoint).

external_id stratejisi:
  HDI response'ta benzersiz kurum ID'si yok. Bu nedenle compound key kullanılır:
    f"hdi-{product_id}-{district_id}-{slugified_name}"
  Aynı scraper çalışmalarında tekrarlanabilir → duplicate oluşmaz.
  Farklı product_id'ler aynı kurumu paylaşabilir (örn. bir hastane hem 366 hem 373'te
  görünebilir) — bu durumda aynı HealthInstitution kaydına farklı InstitutionContract
  satırları eklenir (company+product_type+external_id unique constraint'i).
"""
from __future__ import annotations

import time
import random
from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.text import slugify

from companies.models import InsuranceCompany, PolicyApplication
from geo.models import Province
from products.models import ProductType, InstitutionType

from ..base import BaseScraper
from ..registry import register
from .client import HdiClient
from scraper.exceptions import ScraperError
from scraper.models import ScrapeJob

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# HDI institution type ID → bizim InstitutionType.code eşlemesi
# ---------------------------------------------------------------------------
# institutionTypeId → code
HDI_INSTITUTION_TYPE_MAP: dict[str, str] = {
    "1":  "HASTANE",          # Hastane
    "2":  "ECZANE",           # Eczane
    "3":  "DOKTOR",           # Doktor
    "4":  "TIP_MERKEZI",      # Poliklinik  → Tıp Merkezi & Poliklinik
    "5":  "TANI_GORUNTULEME", # Tanı Merkezi
    "9":  "EVDE_BAKIM",       # Evde Bakım
    "12": "TIP_MERKEZI",      # Tıp Merkezi → Tıp Merkezi & Poliklinik
    "13": "OPTIK",            # Optik
    "14": "MEDIKAL",          # Medikal
    "15": "DIS",              # Diş
    "16": "YURTDISI",         # Yurtdışı
    "17": "HASTANE",          # Üniversite → Hastane (üniversite hastaneleri)
}

# Scraper'da döngüye girecek institution type ID'leri (tam liste)
HDI_INSTITUTION_TYPE_IDS = [
    "1",   # Hastane
    "2",   # Eczane
    "3",   # Doktor
    "4",   # Poliklinik
    "5",   # Tanı Merkezi
    "9",   # Evde Bakım
    "12",  # Tıp Merkezi
    "13",  # Optik
    "14",  # Medikal
    "15",  # Diş
    "16",  # Yurtdışı
    "17",  # Üniversite
]

# Hibrit productId — hem TSS hem ÖSS InstitutionContract oluşturulacak
HDI_HYBRID_PRODUCT_ID = "538"


@register("hdi")
class HdiScraper(BaseScraper):
    """HDI Sigorta için özel scraper eklentisi.

    AXA/Allianz/Anadolu/Mapfre ile aynı BaseScraper altyapısını kullanır.

    HDI API farkı:
      - İlçe bazında tarama: önce GET /districts?provinceId={plate_code} ile
        ilçeler alınır, sonra her ilçe için POST /contracted-health-institutions
        isteği gönderilir.
      - provinceId = plaka kodu (1..81), başında 0 YOK.
      - Hibrit ürün (productId=538): hem TSS hem ÖSS policy application'larıyla
        _upsert_contract iki kez çağrılır; her ürün tipi için ayrı kontrat kaydı.
      - external_id: compound key (HDI'nın benzersiz kurum ID'si yok).
    """

    source_key = "hdi"
    MIN_DELAY_SECONDS = 2.5
    MAX_DELAY_SECONDS = 6.0

    def __init__(self, client: HdiClient | None = None):
        self.client = client or HdiClient()
        # province_id → district list cache (aynı il için tekrar GET yapılmasın)
        self._district_cache: dict[str, list[dict]] = {}

    # ------------------------------------------------------------------ #
    # Ana giriş noktası                                                   #
    # ------------------------------------------------------------------ #

    def run(self, job: ScrapeJob) -> None:
        job.status = ScrapeJob.Status.RUNNING
        job.started_at = timezone.now()
        job.request_params = {
            "source_key": self.source_key,
            "company": "HDI",
            "province": job.province.name if job.province_id else "ALL (81)",
            "product_type": job.product_type.code if job.product_type_id else "ALL",
        }
        job.append_log("Job started [source: hdi].")
        job.save(update_fields=["status", "started_at", "request_params", "log"])

        company, _ = InsuranceCompany.objects.get_or_create(
            code="HDI",
            defaults={
                "name": "HDI Sigorta",
                "slug": "hdi-sigorta",
                "is_active": True,
            },
        )

        had_error = False
        try:
            product_types = self._resolve_product_types(job)
            provinces = self._resolve_provinces(job)

            for province in provinces:
                # Plaka kodu = HDI'nın provinceId parametresi (başında 0 YOK)
                plate_code = str(int(province.plate_code)) if province.plate_code else None
                if not plate_code:
                    job.append_log(
                        f"ATLANDI: {province.name} için plaka kodu bulunamadı — ilçe listesi alınamaz."
                    )
                    continue

                # İlçe listesini al (province başına bir kez, cache'lenir)
                districts = self._get_districts_cached(job, plate_code, province.name)
                if not districts:
                    job.append_log(
                        f"UYARI: {province.name} (provinceId={plate_code}) için ilçe listesi boş veya alınamadı."
                    )
                    continue

                for product_type in product_types:
                    policy_apps = PolicyApplication.objects.filter(
                        company=company,
                        product_type=product_type,
                        is_active=True,
                    ).order_by("external_service_id")

                    if not policy_apps.exists():
                        job.append_log(
                            f"UYARI: {company.code} - {product_type.code} için "
                            f"veritabanında aktif PolicyApplication bulunamadı."
                        )
                        continue

                    for district in districts:
                        district_id = str(district.get("id", ""))
                        district_name = district.get("name", "")
                        if not district_id:
                            continue

                        for policy_app in policy_apps:
                            product_id = policy_app.external_service_id
                            if not product_id:
                                continue

                            for inst_type_id in HDI_INSTITUTION_TYPE_IDS:
                                try:
                                    self._scrape_combination(
                                        job=job,
                                        company=company,
                                        product_type=product_type,
                                        province=province,
                                        province_id=plate_code,
                                        district_id=district_id,
                                        district_name=district_name,
                                        policy_app=policy_app,
                                        product_id=product_id,
                                        inst_type_id=inst_type_id,
                                    )
                                except ScraperError as exc:
                                    had_error = True
                                    job.error_message = str(exc)
                                    job.append_log(
                                        f"HATA (HDI/{product_type.code}/{province.name}"
                                        f"/district={district_name}/product={product_id}"
                                        f"/type={inst_type_id}): {exc}"
                                    )

            job.status = (
                ScrapeJob.Status.FAILED
                if had_error and job.result_count == 0
                else (ScrapeJob.Status.PARTIAL if had_error else ScrapeJob.Status.SUCCESS)
            )
        except Exception as exc:
            job.status = ScrapeJob.Status.FAILED
            job.error_message = str(exc)
            job.append_log(f"Beklenmeyen hata: {exc}")
        finally:
            job.result_count = job.created_count + job.updated_count
            job.finished_at = timezone.now()
            job.append_log(f"Job finished with status={job.status}.")
            job.save()

    # ------------------------------------------------------------------ #
    # İlçe listesi (cache destekli)                                      #
    # ------------------------------------------------------------------ #

    def _get_districts_cached(
        self,
        job: ScrapeJob,
        province_id: str,
        province_name: str,
    ) -> list[dict]:
        """Province başına ilçe listesini bir kez alır, sonrasında cache'den döner."""
        if province_id in self._district_cache:
            return self._district_cache[province_id]

        try:
            districts = self.client.get_districts(province_id=province_id)
            job.append_log(
                f"İlçe listesi alındı: {province_name} (provinceId={province_id})"
                f" → {len(districts)} ilçe."
            )
            job.save(update_fields=["log"])
        except ScraperError as exc:
            job.append_log(
                f"HATA: {province_name} için ilçe listesi alınamadı: {exc}"
            )
            job.save(update_fields=["log"])
            districts = []

        self._district_cache[province_id] = districts
        return districts

    # ------------------------------------------------------------------ #
    # Tek kombinasyon için tarama                                         #
    # ------------------------------------------------------------------ #

    def _scrape_combination(
        self,
        *,
        job: ScrapeJob,
        company: InsuranceCompany,
        product_type: ProductType,
        province: Province,
        province_id: str,
        district_id: str,
        district_name: str,
        policy_app: PolicyApplication,
        product_id: str,
        inst_type_id: str,
    ) -> None:
        try:
            items = self.client.get_institutions(
                product_id=product_id,
                province_id=province_id,
                district_id=district_id,
                institution_type_id=inst_type_id,
            )

            job.pages_fetched += 1
            if items:
                job.append_log(
                    f"{product_type.code}/{province.name}/{district_name}"
                    f"/product={product_id}/type={inst_type_id}: {len(items)} kurum."
                )
            job.save(update_fields=["pages_fetched", "log"])

            for item in items:
                self._upsert_item(
                    job=job,
                    company=company,
                    product_type=product_type,
                    province=province,
                    district_name=district_name,
                    district_id=district_id,
                    policy_app=policy_app,
                    product_id=product_id,
                    inst_type_id=inst_type_id,
                    item=item,
                )
        finally:
            # Her API isteğinden sonra insan benzeri gecikme — anti-bot
            delay = random.uniform(self.MIN_DELAY_SECONDS, self.MAX_DELAY_SECONDS)
            time.sleep(delay)

    # ------------------------------------------------------------------ #
    # Tek kurum kaydı işleme                                              #
    # ------------------------------------------------------------------ #

    def _upsert_item(
        self,
        *,
        job: ScrapeJob,
        company: InsuranceCompany,
        product_type: ProductType,
        province: Province,
        district_name: str,
        district_id: str,
        policy_app: PolicyApplication,
        product_id: str,
        inst_type_id: str,
        item: dict,
    ) -> None:
        name = (item.get("description") or "").strip()
        if not name:
            return

        address = (item.get("address") or "").strip()
        phone = (item.get("phone") or "").strip()
        coverage_notes = (item.get("hcnwDetailDescription") or "").strip()

        # Koordinat parse
        lat, lng = None, None
        try:
            raw_lat = item.get("latitude")
            raw_lng = item.get("longitude")
            if raw_lat:
                lat = float(str(raw_lat).replace(",", "."))
            if raw_lng:
                lng = float(str(raw_lng).replace(",", "."))
        except (ValueError, TypeError):
            pass

        # institution_type_code lookup
        institution_type_code = HDI_INSTITUTION_TYPE_MAP.get(inst_type_id, "")

        # 1. Saf kurum upsert (global dedup)
        inst, inst_created, inst_changed_fields = self._upsert_institution(
            name=name,
            province_name=province.name,
            district_name=district_name,
            institution_type_code=institution_type_code,
            institution_type_name=item.get("typeDescription") or "",
            address=address,
            phone=phone,
            latitude=lat,
            longitude=lng,
            raw_payload=item,
        )

        if inst_created:
            job.append_log(
                f"  + Yeni kurum: '{inst.name}' "
                f"(il={province.name}, ilçe={district_name or '-'}, tip={institution_type_code or '-'})"
            )
        elif inst_changed_fields:
            job.append_log(
                f"  ~ Kurum güncellendi: '{inst.name}' (id={inst.pk})"
                f" — değişen: {', '.join(inst_changed_fields)}"
            )

        # 2. external_id compound key (HDI'nın kendi ID'si yok)
        external_id = f"hdi-{product_id}-{district_id}-{slugify(name, allow_unicode=False)[:80]}"

        # 3. Kontrat upsert
        #    Hibrit ürün (538): hem TSS hem ÖSS product_type'a ayrı kontrat
        if product_id == HDI_HYBRID_PRODUCT_ID:
            self._upsert_and_log_contract(
                job=job, inst=inst, company=company,
                product_type=product_type,
                external_id=external_id,
                policy_app=policy_app,
                coverage_notes=coverage_notes,
                item=item,
            )
            # Diğer product_type için de kontrat oluştur
            other_product_type_code = "TSS" if product_type.code == "OSS" else "OSS"
            try:
                other_product_type = ProductType.objects.get(code=other_product_type_code)
                # Diğer tip için uygun policy application'ı bul
                other_policy_app = PolicyApplication.objects.filter(
                    company=company,
                    product_type=other_product_type,
                    external_service_id=HDI_HYBRID_PRODUCT_ID,
                    is_active=True,
                ).first()
                if other_policy_app:
                    other_external_id = (
                        f"hdi-{product_id}-{district_id}-{slugify(name, allow_unicode=False)[:80]}"
                        f"-{other_product_type_code.lower()}"
                    )
                    self._upsert_and_log_contract(
                        job=job, inst=inst, company=company,
                        product_type=other_product_type,
                        external_id=other_external_id,
                        policy_app=other_policy_app,
                        coverage_notes=coverage_notes,
                        item=item,
                    )
            except ProductType.DoesNotExist:
                pass
        else:
            self._upsert_and_log_contract(
                job=job, inst=inst, company=company,
                product_type=product_type,
                external_id=external_id,
                policy_app=policy_app,
                coverage_notes=coverage_notes,
                item=item,
            )

    def _upsert_and_log_contract(
        self,
        *,
        job: ScrapeJob,
        inst,
        company: InsuranceCompany,
        product_type: ProductType,
        external_id: str,
        policy_app: PolicyApplication,
        coverage_notes: str,
        item: dict,
    ) -> None:
        """_upsert_contract'ı çağırır ve sonucu job log'una yazar."""
        contract, created, contract_changed_fields = self._upsert_contract(
            institution=inst,
            company=company,
            product_type=product_type,
            external_id=external_id,
            job=job,
            policy_applications=[policy_app],
            coverage_notes=coverage_notes,
            raw_payload=item,
        )

        if created:
            job.created_count += 1
            job.append_log(
                f"  + Kontrat: '{inst.name}' ↔ {company.code}/{product_type.code} "
                f"(ext={external_id}, policy={policy_app.code})"
            )
        else:
            job.updated_count += 1
            if contract_changed_fields:
                job.append_log(
                    f"  ~ Kontrat güncellendi: '{inst.name}' ↔ {company.code}/{product_type.code} "
                    f"(ext={external_id}) — değişen: {', '.join(contract_changed_fields)}"
                )

    # ------------------------------------------------------------------ #
    # Yardımcı                                                            #
    # ------------------------------------------------------------------ #

    def _resolve_product_types(self, job: ScrapeJob) -> list[ProductType]:
        if job.product_type_id:
            return [job.product_type]
        return list(ProductType.objects.filter(code__in=["TSS", "OSS"]))
