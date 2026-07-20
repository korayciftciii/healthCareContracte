"""BaseScraper: Tüm şirkete özgü scraper'ların implement etmesi gereken abstract sınıf."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.text import slugify

from companies.models import Network, PolicyApplication
from geo.models import City, District
from institutions.models import HealthInstitution, InstitutionContract
from products.models import InstitutionType

if TYPE_CHECKING:
    from companies.models import InsuranceCompany
    from products.models import ProductType
    from scraper.models import ScrapeJob


class BaseScraper(ABC):
    """Şirket bazlı scraper için soyut temel sınıf.

    Her şirket için bir subclass tanımlanır ve @register decorator'ı ile
    SCRAPER_REGISTRY'e kaydedilir. Örnek:

        @register("axa")
        class AxaScraper(BaseScraper):
            source_key = "axa"
            ...
    """

    #: Registry'de kullanılan benzersiz anahtar — subclass'ta tanımlanır
    source_key: str

    @abstractmethod
    def run(self, job: "ScrapeJob") -> None:
        """Job'u başlatır ve sonuçları job üzerine yazar.

        job.status, job.created_count, job.updated_count, job.pages_fetched
        ve job.log bu method tarafından güncellenir.
        """
        ...

    # ------------------------------------------------------------------ #
    # Ortak yardımcı metodlar — tüm scraper'lar kullanabilir             #
    # ------------------------------------------------------------------ #

    def _upsert_institution(
        self,
        *,
        name: str,
        city_name: str,
        district_name: str = "",
        institution_type_name: str = "",
        address: str = "",
        phone: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
        raw_payload: dict | None = None,
    ) -> HealthInstitution:
        """Slug üzerinden global dedup yapar.

        - Slug yoksa: yeni HealthInstitution oluşturur.
        - Slug varsa: eksik alanları (address, phone, lat/lng, city, district vb.) günceller;
          dolu alanlar korunur (scraper'ın verisi üzerine yazmaz).
        """
        city_obj: City | None = None
        if city_name:
            city_obj = (
                City.objects.filter(name__iexact=city_name.strip()).first()
                or City.objects.filter(name__icontains=city_name.strip()).first()
            )

        district_obj: District | None = None
        if district_name and city_obj:
            district_obj = (
                District.objects.filter(city=city_obj, name__iexact=district_name.strip()).first()
                or District.objects.filter(city=city_obj, name__icontains=district_name.strip()).first()
            )
            if not district_obj and district_name.strip():
                district_name_clean = district_name.strip().title() if district_name.strip().islower() or district_name.strip().isupper() else district_name.strip()
                district_obj, _ = District.objects.get_or_create(
                    city=city_obj,
                    name=district_name_clean,
                )

        institution_type_obj: InstitutionType | None = None
        if institution_type_name:
            institution_type_obj = InstitutionType.objects.filter(
                name__iexact=institution_type_name.strip(),
            ).first()

        clean_name = name.strip().title() if name.islower() else name.strip()

        # Önce mevcut veritabanında aynı isim (veya normalize edilmiş isim) + şehir ile kurum var mı kontrol et!
        # Böylece eski/farklı slug üretimi yüzünden veya farklı ilçelerden gelmesi yüzünden mükerrer kayıt oluşmaz.
        inst: HealthInstitution | None = None
        if city_obj:
            # İlçe de biliniyorsa önce hem il hem ilçe ile eşleşene bak
            if district_obj:
                inst = HealthInstitution.objects.filter(
                    city=city_obj, district=district_obj, name__iexact=clean_name
                ).first()
            # Bulunamadıysa (ya da ilçe verilmediyse/eski kayıtta null ise), aynı il içinde aynı isimde olan ilk kaydı al
            if not inst:
                inst = HealthInstitution.objects.filter(
                    city=city_obj, name__iexact=clean_name
                ).first()

        # Şehir nesnesi yoksa veya il ile bulunamadıysa slug / isim ile kontrol et
        city_str = city_obj.name if city_obj else city_name
        slug = self._build_slug(clean_name, city_str, district_name)
        if not inst:
            inst = HealthInstitution.objects.filter(slug=slug).first()

        if not inst:
            # Hiçbir şekilde bulunamadıysa sıfırdan oluştur
            inst = HealthInstitution.objects.create(
                slug=slug,
                name=clean_name,
                address=address,
                phone=phone,
                latitude=latitude,
                longitude=longitude,
                city=city_obj,
                district=district_obj,
                institution_type=institution_type_obj,
                raw_payload=raw_payload or {},
            )
            created = True
        else:
            created = False

        if not created:
            # Varsa: sadece boş/eksik veya null olan alanları güncelle
            changed = False
            if not inst.address and address:
                inst.address = address
                changed = True
            if not inst.phone and phone:
                inst.phone = phone
                changed = True
            if inst.latitude is None and latitude is not None:
                inst.latitude = latitude
                changed = True
            if inst.longitude is None and longitude is not None:
                inst.longitude = longitude
                changed = True
            if not inst.city_id and city_obj:
                inst.city = city_obj
                changed = True
            if not inst.district_id and district_obj:
                inst.district = district_obj
                changed = True
            if not inst.institution_type_id and institution_type_obj:
                inst.institution_type = institution_type_obj
                changed = True
            if raw_payload and not inst.raw_payload:
                inst.raw_payload = raw_payload
                changed = True
            if changed:
                inst.save()

        return inst

    def _upsert_contract(
        self,
        *,
        institution: HealthInstitution,
        company: "InsuranceCompany",
        product_type: "ProductType",
        external_id: str,
        job: "ScrapeJob",
        policy_applications: list[PolicyApplication] | None = None,
        networks: list[Network] | None = None,
        coverage_notes: str = "",
        raw_payload: dict | None = None,
    ) -> tuple[InstitutionContract, bool]:
        """(company, product_type, external_id) üzerinden upsert.

        Returns (contract, created).
        """
        contract, created = InstitutionContract.objects.get_or_create(
            company=company,
            product_type=product_type,
            external_id=str(external_id),
            defaults={
                "institution": institution,
                "coverage_notes": coverage_notes,
                "is_active": True,
                "last_seen_at": timezone.now(),
                "last_scrape_job": job,
                "raw_payload": raw_payload or {},
            },
        )
        if not created:
            update_fields = ["is_active", "last_seen_at", "last_scrape_job"]
            contract.is_active = True
            contract.last_seen_at = timezone.now()
            contract.last_scrape_job = job
            if coverage_notes and not contract.coverage_notes:
                contract.coverage_notes = coverage_notes
                update_fields.append("coverage_notes")
            if raw_payload and not contract.raw_payload:
                contract.raw_payload = raw_payload
                update_fields.append("raw_payload")
            if contract.institution_id != institution.pk:
                contract.institution = institution
                update_fields.append("institution")
            contract.save(update_fields=update_fields)

        if policy_applications is not None:
            # .set() yerine .add() kullanarak, farklı ServiceId (PolicyApplication) taramalarında
            # gelen tüm uygulamaları ve networkleri kontrata ekliyoruz (biriktiriyoruz)
            contract.policy_applications.add(*policy_applications)
            derived_networks = [
                pa.network for pa in policy_applications if pa.network_id
            ]
            all_networks = list({n.pk: n for n in (derived_networks + (networks or []))}.values())
            if all_networks:
                contract.networks.add(*all_networks)
        elif networks is not None:
            contract.networks.add(*networks)

        return contract, created

    @staticmethod
    def _build_slug(name: str, city_name: str, district_name: str = "") -> str:
        """Çakışmaya karşı dayanıklı slug üretir."""
        base = slugify(f"{name}-{city_name}", allow_unicode=False)[:300]
        if not base:
            base = slugify(name, allow_unicode=False)[:300]

        if not HealthInstitution.objects.filter(slug=base).exists():
            return base

        # Eğer aynı slug ile kayıt varsa ve adı + şehri aynıysa, çakışma değildir (aynı kurumdur)
        existing = HealthInstitution.objects.filter(slug=base).first()
        if existing and existing.name.strip().lower() == name.strip().lower():
            return base

        # Önce district ile genişlet (farklı bir kurumsa)
        if district_name:
            extended = slugify(f"{name}-{city_name}-{district_name}", allow_unicode=False)[:300]
            if not HealthInstitution.objects.filter(slug=extended).exists():
                return extended

        return base

    def _resolve_cities(self, job: "ScrapeJob") -> list[City]:
        """Job'un city filtresine göre şehir listesi döner."""
        if job.city_id:
            return [job.city]
        return list(City.objects.exclude(external_id__isnull=True).order_by("plate_code"))
