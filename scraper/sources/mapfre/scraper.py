import time
import random

from django.utils import timezone

from companies.models import InsuranceCompany, PolicyApplication
from geo.models import Province
from products.models import ProductType

from ..base import BaseScraper
from ..registry import register
from .client import MapfreClient
from scraper.exceptions import ScraperError
from scraper.models import ScrapeJob

# Mapfre formunda payload'a AYNEN bu şekilde gönderilmesi gereken kurum tipi
# etiketleri. Bunlar Mapfre API'sinin kendi sabit listesidir (id değil, isimdir).
MAPFRE_INSTITUTION_TYPES = [
    "HASTANE",
    "AMBULANS",
    "ECZANE",
    "EVDE BAKIM",
    "KLINIK VE POLIKLINIK",
    "TANI MERKEZI",
    "TIBBI MALZEME",
    "TIP MERKEZİ",
]

# Mapfre kurum tipi etiketi -> bizim InstitutionType.code eşlemesi.
# Sorgu institutionType parametresiyle filtrelendiği için, bir isteğin tüm
# sonuçları doğrudan bu tipe aittir (response'taki "kurum_tip" alanını
# ayrıca parse etmeye gerek yoktur).
MAPFRE_INSTITUTION_TYPE_MAP = {
    "HASTANE": "HASTANE",
    "AMBULANS": "AMBULANS",
    "ECZANE": "ECZANE",
    "EVDE BAKIM": "EVDE_BAKIM",
    "KLINIK VE POLIKLINIK": "TIP_MERKEZI",
    "TANI MERKEZI": "TANI_GORUNTULEME",
    "TIBBI MALZEME": "MEDIKAL",
    "TIP MERKEZİ": "TIP_MERKEZI",
}


@register("mapfre")
class MapfreScraper(BaseScraper):
    """Mapfre Sigorta için özel scraper eklentisi.

    Mapfre API'sinde ServiceId bazlı alt kırılım yoktur; her Network
    (networkTypeCode) doğrudan bir PolicyApplication'a karşılık gelir
    (Allianz/Anadolu ile aynı desen). AXA/Anadolu gibi İL bazında taranır —
    districtId boş gönderilir, o ilin TÜM ilçelerindeki kurumlar tek istekte
    döner; her kurumun ilçesi response'taki "ilceadi" alanından okunur.

    Mapfre'ye özgü fark: kurum tipi (institutionType) response'tan değil,
    payload'a ZORUNLU olarak gönderilen sabit bir metin listesinden
    (MAPFRE_INSTITUTION_TYPES) gelir; bu yüzden il × network × kurum tipi
    kombinasyonlarının her biri ayrı bir istektir.
    """

    source_key = "mapfre"
    MIN_DELAY_SECONDS = 2.0
    MAX_DELAY_SECONDS = 5.0

    def __init__(self, client: MapfreClient | None = None):
        self.client = client or MapfreClient()

    def run(self, job: ScrapeJob) -> None:
        job.status = ScrapeJob.Status.RUNNING
        job.started_at = timezone.now()
        job.request_params = {
            "source_key": self.source_key,
            "company": "MAPFRE",
            "province": job.province.name if job.province_id else "ALL (81)",
            "product_type": job.product_type.code if job.product_type_id else "ALL",
        }
        job.append_log("Job started [source: mapfre].")
        job.save(update_fields=["status", "started_at", "request_params", "log"])

        company, _ = InsuranceCompany.objects.get_or_create(
            code="MAPFRE",
            defaults={
                "name": "Mapfre Sigorta",
                "slug": "mapfre-sigorta",
                "is_active": True,
            },
        )

        had_error = False
        try:
            product_types = self._resolve_product_types(job)
            provinces = self._resolve_provinces(job)

            for product_type in product_types:
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
                        for institution_type_label in MAPFRE_INSTITUTION_TYPES:
                            try:
                                self._scrape_network(
                                    job=job,
                                    company=company,
                                    product_type=product_type,
                                    province=province,
                                    policy_app=policy_app,
                                    institution_type_label=institution_type_label,
                                )
                            except ScraperError as exc:
                                had_error = True
                                job.error_message = str(exc)
                                job.append_log(
                                    f"HATA (MAPFRE/{product_type.code}/{province.name}"
                                    f"/network={policy_app.external_service_id}/type={institution_type_label}): {exc}"
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
        policy_app: PolicyApplication,
        institution_type_label: str,
    ) -> None:
        network_code = policy_app.external_service_id
        if not network_code:
            return

        try:
            items = self.client.get_institutions(
                city_id=province.name,
                network_type_code=network_code,
                institution_type=institution_type_label,
            )

            job.pages_fetched += 1
            job.append_log(
                f"{product_type.code}/{province.name}/network={network_code}/type={institution_type_label}: "
                f"{len(items)} kurum bulundu."
            )
            job.save(update_fields=["pages_fetched", "log"])

            for item in items:
                self._upsert_item(job, company, product_type, province, policy_app, institution_type_label, item)
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
        institution_type_label: str,
        item: dict,
    ) -> None:
        name = (item.get("recordname") or "").strip()
        if not name:
            return

        institution_type_code = MAPFRE_INSTITUTION_TYPE_MAP.get(institution_type_label, "")

        address = item.get("address") or ""
        phone = item.get("telephone") or ""
        # İlçe response'un kendisinden okunur (districtId boş gönderildiği için
        # bu istekte tüm ilçelerin kurumları karışık gelir)
        district_name = item.get("ilceadi") or ""
        province_name = item.get("iladi") or province.name

        center_location = item.get("centerLocation") or {}
        lat, lng = None, None
        try:
            if center_location.get("x_coord"):
                lat = float(str(center_location["x_coord"]).replace(",", "."))
            if center_location.get("y_coord"):
                lng = float(str(center_location["y_coord"]).replace(",", "."))
        except (ValueError, TypeError):
            pass

        inst, inst_created, inst_changed_fields = self._upsert_institution(
            name=name,
            province_name=province_name,
            district_name=district_name,
            institution_type_code=institution_type_code,
            institution_type_name=institution_type_label,
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

        coverage = item.get("network_tip_adi") or ""

        # Kurum anlaşması upsert (recordcode = Mapfre'nin kurum kodu)
        institute_code = str(item.get("recordcode") or f"mapfre-missing-{inst.pk}")

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
