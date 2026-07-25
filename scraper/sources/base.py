"""BaseScraper: Tüm şirkete özgü scraper'ların implement etmesi gereken abstract sınıf."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.utils import timezone
from django.utils.text import slugify

from companies.models import Network, PolicyApplication
from geo.models import Province, District
from institutions.models import HealthInstitution, InstitutionContract
from products.models import InstitutionType

if TYPE_CHECKING:
    from companies.models import InsuranceCompany
    from products.models import ProductType
    from scraper.models import ScrapeJob


def _normalize_tr(value: str) -> str:
    """Türkçe İ/I/ı/i harflerini tek bir forma indirger.

    Postgres'in varsayılan (Türkçe olmayan) locale'inde UPPER()/LOWER() fonksiyonları
    Türkçe'ye özgü nokta kurallarını bilmez: örn. 'i'.upper() -> 'I' (noktasız) verir,
    oysa DB'de il/ilçe isimleri gerçek Türkçe büyük harfle ('İ', noktalı) saklanır.
    Bu yüzden name__iexact/icontains gibi DB-taraflı case-insensitive karşılaştırmalar
    "Yüreğir" gibi isimlerde sessizce eşleşmeyi kaçırabilir. Bu fonksiyon, il/ilçe
    eşlemesini Python tarafında normalize ederek locale'den bağımsız hale getirir.
    """
    return value.strip().replace("İ", "i").replace("I", "i").replace("ı", "i").lower()


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
        province_name: str,
        district_name: str = "",
        institution_type_name: str = "",
        institution_type_code: str = "",
        address: str = "",
        phone: str = "",
        latitude: float | None = None,
        longitude: float | None = None,
        raw_payload: dict | None = None,
    ) -> tuple[HealthInstitution, bool, list[str]]:
        """Slug üzerinden global dedup yapar.

        - Slug yoksa: yeni HealthInstitution oluşturur.
        - Slug varsa: eksik alanları (address, phone, lat/lng, province, district vb.) günceller;
          dolu alanlar korunur (scraper'ın verisi üzerine yazmaz).
        - İl/ilçe tablosu (geo app) eksiksiz seedlenmiştir; ilçe eşleşmezse burada
          otomatik ilçe OLUŞTURULMAZ, sadece null bırakılır (migrate_institutions_from_api
          komutuyla aynı yaklaşım).
        """
        province_obj: Province | None = None
        if province_name:
            target_province = _normalize_tr(province_name)
            for p in Province.objects.all():
                if _normalize_tr(p.name) == target_province:
                    province_obj = p
                    break
            if not province_obj:
                for p in Province.objects.all():
                    norm_name = _normalize_tr(p.name)
                    if target_province in norm_name or norm_name in target_province:
                        province_obj = p
                        break

        district_obj: District | None = None
        if district_name and province_obj:
            target_district = _normalize_tr(district_name)
            candidates = list(District.objects.filter(province=province_obj))
            for d in candidates:
                if _normalize_tr(d.name) == target_district:
                    district_obj = d
                    break
            if not district_obj:
                for d in candidates:
                    norm_name = _normalize_tr(d.name)
                    if target_district in norm_name or norm_name in target_district:
                        district_obj = d
                        break

        # Kod biliniyorsa (örn. Allianz hospitalType eşlemesi) önce kod ile eşleştir;
        # bulunamazsa serbest metin isim (örn. AXA "Tip" alanı) ile dene.
        institution_type_obj: InstitutionType | None = None
        if institution_type_code:
            institution_type_obj = InstitutionType.objects.filter(
                code__iexact=institution_type_code.strip(),
            ).first()
        if not institution_type_obj and institution_type_name:
            institution_type_obj = InstitutionType.objects.filter(
                name__iexact=institution_type_name.strip(),
            ).first()

        clean_name = name.strip().title() if name.islower() else name.strip()

        # Önce mevcut veritabanında aynı isim (veya normalize edilmiş isim) + il ile kurum var mı kontrol et!
        # Böylece eski/farklı slug üretimi yüzünden veya farklı ilçelerden gelmesi yüzünden mükerrer kayıt oluşmaz.
        inst: HealthInstitution | None = None
        if province_obj:
            # İlçe de biliniyorsa önce hem il hem ilçe ile eşleşene bak
            if district_obj:
                inst = HealthInstitution.objects.filter(
                    province=province_obj, district=district_obj, name__iexact=clean_name
                ).first()
            # Bulunamadıysa (ya da ilçe verilmediyse/eski kayıtta null ise), aynı il içinde aynı isimde olan ilk kaydı al
            if not inst:
                inst = HealthInstitution.objects.filter(
                    province=province_obj, name__iexact=clean_name
                ).first()

        # İl nesnesi yoksa veya il ile bulunamadıysa slug / isim ile kontrol et
        province_str = province_obj.name if province_obj else province_name
        slug = self._build_slug(clean_name, province_str, district_name)
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
                province=province_obj,
                district=district_obj,
                institution_type=institution_type_obj,
                raw_payload=raw_payload or {},
            )
            created = True
        else:
            created = False

        changed_fields: list[str] = []
        if not created:
            # Varsa: sadece boş/eksik veya null olan alanları güncelle
            if not inst.address and address:
                inst.address = address
                changed_fields.append("address")
            if not inst.phone and phone:
                inst.phone = phone
                changed_fields.append("phone")
            if inst.latitude is None and latitude is not None:
                inst.latitude = latitude
                changed_fields.append("latitude")
            if inst.longitude is None and longitude is not None:
                inst.longitude = longitude
                changed_fields.append("longitude")
            if not inst.province_id and province_obj:
                inst.province = province_obj
                changed_fields.append("province")
            if not inst.district_id and district_obj:
                inst.district = district_obj
                changed_fields.append("district")
            if not inst.institution_type_id and institution_type_obj:
                inst.institution_type = institution_type_obj
                changed_fields.append("institution_type")
            if raw_payload and not inst.raw_payload:
                inst.raw_payload = raw_payload
                changed_fields.append("raw_payload")
            if changed_fields:
                inst.save()

        return inst, created, changed_fields

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
    ) -> tuple[InstitutionContract, bool, list[str]]:
        """(company, product_type, external_id) üzerinden upsert.

        Returns (contract, created, changed_fields).
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
        changed_fields: list[str] = []
        if not created:
            update_fields = ["is_active", "last_seen_at", "last_scrape_job"]
            if not contract.is_active:
                changed_fields.append("is_active(reactivated)")
            contract.is_active = True
            contract.last_seen_at = timezone.now()
            contract.last_scrape_job = job
            if coverage_notes and not contract.coverage_notes:
                contract.coverage_notes = coverage_notes
                update_fields.append("coverage_notes")
                changed_fields.append("coverage_notes")
            if raw_payload and not contract.raw_payload:
                contract.raw_payload = raw_payload
                update_fields.append("raw_payload")
                changed_fields.append("raw_payload")
            if contract.institution_id != institution.pk:
                contract.institution = institution
                update_fields.append("institution")
                changed_fields.append("institution")
            contract.save(update_fields=update_fields)

        if policy_applications is not None:
            # .set() yerine .add() kullanarak, farklı ServiceId (PolicyApplication) taramalarında
            # gelen tüm uygulamaları ve networkleri kontrata ekliyoruz (biriktiriyoruz)
            existing_pa_ids = set(contract.policy_applications.values_list("pk", flat=True))
            new_pa = [pa for pa in policy_applications if pa.pk not in existing_pa_ids]
            contract.policy_applications.add(*policy_applications)
            if new_pa:
                changed_fields.append(
                    "policy_applications+=" + ",".join(pa.code for pa in new_pa)
                )

            derived_networks = [
                pa.network for pa in policy_applications if pa.network_id
            ]
            all_networks = list({n.pk: n for n in (derived_networks + (networks or []))}.values())
            if all_networks:
                existing_net_ids = set(contract.networks.values_list("pk", flat=True))
                new_networks = [n for n in all_networks if n.pk not in existing_net_ids]
                contract.networks.add(*all_networks)
                if new_networks:
                    changed_fields.append(
                        "networks+=" + ",".join(n.name for n in new_networks)
                    )
        elif networks is not None:
            existing_net_ids = set(contract.networks.values_list("pk", flat=True))
            new_networks = [n for n in networks if n.pk not in existing_net_ids]
            contract.networks.add(*networks)
            if new_networks:
                changed_fields.append(
                    "networks+=" + ",".join(n.name for n in new_networks)
                )

        return contract, created, changed_fields

    @staticmethod
    def _build_slug(name: str, province_name: str, district_name: str = "") -> str:
        """Çakışmaya karşı dayanıklı slug üretir."""
        base = slugify(f"{name}-{province_name}", allow_unicode=False)[:300]
        if not base:
            base = slugify(name, allow_unicode=False)[:300]

        if not HealthInstitution.objects.filter(slug=base).exists():
            return base

        # Eğer aynı slug ile kayıt varsa ve adı + ili aynıysa, çakışma değildir (aynı kurumdur)
        existing = HealthInstitution.objects.filter(slug=base).first()
        if existing and existing.name.strip().lower() == name.strip().lower():
            return base

        # Önce district ile genişlet (farklı bir kurumsa)
        if district_name:
            extended = slugify(f"{name}-{province_name}-{district_name}", allow_unicode=False)[:300]
            if not HealthInstitution.objects.filter(slug=extended).exists():
                return extended

        return base

    def _resolve_provinces(self, job: "ScrapeJob") -> list[Province]:
        """Job'un il filtresine göre il listesi döner."""
        if job.province_id:
            return [job.province]
        return list(Province.objects.filter(is_active=True).order_by("plate_code"))
