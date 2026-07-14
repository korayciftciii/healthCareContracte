import time

from django.utils import timezone
from django.utils.text import slugify

from companies.models import InsuranceCompany, Network
from geo.models import City, District
from institutions.models import HealthInstitution
from products.models import InstitutionType, ProductType

from .client import TamamlayiciSaglikClient
from .exceptions import ScraperError
from .models import ScrapeJob


class ScrapeJobRunner:
    """Executes a ScrapeJob: resolves its (possibly-wildcard) filters into concrete
    company/product_type/city combinations, paginates the upstream institution
    search for each, and upserts the results into HealthInstitution.

    search-hospital (the real endpoint) is scoped by cityId, so "all cities" (job.city
    left blank) means looping all 81 provinces — this can be a large number of calls;
    prefer setting company+city+product_type for a fast targeted job.
    """

    def __init__(self, client: TamamlayiciSaglikClient | None = None):
        self.client = client or TamamlayiciSaglikClient()

    def run(self, job: ScrapeJob) -> None:
        job.status = ScrapeJob.Status.RUNNING
        job.started_at = timezone.now()
        job.request_params = self._describe_params(job)
        job.append_log("Job started.")
        job.save(update_fields=["status", "started_at", "request_params", "log"])

        had_error = False
        try:
            companies = self._resolve_companies(job)
            product_types = self._resolve_product_types(job)
            cities = self._resolve_cities(job)
            for company in companies:
                for product_type in product_types:
                    if not product_type.external_id:
                        job.append_log(
                            f"ATLANDI: {product_type.code} için tamamlayicisaglik.com "
                            f"productTypeId eşlemesi henüz bilinmiyor (external_id boş)."
                        )
                        continue
                    for city in cities:
                        try:
                            self._scrape_one(job, company, product_type, city)
                        except ScraperError as exc:
                            had_error = True
                            job.error_message = str(exc)
                            job.append_log(
                                f"HATA ({company.code}/{product_type.code}/{city.name}): {exc}"
                            )
            job.status = ScrapeJob.Status.FAILED if had_error and job.result_count == 0 else (
                ScrapeJob.Status.PARTIAL if had_error else ScrapeJob.Status.SUCCESS
            )
        except Exception as exc:  # unexpected/programmer error — still record it, don't crash the thread
            job.status = ScrapeJob.Status.FAILED
            job.error_message = str(exc)
            job.append_log(f"Beklenmeyen hata: {exc}")
        finally:
            job.result_count = job.created_count + job.updated_count
            job.finished_at = timezone.now()
            job.append_log(f"Job finished with status={job.status}.")
            job.save()

    def _resolve_companies(self, job: ScrapeJob):
        if job.company_id:
            return [job.company]
        return list(InsuranceCompany.objects.filter(is_active=True))

    def _resolve_product_types(self, job: ScrapeJob):
        if job.product_type_id:
            return [job.product_type]
        return list(ProductType.objects.all())

    def _resolve_cities(self, job: ScrapeJob):
        if job.city_id:
            return [job.city]
        return list(City.objects.exclude(external_id__isnull=True).order_by("plate_code"))

    def _describe_params(self, job: ScrapeJob) -> dict:
        return {
            "company": job.company.code if job.company_id else "ALL",
            "product_type": job.product_type.code if job.product_type_id else "ALL",
            "city": job.city.name if job.city_id else "ALL (81)",
            "district": job.district.name if job.district_id else "ALL",
            "institution_type": job.institution_type.code if job.institution_type_id else "ALL",
        }

    def _scrape_one(
        self,
        job: ScrapeJob,
        company: InsuranceCompany,
        product_type: ProductType,
        city: City,
    ) -> None:
        page = 1
        while True:
            payload = self.client.get_institutions(
                company_external_id=company.external_id,
                city_id=city.external_id,
                district_id=job.district.external_id if job.district_id else None,
                product_type_id=product_type.external_id,
                page=page,
            )
            for item in payload.get("data", []):
                if self._should_skip(job, item):
                    continue
                self._upsert_institution(job, company, product_type, city, item)

            job.pages_fetched += 1
            job.save(update_fields=["pages_fetched", "created_count", "updated_count"])

            last_page = payload.get("last_page", page)
            if page >= last_page:
                break
            page += 1
            time.sleep(self.client.config["REQUEST_DELAY_SECONDS"])

    def _should_skip(self, job: ScrapeJob, item: dict) -> bool:
        # districtId isn't a confirmed server-side filter param on search-hospital,
        # so re-check client-side using the district_name the API does return.
        if job.district_id:
            district_name = (item.get("district_name") or "").strip().lower()
            if district_name != job.district.name.strip().lower():
                return True

        if job.institution_type_id:
            hospital_type = item.get("hospital_type") or {}
            if hospital_type.get("id") != job.institution_type.external_id:
                return True

        return False

    def _upsert_institution(
        self,
        job: ScrapeJob,
        company: InsuranceCompany,
        product_type: ProductType,
        city: City,
        item: dict,
    ) -> None:
        external_id = item["id"]
        name = item.get("name") or ""

        district = None
        district_name = item.get("district_name")
        if district_name:
            district = District.objects.filter(city=city, name__iexact=district_name).first()

        institution_type = None
        hospital_type = item.get("hospital_type") or {}
        if hospital_type.get("id"):
            institution_type = InstitutionType.objects.filter(
                external_id=hospital_type["id"]
            ).first()

        obj, created = HealthInstitution.objects.update_or_create(
            company=company,
            product_type=product_type,
            external_id=external_id,
            defaults={
                "name": name,
                "slug": slugify(name)[:300],
                "city": city,
                "district": district,
                "institution_type": institution_type,
                "is_active": True,
                "last_seen_at": timezone.now(),
                "last_scrape_job": job,
                "raw_payload": item,
            },
        )

        # item["network_ids"] platformdaki TÜM şirketlerin network id'lerini
        # karışık halde içerir (bir kurum birden fazla sigorta şirketiyle anlaşmalı
        # olabilir) — bu yüzden sadece taranan (company, product_type) kapsamındaki
        # Network'lerle eşleştiriyoruz, diğer şirketlere ait id'ler otomatik elenir.
        network_ids = item.get("network_ids") or []
        if network_ids:
            matched_networks = Network.objects.filter(
                company=company, product_type=product_type, external_id__in=network_ids
            )
            obj.networks.set(matched_networks)
        else:
            obj.networks.clear()

        if created:
            job.created_count += 1
        else:
            job.updated_count += 1
