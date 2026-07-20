import os
import requests
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify
from institutions.models import HealthInstitution, InstitutionContract
from products.models import ProductType, InstitutionType
from companies.models import InsuranceCompany, Network
from geo.models import Province, District


class Command(BaseCommand):
    help = "Mevcut sistemden API üzerinden kurumları çek ve yeni DB'ye migrate et"

    def add_arguments(self, parser):
        parser.add_argument(
            "--city-plate-code",
            type=int,
            help="Spesifik bir şehir için migrate et (1-81)",
        )

    def handle(self, *args, **options):
        token = os.getenv("API_TOKEN")
        if not token:
            self.stdout.write(self.style.ERROR("✗ NEXTJS_MASTER_TOKEN env'de tanımlanmadı"))
            return

        base_url = "https://api.sigortafi.net/api/v1/institutions"
        headers = {"Authorization": f"Bearer {token}", "accept": "application/json"}

        total_migrated = 0
        total_errors = 0
        duplicates_handled = 0

        # İlleri seç
        province_plate_codes = [f"{i:02d}" for i in range(1, 82)]
        if options.get("city_plate_code"):
            province_plate_codes = [f"{options['city_plate_code']:02d}"]

        for plate_code in province_plate_codes:
            try:
                province = Province.objects.get(plate_code=plate_code)
            except Province.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"⚠ İl bulunamadı: plate_code={plate_code}"))
                continue

            # API'den kurumları çek (API hala city__plate_code kullanıyor)
            url = f"{base_url}/?city__plate_code={int(plate_code)}"
            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                self.stdout.write(self.style.ERROR(f"✗ API hatası ({province.name}): {str(e)}"))
                total_errors += 1
                continue

            try:
                api_response = response.json()
            except ValueError:
                self.stdout.write(self.style.ERROR(f"✗ API JSON decode hatası ({province.name})"))
                total_errors += 1
                continue

            # Sonuçları çıkar (paginated veya direkt liste)
            if isinstance(api_response, dict):
                results = api_response.get("results", [])
            elif isinstance(api_response, list):
                results = api_response
            else:
                self.stdout.write(self.style.WARNING(f"⚠ Beklenmeyen API format ({province.name})"))
                continue

            self.stdout.write(f"📍 {province.name}: {len(results)} kurum bulundu")

            for inst_data in results:
                try:
                    with transaction.atomic():
                        # İl ve ilçeyi eşleştir
                        province_obj = province
                        district_obj = None

                        if inst_data.get("district"):
                            try:
                                district_obj = District.objects.get(
                                    province=province_obj,
                                    name__iexact=inst_data["district"].strip(),
                                )
                            except District.DoesNotExist:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"⚠ İlçe bulunamadı: {inst_data.get('name')} - {inst_data['district']}"
                                    )
                                )

                        # Slug oluştur (deduplicate_institutions.py mantığı)
                        inst_name = inst_data.get("name", "").strip()
                        province_name = province_obj.name
                        district_name = district_obj.name if district_obj else ""

                        # Base slug
                        slug = slugify(f"{inst_name}-{province_name}", allow_unicode=False)
                        if len(slug) > 300:
                            slug = slug[:300]

                        # Duplicate slug kontrol (aynı ad+il+ilçe ama farklı kurum varsa)
                        existing_by_slug = HealthInstitution.objects.filter(slug=slug).first()
                        if existing_by_slug:
                            if (
                                existing_by_slug.name == inst_name
                                and existing_by_slug.province_id == province_obj.id
                                and existing_by_slug.district_id == (district_obj.id if district_obj else None)
                            ):
                                # Aynı kurum, güncelle
                                pass
                            else:
                                # Farklı kurum, ilçe ile disambiguate
                                extended_slug = slugify(
                                    f"{inst_name}-{province_name}-{district_name}", allow_unicode=False
                                )
                                if len(extended_slug) > 300:
                                    extended_slug = extended_slug[:300]
                                slug = extended_slug
                                duplicates_handled += 1

                        # InstitutionType bul veya oluştur
                        institution_type_code = inst_data.get("institution_type", "UNKNOWN")
                        try:
                            institution_type = InstitutionType.objects.get(code=institution_type_code)
                        except InstitutionType.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"⚠ InstitutionType bulunamadı: {institution_type_code}")
                            )
                            institution_type = None

                        # HealthInstitution oluştur/güncelle
                        health_inst, created = HealthInstitution.objects.update_or_create(
                            slug=slug,
                            defaults={
                                "name": inst_name,
                                "province": province_obj,
                                "district": district_obj,
                                "address": inst_data.get("address", ""),
                                "phone": inst_data.get("phone", ""),
                                "latitude": inst_data.get("latitude"),
                                "longitude": inst_data.get("longitude"),
                                "institution_type": institution_type,
                                "is_active": inst_data.get("is_active", True),
                                "raw_payload": inst_data,
                            },
                        )

                        # Company ve ProductType bul
                        company_code = inst_data.get("company")
                        product_type_code = inst_data.get("product_type")

                        try:
                            company = InsuranceCompany.objects.get(code=company_code)
                        except InsuranceCompany.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"⚠ Şirket bulunamadı: {company_code}")
                            )
                            total_errors += 1
                            continue

                        try:
                            product_type = ProductType.objects.get(code=product_type_code)
                        except ProductType.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(f"⚠ Ürün tipi bulunamadı: {product_type_code}")
                            )
                            total_errors += 1
                            continue

                        # InstitutionContract oluştur/güncelle
                        external_id = str(inst_data.get("external_id", ""))
                        contract, _ = InstitutionContract.objects.update_or_create(
                            institution=health_inst,
                            company=company,
                            product_type=product_type,
                            external_id=external_id,
                            defaults={
                                "is_active": inst_data.get("is_active", True),
                                "last_seen_at": inst_data.get("last_seen_at"),
                                "raw_payload": inst_data,
                            },
                        )

                        # Networks ekle/güncelle
                        for network_data in inst_data.get("networks", []):
                            try:
                                network = Network.objects.get(id=network_data["id"])
                                contract.networks.add(network)
                            except Network.DoesNotExist:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"⚠ Network bulunamadı: {network_data.get('id')} ({network_data.get('name')})"
                                    )
                                )

                        total_migrated += 1

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"✗ Kurum hatası: {inst_data.get('name')} - {str(e)}"))
                    total_errors += 1

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"✓ Toplam {total_migrated} kurum migrate edildi"))
        if duplicates_handled > 0:
            self.stdout.write(self.style.NOTICE(f"ℹ {duplicates_handled} duplicate slug'u ilçe ile disambiguate edildi"))
        if total_errors > 0:
            self.stdout.write(self.style.WARNING(f"⚠ {total_errors} hata oluştu"))
