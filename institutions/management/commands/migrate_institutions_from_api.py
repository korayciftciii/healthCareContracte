import os
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from institutions.models import HealthInstitution
from products.models import InstitutionType
from geo.models import Province, District
from scraper.models import ScrapeJob


class Command(BaseCommand):
    help = (
        "Eski sistemden (sigortafi.net) API üzerinden kurumları çek ve HealthInstitution "
        "tablosunu doldur. Aynı fiziksel kurum, eski sistemde her sigorta şirketi/network "
        "kombinasyonu için ayrı kayıt olarak geldiğinden (bkz. company alanı), burada "
        "şirket/network bilgisi kullanılmaz — sadece il/ilçe/isim bazlı dublikeler "
        "birleştirilip TEK kurum kaydı olarak içeri alınır. Şirket-kurum ilişkileri "
        "(InstitutionContract, Network) ayrı scraper'lar tarafından doldurulacaktır."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--city-plate-code",
            type=int,
            help="Spesifik bir il için migrate et (1-81)",
        )

    def handle(self, *args, **options):
        token = os.getenv("API_TOKEN")
        if not token:
            self.stdout.write(self.style.ERROR("✗ API_TOKEN env'de tanımlanmadı"))
            return

        base_url = "https://api.sigortafi.net/api/v1/institutions"
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}

        plate_arg = options.get("city_plate_code")
        province_plate_codes = [f"{plate_arg:02d}"] if plate_arg else [f"{i:02d}" for i in range(1, 82)]

        job = ScrapeJob.objects.create(
            source_key="migration",
            status=ScrapeJob.Status.RUNNING,
            started_at=timezone.now(),
            request_params={
                "command": "migrate_institutions_from_api",
                "city_plate_code": plate_arg or "ALL (1-81)",
            },
        )
        self.job = job
        self.log(f"Migration başlatıldı. PID: {os.getpid()}. İller: {province_plate_codes}")

        total_created = 0
        total_updated = 0
        total_errors = 0
        total_duplicates_merged = 0

        for plate_code in province_plate_codes:
            try:
                province = Province.objects.get(plate_code=plate_code)
            except Province.DoesNotExist:
                self.log(f"⚠ İl bulunamadı: plate_code={plate_code}", "warning")
                continue

            self.log(f"📍 {province.name}: API'den çekiliyor...")
            results = self.fetch_all_pages(base_url, plate_code, headers, province.name)
            if results is None:
                total_errors += 1
                continue

            self.log(f"📍 {province.name}: {len(results)} kayıt bulundu (dublike dahil)")

            merged = self.merge_duplicates(results)
            duplicates_in_province = len(results) - len(merged)
            total_duplicates_merged += duplicates_in_province
            self.log(
                f"📍 {province.name}: {len(merged)} tekil kurum "
                f"({duplicates_in_province} dublike birleştirildi)"
            )

            province_created = 0
            province_updated = 0
            for inst_data in merged.values():
                try:
                    with transaction.atomic():
                        created = self.upsert_institution(province, inst_data)
                        if created:
                            total_created += 1
                            province_created += 1
                        else:
                            total_updated += 1
                            province_updated += 1
                except Exception as e:
                    self.log(f"✗ Kurum hatası: {inst_data.get('name')} - {str(e)}", "error")
                    total_errors += 1

            self.log(f"📍 {province.name}: {province_created} yeni, {province_updated} güncellendi")

            # Her il sonunda ilerlemeyi DB'ye yaz (canlı log dosyası zaten anlık yazılıyor)
            job.created_count = total_created
            job.updated_count = total_updated
            job.result_count = total_created + total_updated
            job.save(update_fields=["created_count", "updated_count", "result_count", "log"])

        self.log("=" * 60)
        self.log(f"✓ {total_created} yeni kurum, {total_updated} güncellenen kurum", "success")
        if total_duplicates_merged:
            self.log(f"ℹ {total_duplicates_merged} dublike kayıt tek kuruma birleştirildi", "notice")
        if total_errors:
            self.log(f"⚠ {total_errors} hata oluştu", "warning")

        job.created_count = total_created
        job.updated_count = total_updated
        job.result_count = total_created + total_updated
        job.error_message = f"{total_errors} hata oluştu" if total_errors else ""
        job.status = (
            ScrapeJob.Status.FAILED if total_errors and job.result_count == 0
            else ScrapeJob.Status.PARTIAL if total_errors
            else ScrapeJob.Status.SUCCESS
        )
        job.finished_at = timezone.now()
        job.save()

    def log(self, message, level=None):
        """Hem konsola hem ScrapeJob.log alanına + logs/MIGRATION/*.log dosyasına yazar.

        Dosyaya yazım anlıktır (append_log), bu sayede admin'deki
        'Canlı Log Takibi' (WebSocket) sekmesinden MIGRATION klasörü seçilip
        bu script'in loğu gerçek zamanlı izlenebilir.
        """
        style_map = {
            "error": self.style.ERROR,
            "warning": self.style.WARNING,
            "success": self.style.SUCCESS,
            "notice": self.style.NOTICE,
        }
        self.stdout.write(style_map.get(level, lambda x: x)(message))
        self.job.append_log(message)

    def fetch_all_pages(self, base_url, plate_code, headers, province_name):
        """API sayfalanmış (paginated) döner — 'next' bitene kadar tüm sayfaları toplar."""
        results = []
        url = f"{base_url}/?city__plate_code={int(plate_code)}"
        page = 1
        while url:
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as e:
                self.log(f"✗ API hatası ({province_name}, sayfa {page}): {str(e)}", "error")
                return None

            if isinstance(payload, dict):
                results.extend(payload.get("results", []))
                url = payload.get("next")
            elif isinstance(payload, list):
                results.extend(payload)
                url = None
            else:
                self.log(f"⚠ Beklenmeyen API formatı ({province_name})", "warning")
                url = None

            self.job.pages_fetched += 1
            page += 1

        return results

    @staticmethod
    def normalize(value):
        return (value or "").strip().casefold()

    def merge_duplicates(self, results):
        """Aynı fiziksel kurumun şirket bazlı tekrarlarını (isim + ilçe) tek kayda indirger.

        Eski sistemde aynı kurum, her sigorta şirketi/network kombinasyonu için ayrı
        satır olarak geliyor (örn. aynı hastane hem ACIBADEM hem ALLIANZ satırında).
        Bunlar aynı fiziksel kurumdur; şirket/network farkı bizim için önemli değil,
        sadece kurum alanlarını (adres/telefon/koordinat/tür) eksik olan yerlerde
        doldurmak için birleştiriyoruz.
        """
        merged = {}
        for row in results:
            name = (row.get("name") or "").strip()
            if not name:
                continue
            key = (self.normalize(name), self.normalize(row.get("district")))
            if key not in merged:
                merged[key] = dict(row)
                continue

            existing = merged[key]
            for field in ("address", "phone", "latitude", "longitude", "institution_type", "city", "district"):
                if not existing.get(field) and row.get(field):
                    existing[field] = row[field]

        return merged

    def upsert_institution(self, province, inst_data):
        inst_name = inst_data.get("name", "").strip()

        district_obj = None
        district_name = (inst_data.get("district") or "").strip()
        if district_name:
            district_obj = District.objects.filter(
                province=province, name__iexact=district_name,
            ).first()
            if district_obj is None:
                self.log(f"⚠ İlçe bulunamadı: {inst_name} - {district_name} ({province.name})", "warning")

        # Slug: name + il. Aynı isim+il ile farklı bir kurum zaten kayıtlıysa
        # (ör. aynı isimli iki farklı şube), ilçe eklenerek ayrıştırılır.
        base_slug = slugify(f"{inst_name}-{province.name}", allow_unicode=False)[:300]
        slug = base_slug
        existing = HealthInstitution.objects.filter(slug=base_slug).first()
        if existing and not (
            existing.name == inst_name
            and existing.province_id == province.id
            and existing.district_id == (district_obj.id if district_obj else None)
        ):
            extended = slugify(
                f"{inst_name}-{province.name}-{district_obj.name if district_obj else ''}",
                allow_unicode=False,
            )
            slug = extended[:300]

        institution_type = None
        type_code = inst_data.get("institution_type")
        if type_code:
            institution_type = InstitutionType.objects.filter(code=type_code).first()
            if institution_type is None:
                self.log(f"⚠ InstitutionType bulunamadı: {type_code}", "warning")

        _, created = HealthInstitution.objects.update_or_create(
            slug=slug,
            defaults={
                "name": inst_name,
                "province": province,
                "district": district_obj,
                "address": inst_data.get("address") or "",
                "phone": inst_data.get("phone") or "",
                "latitude": inst_data.get("latitude"),
                "longitude": inst_data.get("longitude"),
                "institution_type": institution_type,
                "is_active": inst_data.get("is_active", True),
                "raw_payload": inst_data,
            },
        )
        return created
