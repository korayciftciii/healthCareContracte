import time
import random

from django.utils import timezone

from companies.models import InsuranceCompany, PolicyApplication
from geo.models import Province
from products.models import ProductType

from ..base import BaseScraper
from ..registry import register
from .client import AllianzClient
from scraper.exceptions import ScraperError
from scraper.models import ScrapeJob

# Ürün tipimiz -> Allianz partitionType eşlemesi
# TSS (Tamamlayıcı Sağlık) -> STSS, OSS (Özel Sağlık) -> MDSG (Modüler Sağlık)
PARTITION_TYPE_BY_PRODUCT = {
    "TSS": "STSS",
    "OSS": "MDSG",
}

# Allianz "hospitalType" (instutionType query param'ı) -> bizim InstitutionType.code eşlemesi.
# Allianz response'u kurum tipini DÖNMÜYOR — backend bu bilgiyi sorgu parametresine göre
# filtreleyip gönderiyor. Bu yüzden her kurum tipini AYRI bir istekle taramak zorundayız;
# bir kurum hangi hospitalType isteğinde döndüyse, tipi odur.
ALLIANZ_HOSPITAL_TYPE_MAP = {
    1: "HASTANE",
    2: "TIP_MERKEZI",
    5: "FIZIK_TEDAVI",
    6: "LABORATUAR",
    7: "TANI_GORUNTULEME",
    9: "MEDIKAL",
    10: "ASISTANS",
    11: "EVDE_BAKIM",
    17: "HASTANE",  # ÜNİVERSİTE HASTANESİ -> HASTANE'ye bağlanıyor
    19: "BAKIM_EVI",
}

# Tamamlayıcı Sağlık (STSS) sorgularında taranacak hospitalType'lar
_TSS_HOSPITAL_TYPES = [1, 2, 5, 9, 11, 17, 19]
# Özel Sağlık (MDSG) sorgularında TSS'dekilere ek olarak LABORATUAR/ASİSTANS/TANI_GORUNTULEME de var
_OSS_HOSPITAL_TYPES = _TSS_HOSPITAL_TYPES + [6, 7, 10]

HOSPITAL_TYPES_BY_PRODUCT = {
    "TSS": _TSS_HOSPITAL_TYPES,
    "OSS": _OSS_HOSPITAL_TYPES,
}


