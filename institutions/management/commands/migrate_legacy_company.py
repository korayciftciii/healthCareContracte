import os

import requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from companies.models import InsuranceCompany, Network
from products.models import ProductType
from scraper.models import ScrapeJob
from scraper.sources.base import BaseScraper


# Eski API'de AXA TSS network isimleri "Sağlığım Tamam Nw." ve "Sağlığım Tamam B Nw."
# olarak geliyor; ikisi de neredeyse aynı kurum kümesini kapsıyor ve bizdeki
# "Sağlığım Tamam Sigortası" (17) ile "Grup Sağlığım Tamam Sigortası" (81) network'lerinin
# ikisine birden karşılık geliyor — bu yüzden gelen kurumlar her iki network'e de eklenir.
LEGACY_NETWORK_NAME_ALIASES = {
    "AXA": {
        "Sağlığım Tamam Nw.": ["Sağlığım Tamam Sigortası", "Grup Sağlığım Tamam Sigortası"],
        "Sağlığım Tamam B Nw.": ["Sağlığım Tamam Sigortası", "Grup Sağlığım Tamam Sigortası"],
    },
    # Eski API'de HDI ÖSS network'leri "A1 Network".."A4 Network" (id 330-333) olarak
    # geliyor; bizdeki seed_company_data.py'de aynı network'ler "Size Özel Sağlık A1".."A4"
    # (external_id 385/397/400/401) adıyla kayıtlı — isim eşlemesi burada yapılır.
    "HDI": {
        "A1 Network": ["Size Özel Sağlık A1"],
        "A2 Network": ["Size Özel Sağlık A2"],
        "A3 Network": ["Size Özel Sağlık A3"],
        "A4 Network": ["Size Özel Sağlık A4"],
    },
}


class _LegacyImporter(BaseScraper):
    """BaseScraper'ın ortak _upsert_institution/_upsert_contract metodlarını
    kullanmak için tanımlanmış boş kabuk. run() bu komutta kullanılmaz."""

    source_key = "migration"

    def run(self, job: ScrapeJob) -> None:  # pragma: no cover - kullanılmıyor
        raise NotImplementedError


