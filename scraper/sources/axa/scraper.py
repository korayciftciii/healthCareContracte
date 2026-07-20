import time
from typing import TYPE_CHECKING

from django.utils import timezone

from companies.models import InsuranceCompany, Network, PolicyApplication
from geo.models import Province
from products.models import ProductType

from ..base import BaseScraper
from ..registry import register
from .client import AxaClient
from scraper.exceptions import ScraperError
from scraper.models import ScrapeJob

if TYPE_CHECKING:
    pass


@register("axa")
class AxaScraper(BaseScraper):
    """AXA Sigorta için özel scraper eklentisi.

    TSS ve ÖSS için ServiceId bazlı tarama yapar. Tarayacağı servisleri
    doğrudan veritabanındaki aktif PolicyApplication tablosundan dinamik olarak çeker.
    Senkronize edilen her kurum HealthInstitution tablosunda tekelleştirilir, eksik/null alanları
    (ilçe vb.) güncellenir ve PolicyApplication'lar üzerinden InstitutionContract'a bağlanır.
    """

    source_key = "axa"
    DELAY_SECONDS = 0.3

    def __init__(self, client: AxaClient | None = None):
        self.client = client or AxaClient()

    def run(self, job: ScrapeJob) -> None:
        job.status = ScrapeJob.Status.RUNNING
        job.started_at = timezone.now()
        job.request_params = {
            "source_key": self.source_key,
            "company": "AXA",
            "province": job.province.name if job.province_id else "ALL (81)",
            "product_type": job.product_type.code if job.product_type_id else "ALL",
        }
        job.append_log("Job started [source: axa].")
        job.save(update_fields=["status", "started_at", "request_params", "log"])

        # AXA şirketini bul/oluştur
        company, _ = InsuranceCompany.objects.get_or_create(
            code="AXA",
            defaults={
                "name": "AXA Sigorta",
                "slug": "axa-sigorta",
                "is_active": True,
            },
        )

        had_error = False
        try:
            # Tarama yapılacak ürün tipleri (TSS ve/veya ÖSS)
            product_types = self._resolve_product_types(job)
            provinces = self._resolve_provinces(job)

            for product_type in product_types:
                if product_type.code.upper() == "TSS":
                    policy_type_param = "TAMAMLAYICI SİGORTA"
                elif product_type.code.upper() == "OSS":
                    policy_type_param = "ÖZEL SAĞLIK SİGORTASI"
                else:
                    job.append_log(f"ATLANDI: AXA için desteklenmeyen ürün tipi ({product_type.code}).")
                    continue

                # Veritabanında (bizim seeder ile oluşturduğumuz) bu şirkete ve ürün tipine ait
                # aktif tüm PolicyApplication (servis) kayıtlarını çekiyoruz
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
                            self._scrape_service(
                                job=job,
                                company=company,
                                product_type=product_type,
                                province=province,
                                policy_type_param=policy_type_param,
                                policy_app=policy_app,
                            )
                        except ScraperError as exc:
                            had_error = True
                            job.error_message = str(exc)
                            job.append_log(
                                f"HATA (AXA/{product_type.code}/{province.name}/ServiceId={policy_app.external_service_id}): {exc}"
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

    def _scrape_service(
        self,
        *,
        job: ScrapeJob,
        company: InsuranceCompany,
        product_type: ProductType,
        province: Province,
        policy_type_param: str,
        policy_app: PolicyApplication,
    ) -> None:
        service_id = policy_app.external_service_id
        if not service_id:
            return

        items = self.client.get_institutions(
            policy_type=policy_type_param,
            service_id=service_id,
            city_name=province.name,
        )

        job.pages_fetched += 1
        job.save(update_fields=["pages_fetched"])

        for item in items:
            self._upsert_item(job, company, product_type, province, policy_app, item)

        time.sleep(self.DELAY_SECONDS)

    def _upsert_item(
        self,
        job: ScrapeJob,
        company: InsuranceCompany,
        product_type: ProductType,
        province: Province,
        policy_app: PolicyApplication,
        item: dict,
    ) -> None:
        name = item.get("KurumAdi") or ""
        if not name:
            return

        district_name = item.get("Ilce") or ""
        type_name = item.get("Tip") or ""
        address = item.get("Adres") or ""
        phone = item.get("Tel") or ""

        # Enlem/Boylam parsing
        lat, lng = None, None
        try:
            if item.get("GmapEnlem"):
                lat = float(str(item["GmapEnlem"]).replace(",", "."))
            if item.get("GmapBoylam"):
                lng = float(str(item["GmapBoylam"]).replace(",", "."))
        except (ValueError, TypeError):
            pass

        # 1. Saf kurum upsert (global dedup)
        # Var olan kurumda eksik (veya null olan ilçe vb.) alanlar varsa _upsert_institution otomatik günceller
        inst = self._upsert_institution(
            name=name,
            province_name=province.name,
            district_name=district_name,
            institution_type_name=type_name,
            address=address,
            phone=phone,
            latitude=lat,
            longitude=lng,
            raw_payload=item,
        )

        # 2. Kurum anlaşması upsert (kurum kodu ile)
        kurum_kodu = str(item.get("Kurumkodu") or item.get("ID") or f"axa-missing-{inst.pk}")
        coverage = item.get("TamamlayiciUrunAnlasmaDurumu") or ""

        contract, created = self._upsert_contract(
            institution=inst,
            company=company,
            product_type=product_type,
            external_id=kurum_kodu,
            job=job,
            policy_applications=[policy_app],
            coverage_notes=coverage,
            raw_payload=item,
        )

        if created:
            job.created_count += 1
        else:
            job.updated_count += 1