@register("allianz")
class AllianzScraper(BaseScraper):
    """Allianz Sigorta için özel scraper eklentisi.

    Allianz API'sinde ServiceId bazlı alt kırılım yoktur; her Network (networkType)
    doğrudan bir PolicyApplication'a karşılık gelir (AXA TSS ile aynı desen).
    İl bazlı taranır (district gönderilmez — o ilin TÜM kurumları gelir).
    Senkronize edilen her kurum HealthInstitution tablosunda tekelleştirilir,
    eksik alanları güncellenir ve PolicyApplication üzerinden InstitutionContract'a bağlanır.
    """

    source_key = "allianz"
    MIN_DELAY_SECONDS = 2.0
    MAX_DELAY_SECONDS = 5.0

    def __init__(self, client: AllianzClient | None = None):
        self.client = client or AllianzClient()

    def run(self, job: ScrapeJob) -> None:
        job.status = ScrapeJob.Status.RUNNING
        job.started_at = timezone.now()
        job.request_params = {
            "source_key": self.source_key,
            "company": "ALLIANZ",
            "province": job.province.name if job.province_id else "ALL (81)",
            "product_type": job.product_type.code if job.product_type_id else "ALL",
        }
        job.append_log("Job started [source: allianz].")
        job.save(update_fields=["status", "started_at", "request_params", "log"])

        company, _ = InsuranceCompany.objects.get_or_create(
            code="ALLIANZ",
            defaults={
                "name": "Allianz Sigorta",
                "slug": "allianz-sigorta",
                "is_active": True,
            },
        )

        had_error = False
        try:
            product_types = self._resolve_product_types(job)
            provinces = self._resolve_provinces(job)

            for product_type in product_types:
                partition_type_param = PARTITION_TYPE_BY_PRODUCT.get(product_type.code.upper())
                if not partition_type_param:
                    job.append_log(f"ATLANDI: Allianz için desteklenmeyen ürün tipi ({product_type.code}).")
                    continue

                hospital_types = HOSPITAL_TYPES_BY_PRODUCT.get(product_type.code.upper(), [])
                if not hospital_types:
                    job.append_log(f"ATLANDI: {product_type.code} için taranacak hospitalType tanımlı değil.")
                    continue

                policy_apps = PolicyApplication.objects.filter(
                    company=company,
                    product_type=product_type,
                    is_active=True,
                ).order_by("external_service_id")

                if not policy_apps.exists():
                    job.append_log(f"UYARI: {company.code} - {product_type.code} için veritabanında aktif PolicyApplication bulunamadı.")
                    continue

                for province in provinces:
                    if not province.plate_code:
                        job.append_log(f"ATLANDI: '{province.name}' için plaka kodu tanımlı değil.")
                        continue

                    for policy_app in policy_apps:
                        for hospital_type in hospital_types:
                            try:
                                self._scrape_network(
                                    job=job,
                                    company=company,
                                    product_type=product_type,
                                    province=province,
                                    partition_type_param=partition_type_param,
                                    policy_app=policy_app,
                                    hospital_type=hospital_type,
                                )
                            except ScraperError as exc:
                                had_error = True
                                job.error_message = str(exc)
                                job.append_log(
                                    f"HATA (ALLIANZ/{product_type.code}/{province.name}/networkType={policy_app.external_service_id}"
                                    f"/hospitalType={hospital_type}): {exc}"
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
        partition_type_param: str,
        policy_app: PolicyApplication,
        hospital_type: int,
    ) -> None:
        network_type = policy_app.external_service_id
        if not network_type:
            return

        institution_type_code = ALLIANZ_HOSPITAL_TYPE_MAP.get(hospital_type, "")

        try:
            items = self.client.get_institutions(
                city_plate_code=province.plate_code,
                partition_type=partition_type_param,
                network_type=network_type,
                institution_type=hospital_type,
            )

            job.pages_fetched += 1
            job.append_log(
                f"{product_type.code}/{province.name}/networkType={network_type}/hospitalType={hospital_type}: "
                f"{len(items)} kurum bulundu."
            )
            job.save(update_fields=["pages_fetched", "log"])

            for item in items:
                self._upsert_item(job, company, product_type, province, policy_app, institution_type_code, item)
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
        institution_type_code: str,
        item: dict,
    ) -> None:
        name = (item.get("instituteName") or "").strip()
        if not name:
            return

        address = item.get("address") or ""
        phone = item.get("phone") or ""

        # Enlem/Boylam parsing (Allianz string olarak dönebiliyor)
        lat, lng = None, None
        try:
            if item.get("latitude"):
                lat = float(str(item["latitude"]).replace(",", "."))
            if item.get("longitude"):
                lng = float(str(item["longitude"]).replace(",", "."))
        except (ValueError, TypeError):
            pass

        # Allianz response'unda ilçe bilgisi yok (sadece serbest metin address).
        # 1. Saf kurum upsert (global dedup) — district_name boş geçilir,
        # mevcut kurumda ilçe zaten varsa dokunulmaz, yoksa null kalır.
        inst, inst_created, inst_changed_fields = self._upsert_institution(
            name=name,
            province_name=province.name,
            district_name="",
            institution_type_code=institution_type_code,
            address=address,
            phone=phone,
            latitude=lat,
            longitude=lng,
            raw_payload=item,
        )

        if inst_created:
            job.append_log(
                f"  + Yeni kurum oluşturuldu: '{inst.name}' (il={province.name})"
            )
        elif inst_changed_fields:
            job.append_log(
                f"  ~ Kurum güncellendi: '{inst.name}' (id={inst.pk}) — değişen alanlar: {', '.join(inst_changed_fields)}"
            )

        # institutePartitions açıklamalarını coverage_notes'a çevir (serbest metin anlaşma kapsamı)
        partitions = item.get("institutePartitions") or []
        coverage = ", ".join(
            p.get("explanation", "").strip() for p in partitions if p.get("explanation")
        )

        # 2. Kurum anlaşması upsert (instituteCode ile)
        institute_code = str(item.get("instituteCode") or f"allianz-missing-{inst.pk}")

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
                f"(external_id={institute_code}, policy_app={policy_app.code}, networkType={policy_app.external_service_id})"
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