class Command(BaseCommand):
    help = (
        "Eski sistemin (api.sigortafi.net) REST API'sinden, belirtilen sigorta şirketi "
        "için anlaşmalı kurum listesini çeker; HealthInstitution + InstitutionContract "
        "olarak (kurum tipi/il/ilçe/network eşleştirmeleriyle) mevcut sisteme seed eder.\n\n"
        "Eski API'de bir satır zaten (kurum, şirket, ürün tipi) kombinasyonuna karşılık "
        "gelir ve o kombinasyonun tüm network'lerini embedded olarak içerir — bu yüzden "
        "burada AXA/HDI gibi ServiceId bazlı tarama yapılmaz, doğrudan networks listesi "
        "isimden bizim companies.Network tablosuna eşlenir."
    )

    BASE_URL = "https://api.sigortafi.net/api/v1/institutions/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-code",
            default="ACIBADEM",
            help="Eski API'deki company__code filtresi (varsayılan: ACIBADEM).",
        )
        parser.add_argument(
            "--page-size",
            type=int,
            default=200,
            help="Eski API sayfalama boyutu (varsayılan: 200).",
        )
        parser.add_argument(
            "--city-plate-code",
            type=int,
            help="Sadece belirli bir il için çek (test amaçlı, opsiyonel).",
        )

    def handle(self, *args, **options):
        token = os.getenv("API_TOKEN")
        if not token:
            raise CommandError("API_TOKEN env'de tanımlanmadı")

        company_code = options["company_code"].upper()
        page_size = options["page_size"]
        plate_code = options.get("city_plate_code")

        try:
            company = InsuranceCompany.objects.get(code=company_code)
        except InsuranceCompany.DoesNotExist as exc:
            raise CommandError(
                f"InsuranceCompany bulunamadı: code={company_code}. "
                f"Önce 'python manage.py seed_company_data' çalıştırılmalı."
            ) from exc

        job = ScrapeJob.objects.create(
            source_key="migration",
            company=company,
            status=ScrapeJob.Status.RUNNING,
            started_at=timezone.now(),
            request_params={
                "command": "migrate_legacy_company",
                "company_code": company_code,
                "city_plate_code": plate_code or "ALL",
            },
        )
        self.job = job
        self.importer = _LegacyImporter()
        self.log(f"Migration başlatıldı ({company_code}). PID: {os.getpid()}.")

        headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}
        params = {"company__code": company_code, "page_size": page_size}
        if plate_code:
            params["city__plate_code"] = plate_code

        created = updated = errors = network_misses = 0

        try:
            for row in self.fetch_all_pages(headers, params):
                try:
                    with transaction.atomic():
                        row_created = self.upsert_row(company, row)
                        if row_created:
                            created += 1
                        else:
                            updated += 1
                except Network.DoesNotExist:
                    network_misses += 1
                except Exception as e:
                    errors += 1
                    self.log(f"✗ Kurum hatası: {row.get('name')} (id={row.get('id')}) - {e}", "error")

            job.status = (
                ScrapeJob.Status.FAILED if errors and (created + updated) == 0
                else ScrapeJob.Status.PARTIAL if errors
                else ScrapeJob.Status.SUCCESS
            )
        except Exception as exc:
            job.status = ScrapeJob.Status.FAILED
            job.error_message = str(exc)
            self.log(f"Beklenmeyen hata: {exc}", "error")
        finally:
            job.created_count = created
            job.updated_count = updated
            job.result_count = created + updated
            if errors:
                job.error_message = f"{errors} kurum hatası oluştu"
            job.finished_at = timezone.now()
            job.save()

        self.log("=" * 60)
        self.log(f"✓ {created} yeni kontrat, {updated} güncellenen kontrat", "success")
        if network_misses:
            self.log(f"⚠ {network_misses} kurum, eşleşmeyen network yüzünden atlandı", "warning")
        if errors:
            self.log(f"⚠ {errors} hata oluştu", "warning")

    def log(self, message, level=None):
        style_map = {
            "error": self.style.ERROR,
            "warning": self.style.WARNING,
            "success": self.style.SUCCESS,
            "notice": self.style.NOTICE,
        }
        self.stdout.write(style_map.get(level, lambda x: x)(message))
        self.job.append_log(message)

    def fetch_all_pages(self, headers, params):
        """Eski API sayfalanmış döner ('next' bitene kadar tüm sayfaları toplar)."""
        url = self.BASE_URL
        request_params = params
        page = 1
        total = None
        while url:
            try:
                response = requests.get(url, headers=headers, params=request_params, timeout=20)
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as e:
                self.log(f"✗ API hatası (sayfa {page}): {e}", "error")
                return

            if total is None:
                total = payload.get("count")
                self.log(f"Toplam {total} kayıt bulundu.")

            for row in payload.get("results", []):
                yield row

            url = payload.get("next")
            request_params = None  # 'next' linki zaten tüm query param'ları içeriyor
            self.job.pages_fetched += 1
            page += 1
            if page % 10 == 0:
                self.job.save(update_fields=["pages_fetched"])

    def upsert_row(self, company: InsuranceCompany, row: dict) -> bool:
        name = (row.get("name") or "").strip()
        if not name:
            raise ValueError("kurum adı boş")

        product_type_code = row.get("product_type")
        product_type = ProductType.objects.filter(code=product_type_code).first()
        if product_type is None:
            raise ValueError(f"ProductType bulunamadı: {product_type_code}")

        province_name = row.get("city") or ""
        district_name = row.get("district") or ""
        institution_type_code = row.get("institution_type") or ""

        lat = row.get("latitude")
        lng = row.get("longitude")
        latitude = float(lat) if lat not in (None, "") else None
        longitude = float(lng) if lng not in (None, "") else None

        # 1. Saf kurum upsert (global dedup) — BaseScraper'ın ortak mantığı
        inst, inst_created, inst_changed = self.importer._upsert_institution(
            name=name,
            province_name=province_name,
            district_name=district_name,
            institution_type_code=institution_type_code,
            address=row.get("address") or "",
            phone=row.get("phone") or "",
            latitude=latitude,
            longitude=longitude,
            raw_payload=row,
        )
        if inst_created:
            self.job.append_log(
                f"  + Yeni kurum: '{inst.name}' (il={province_name or '-'}, ilçe={district_name or '-'})"
            )
        elif inst_changed:
            self.job.append_log(f"  ~ Kurum güncellendi: '{inst.name}' — {', '.join(inst_changed)}")

        # 2. Network eşleştirmesi — eski API'nin embedded 'networks' listesindeki
        # her isim, companies.Network tablosunda (company, product_type, name) ile aranır.
        # Bazı şirketlerde eski isim bizdeki kanonik isimden farklı olabiliyor (veya
        # birden fazla kanonik network'e karşılık gelebiliyor) — bu durumda
        # LEGACY_NETWORK_NAME_ALIASES üzerinden eşlenir. Bulunamayan network varsa
        # (henüz seed edilmemiş) o kurum atlanır ki sessizce eksik network'le kontrat
        # oluşmasın.
        aliases = LEGACY_NETWORK_NAME_ALIASES.get(company.code, {})
        networks = []
        seen_network_ids = set()
        for net in row.get("networks") or []:
            net_product_type = ProductType.objects.filter(code=net.get("product_type")).first()
            if net_product_type is None:
                continue
            for target_name in aliases.get(net.get("name"), [net.get("name")]):
                network = Network.objects.filter(
                    company=company, product_type=net_product_type, name=target_name,
                ).first()
                if network is None:
                    self.job.append_log(
                        f"  ⚠ Network bulunamadı: {company.code}/{net.get('product_type')} - "
                        f"'{target_name}' (kurum: {inst.name}) — seed_company_data.py'ye eklenmeli."
                    )
                    continue
                if network.id not in seen_network_ids:
                    seen_network_ids.add(network.id)
                    networks.append(network)

        # 3. Kurum anlaşması upsert — eski API'nin external_id'si (kaynak sitedeki
        # fiziksel kurum ID'si), (company, product_type) ile birlikte unique.
        external_id = str(row.get("external_id") or row.get("id"))
        contract, created, contract_changed = self.importer._upsert_contract(
            institution=inst,
            company=company,
            product_type=product_type,
            external_id=external_id,
            job=self.job,
            networks=networks,
            raw_payload=row,
        )
        if created:
            self.job.append_log(
                f"  + Yeni kontrat: '{inst.name}' <-> {company.code}/{product_type.code} "
                f"(external_id={external_id}, networks={[n.name for n in networks]})"
            )
        elif contract_changed:
            self.job.append_log(
                f"  ~ Kontrat güncellendi: '{inst.name}' <-> {company.code}/{product_type.code} "
                f"— {', '.join(contract_changed)}"
            )

        return created
