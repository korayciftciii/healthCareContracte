import json
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from geo.models import Province, District


TURKISH_PROVINCES = [
    ("01", "Adana"), ("02", "Adıyaman"), ("03", "Afyonkarahisar"), ("04", "Ağrı"), ("05", "Amasya"),
    ("06", "Ankara"), ("07", "Antalya"), ("08", "Artvin"), ("09", "Aydın"), ("10", "Balıkesir"),
    ("11", "Bilecik"), ("12", "Bingöl"), ("13", "Bitlis"), ("14", "Bolu"), ("15", "Burdur"),
    ("16", "Bursa"), ("17", "Çanakkale"), ("18", "Çankırı"), ("19", "Çorum"), ("20", "Denizli"),
    ("21", "Diyarbakır"), ("22", "Edirne"), ("23", "Elazığ"), ("24", "Erzincan"), ("25", "Erzurum"),
    ("26", "Eskişehir"), ("27", "Gaziantep"), ("28", "Giresun"), ("29", "Gümüşhane"), ("30", "Hakkari"),
    ("31", "Hatay"), ("32", "Isparta"), ("33", "Mersin"), ("34", "İstanbul"), ("35", "İzmir"),
    ("36", "Kars"), ("37", "Kastamonu"), ("38", "Kayseri"), ("39", "Kırklareli"), ("40", "Kırşehir"),
    ("41", "Kocaeli"), ("42", "Konya"), ("43", "Kütahya"), ("44", "Malatya"), ("45", "Manisa"),
    ("46", "Kahramanmaraş"), ("47", "Mardin"), ("48", "Muğla"), ("49", "Muş"), ("50", "Nevşehir"),
    ("51", "Niğde"), ("52", "Ordu"), ("53", "Rize"), ("54", "Sakarya"), ("55", "Samsun"),
    ("56", "Siirt"), ("57", "Sinop"), ("58", "Sivas"), ("59", "Tekirdağ"), ("60", "Tokat"),
    ("61", "Trabzon"), ("62", "Tunceli"), ("63", "Şanlıurfa"), ("64", "Uşak"), ("65", "Van"),
    ("66", "Yozgat"), ("67", "Zonguldak"), ("68", "Aksaray"), ("69", "Bayburt"), ("70", "Karaman"),
    ("71", "Kırıkkale"), ("72", "Batman"), ("73", "Şırnak"), ("74", "Bartın"), ("75", "Ardahan"),
    ("76", "Iğdır"), ("77", "Yalova"), ("78", "Karabük"), ("79", "Kilis"), ("80", "Osmaniye"),
    ("81", "Düzce"),
]


class Command(BaseCommand):
    help = "Seed 81 il ve tüm ilçeleri JSON dosyasından."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. İller (Provinces)
        province_count = 0
        for plate_code, name in TURKISH_PROVINCES:
            Province.objects.update_or_create(
                plate_code=plate_code, defaults={"name": name, "is_active": True}
            )
            province_count += 1

        self.stdout.write(self.style.SUCCESS(f"✓ {province_count} il seed edildi"))

        # 2. İlçeler - JSON dosyasından
        districts_file = Path(__file__).resolve().parent.parent.parent.parent / "districts.json"

        if not districts_file.exists():
            self.stdout.write(self.style.ERROR(f"✗ districts.json dosyası bulunamadı: {districts_file}"))
            return

        with open(districts_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        districts_data = data.get("districts", [])
        district_count = 0
        error_count = 0

        for district_info in districts_data:
            try:
                province_plate_code = str(district_info.get("province_id")).zfill(2)
                name = district_info.get("name", "").strip()

                if not name or not province_plate_code:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ Eksik veri - İlçe: {name}, İl plate_code: {province_plate_code}"
                        )
                    )
                    error_count += 1
                    continue

                try:
                    province = Province.objects.get(plate_code=province_plate_code)
                except Province.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠ İl bulunamadı - İl plate_code: {province_plate_code}, İlçe: {name}"
                        )
                    )
                    error_count += 1
                    continue

                District.objects.update_or_create(
                    province=province,
                    name=name,
                    defaults={"is_active": True}
                )
                district_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Hata - {district_info.get('name')}: {str(e)}")
                )
                error_count += 1

        self.stdout.write(self.style.SUCCESS(f"✓ {district_count} ilçe seed edildi"))
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f"⚠ {error_count} ilçe hata ile atlandı"))
