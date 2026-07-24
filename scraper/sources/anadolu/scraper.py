import time
import random

from django.utils import timezone

from companies.models import InsuranceCompany, PolicyApplication
from geo.models import Province
from products.models import ProductType

from ..base import BaseScraper
from ..registry import register
from .client import AnadoluClient
from scraper.exceptions import ScraperError
from scraper.models import ScrapeJob

# Anadolu formundaki "networkCodes" dizisinin sabit ön eki — ürün tipine göre değişir.
# Dizinin son elemanı olarak seçilen networkün kodu eklenir (bkz. AnadoluScraper._scrape_network).
BASE_NETWORK_CODES_BY_PRODUCT = {
    "TSS": ["BT_A", "BT_B", "BT_C", "TSS_A", "TSS_B", "TSS_Tamamlayıcı_Eko", "TSS_Tamamlayıcı"],
    "OSS": ["AHN", "S", "E"],
}

# ÖSS taramalarında eczaneler de dahil edilir (Anadolu formunda "includepharmacies" bayrağı)
INCLUDE_PHARMACIES_BY_PRODUCT = {
    "TSS": False,
    "OSS": True,
}

# Anadolu response'undaki "type" (serbest metin kurum tipi) -> bizim InstitutionType.code eşlemesi.
ANADOLU_INSTITUTION_TYPE_MAP = {
    "HASTANE": "HASTANE",
    "Diğer": "DIGER",
    "Eczane": "ECZANE",
    "Tıbbı Malzeme Cihaz": "MEDIKAL",
    "Evde Bakım Merkezi": "EVDE_BAKIM",
    "Teşhis Tanı Merkezi": "TANI_GORUNTULEME",
    "DOKTOR": "DOKTOR",
    "Atm Tıp Merkezi": "TIP_MERKEZI",
}


@register("anadolu")
class AnadoluScraper(BaseScraper):
    """Anadolu Sigorta için özel scraper eklentisi.

    Anadolu API'sinde ServiceId bazlı alt kırılım yoktur; her Network doğrudan bir
    PolicyApplication'a karşılık gelir (Allianz ile aynı desen). AXA gibi İL bazında
    taranır — countyName boş gönderilir, o ilin TÜM ilçelerindeki kurumlar tek istekte
    döner; her kurumun ilçesi response'taki "countyName" alanından okunur.
    Sadece "Anlaşmalı Sağlık Kurumu" sorgulama tipi hedeflenir (Tüp Bebek, Robotik Cerrahi
    gibi diğer sorgulama tipleri kapsam dışıdır). Kurum tipi filtresi gönderilmez;
    response'taki serbest metin "type" alanından bizim InstitutionType'a eşlenir.
    """

    source_key = "anadolu"
    MIN_DELAY_SECONDS = 2.0
    MAX_DELAY_SECONDS = 5.0

    def __init__(self, client: AnadoluClient | None = None):
        self.client = client or AnadoluClient()

    def run(self, job: ScrapeJob) -> None:
        job.status = ScrapeJob.Status.RUNNING
        job.started_at = timezone.now()
        job.request_params = {
            "source_key": self.source_key,
            "company": "ANADOLU",
            "province": job.province.name if job.province_id else "ALL (81)",
            "product_type": job.product_type.code if job.product_type_id else "ALL",
        }
        job.append_log("Job started [source: anadolu].")
        job.save(update_fields=["status", "started_at", "request_params", "log"])

        company, _ = InsuranceCompany.objects.get_or_create(
            code="ANADOLU",
            defaults={
                "name": "Anadolu Sigorta",
                "slug": "anadolu-sigorta",
                "is_active": True,
            },
        )

        had_error = False
        try:
            product_types = self._resolve_product_types(job)
            provinces = self._resolve_provinces(job)

            for product_type in product_types:
                base_codes = BASE_NETWORK_CODES_BY_PRODUCT.get(product_type.code.upper())
                if base_codes is None:
                    job.append_log(f"ATLANDI: Anadolu için desteklenmeyen ürün tipi ({product_type.code}).")
                    continue

                include_pharmacies = INCLUDE_PHARMACIES_BY_PRODUCT.get(product_type.code.upper(), False)

                policy_apps = PolicyApplication.objects.filter(
                    company=company,
                    product_type=product_type,
                    is_active=True,
                ).order_by("external_service_id")

                if not policy_apps.exists():
                    job.append_log(f"UYARI: {company.code} - {product_type.code} için veritabanında aktif PolicyApplication bulunamadı.")
                    continue

                for province in provinces:
                    for policy_app in policy_apps:
                        try:
                            self._scrape_network(
                                job=job,
                                company=company,
                                product_type=product_type,
                                province=province,
                                base_codes=base_codes,
                                include_pharmacies=include_pharmacies,
                                policy_app=policy_app,
                            )
                        except ScraperError as exc:
                            had_error = True
                            job.error_message = str(exc)
                            job.append_log(
                                f"HATA (ANADOLU/{product_type.code}/{province.name}"
                                f"/network={policy_app.external_service_id}): {exc}"
                            )

            job.status = ScrapeJob.Status.FAILED if had_error and job.result_count == 0 else (
                ScrapeJob.Status.PARTIAL if had_error else ScrapeJob.Status.SUCCESS
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

    def _resolve_product_types(self, job: ScrapeJob) -> list[ProductType]:
        if job.product_type_id:
            return [job.product_type]
        return list(ProductType.objects.filter(code__in=["TSS", "OSS"]))

    def _scrape_network(
        self,
        *,
        job: ScrapeJob,
        company: InsuranceCompany,
        product_type: ProductType,
        province: Province,
        base_codes: list[str],
        include_pharmacies: bool,
        policy_app: PolicyApplication,
    ) -> None:
        network_code = policy_app.external_service_id
        if not network_code:
            return

        network_codes_payload = [*base_codes, network_code]

        try:
            items = self.client.get_institutions(
                city_name=province.name,
                network_codes=network_codes_payload,
                include_pharmacies=include_pharmacies,
            )

            job.pages_fetched += 1
            job.append_log(
                f"{product_type.code}/{province.name}/network={network_code}: "
                f"{len(items)} kurum bulundu."
            )
            job.save(update_fields=["pages_fetched", "log"])

            for item in items:
                self._upsert_item(job, company, product_type, province, policy_app, item)
        finally:
            # Başarılı ya da hatalı olsun, bir sonraki isteğe geçmeden önce
            # her zaman rastgele bir gecikme uygulanır (banlanmayı önlemek için).
            delay = random.uniform(self.MIN_DELAY_SECONDS, self.MAX_DELAY_SECONDS)
            time.sleep(delay)

    def _upsert_item(
        self,
        job: ScrapeJob,
        company: InsuranceCompany,
        product_type: ProductType,
        province: Province,
        policy_app: PolicyApplication,
        item: dict,
    ) -> None:
        name = (item.get("organizationName") or "").strip()
        if not name:
            return

        type_name = (item.get("type") or "").strip()
        institution_type_code = ANADOLU_INSTITUTION_TYPE_MAP.get(type_name, "")

        address = item.get("address") or ""
        phone = item.get("phone") or ""
        # İlçe response'un kendisinden okunur (countyName boş gönderildiği için
        # bu istekte tüm ilçelerin kurumları karışık gelir)
        district_name = item.get("countyName") or ""
        province_name = item.get("cityName") or province.name

        # Anadolu'da alan adları ters: "parallel" = enlem, "meridian" = boylam
        lat, lng = None, None
        try:
            if item.get("parallel"):
                lat = float(str(item["parallel"]).replace(",", "."))
            if item.get("meridian"):
                lng = float(str(item["meridian"]).replace(",", "."))
        except (ValueError, TypeError):
            pass

        inst, inst_created, inst_changed_fields = self._upsert_institution(
            name=name,
            province_name=province_name,
            district_name=district_name,
            institution_type_code=institution_type_code,
            institution_type_name=type_name,
            address=address,
            phone=phone,
            latitude=lat,
            longitude=lng,
            raw_payload=item,
        )

        if inst_created:
            job.append_log(
                f"  + Yeni kurum oluşturuldu: '{inst.name}' (il={province_name}, ilçe={district_name})"
            )
        elif inst_changed_fields:
            job.append_log(
                f"  ~ Kurum güncellendi: '{inst.name}' (id={inst.pk}) — değişen alanlar: {', '.join(inst_changed_fields)}"
            )

        # Response'taki networkCodes listesini serbest metin anlaşma kapsamına çevir
        item_network_codes = item.get("networkCodes")
        coverage = ", ".join(c for c in item_network_codes if c) if isinstance(item_network_codes, list) else ""

        # Kurum anlaşması upsert (skrs = Anadolu'nun kurum kodu)
        institute_code = str(item.get("skrs") or f"anadolu-missing-{inst.pk}")

        contract, created, contract_changed_fields = self._upsert_contract(
            institution=inst,
            company=company,
            product_type=product_type,
            external_id=institute_code,
            job=job,
            policy_applications=[policy_app],
            coverage_notes=coverage,
            raw_payload=item,
        )

        if created:
            job.created_count += 1
            job.append_log(
                f"  + Yeni kontrat oluşturuldu: '{inst.name}' <-> {company.code}/{product_type.code} "
                f"(external_id={institute_code}, policy_app={policy_app.code}, network={policy_app.external_service_id})"
            )
        else:
            job.updated_count += 1
            if contract_changed_fields:
                job.append_log(
                    f"  ~ Kontrat güncellendi: '{inst.name}' <-> {company.code}/{product_type.code} "
                    f"(external_id={institute_code}) — değişen: {', '.join(contract_changed_fields)}"
                )
            else:
                job.append_log(
                    f"  = Kontrat zaten güncel: '{inst.name}' <-> {company.code}/{product_type.code} "
                    f"(external_id={institute_code}, policy_app={policy_app.code})"
                )
