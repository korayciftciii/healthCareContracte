from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import InsuranceCompany
from geo.models import City
from products.models import InstitutionType, ProductType

TURKISH_CITIES = [
    (1, "Adana"), (2, "Adıyaman"), (3, "Afyonkarahisar"), (4, "Ağrı"), (5, "Amasya"),
    (6, "Ankara"), (7, "Antalya"), (8, "Artvin"), (9, "Aydın"), (10, "Balıkesir"),
    (11, "Bilecik"), (12, "Bingöl"), (13, "Bitlis"), (14, "Bolu"), (15, "Burdur"),
    (16, "Bursa"), (17, "Çanakkale"), (18, "Çankırı"), (19, "Çorum"), (20, "Denizli"),
    (21, "Diyarbakır"), (22, "Edirne"), (23, "Elazığ"), (24, "Erzincan"), (25, "Erzurum"),
    (26, "Eskişehir"), (27, "Gaziantep"), (28, "Giresun"), (29, "Gümüşhane"), (30, "Hakkari"),
    (31, "Hatay"), (32, "Isparta"), (33, "Mersin"), (34, "İstanbul"), (35, "İzmir"),
    (36, "Kars"), (37, "Kastamonu"), (38, "Kayseri"), (39, "Kırklareli"), (40, "Kırşehir"),
    (41, "Kocaeli"), (42, "Konya"), (43, "Kütahya"), (44, "Malatya"), (45, "Manisa"),
    (46, "Kahramanmaraş"), (47, "Mardin"), (48, "Muğla"), (49, "Muş"), (50, "Nevşehir"),
    (51, "Niğde"), (52, "Ordu"), (53, "Rize"), (54, "Sakarya"), (55, "Samsun"),
    (56, "Siirt"), (57, "Sinop"), (58, "Sivas"), (59, "Tekirdağ"), (60, "Tokat"),
    (61, "Trabzon"), (62, "Tunceli"), (63, "Şanlıurfa"), (64, "Uşak"), (65, "Van"),
    (66, "Yozgat"), (67, "Zonguldak"), (68, "Aksaray"), (69, "Bayburt"), (70, "Karaman"),
    (71, "Kırıkkale"), (72, "Batman"), (73, "Şırnak"), (74, "Bartın"), (75, "Ardahan"),
    (76, "Iğdır"), (77, "Yalova"), (78, "Karabük"), (79, "Kilis"), (80, "Osmaniye"),
    (81, "Düzce"),
]

# external_id: tamamlayicisaglik.com company id, resolved directly from
# /internal-api/company-list-results — see plan.md.
INSURANCE_COMPANIES = [
    {"code": "AXA", "name": "AXA", "slug": "axa-sigorta", "external_id": 6},
    {"code": "HDI", "name": "HDI", "slug": "hdi-sigorta", "external_id": 17},
    {"code": "ACIBADEM", "name": "Acıbadem", "slug": "acibadem-sigorta", "external_id": 15},
    {"code": "TURKIYE", "name": "Türkiye", "slug": "turkiye-sigorta", "external_id": 32},
    {"code": "ANADOLU", "name": "Anadolu", "slug": "anadolu-sigorta", "external_id": 7},
    {"code": "ALLIANZ", "name": "Allianz", "slug": "allianz-sigorta", "external_id": 8},
    {"code": "MAPFRE", "name": "Mapfre", "slug": "mapfre-sigorta", "external_id": 3},
]

# Both confirmed against /internal-api/search-hospital directly (AXA/İstanbul):
# productTypeId=1 -> 189 sonuç (TSS), productTypeId=3 -> 563 sonuç (ÖSS, daha
# geniş network — beklenen oranla tutarlı).
PRODUCT_TYPES = [
    {"code": "TSS", "name": "Tamamlayıcı Sağlık Sigortası", "external_id": 1},
    {"code": "OSS", "name": "Özel Sağlık Sigortası", "external_id": 3},
]

# Confirmed directly from GET /internal-api/hospital-types (live, no auth needed).
INSTITUTION_TYPES = [
    {"code": "HASTANE", "name": "Hastane", "external_id": 1},
    {"code": "FIZIK_TEDAVI", "name": "Fizik Tedavi Merkezi", "external_id": 2},
    {"code": "DOKTOR", "name": "Doktor", "external_id": 6},
    {"code": "TIP_MERKEZI", "name": "Tıp Merkezi & Poliklinik", "external_id": 4},
    {"code": "DIS", "name": "Diş Hekimi & Kliniği", "external_id": 7},
    {"code": "TANI_GORUNTULEME", "name": "Tanı & Görüntüleme Merkezi", "external_id": 8},
    {"code": "EVDE_BAKIM", "name": "Evde Bakım", "external_id": 10},
    {"code": "OPTIK", "name": "Optik", "external_id": 11},
    {"code": "MEDIKAL", "name": "Medikal ve Tıbbi Malzeme", "external_id": 12},
]


class Command(BaseCommand):
    help = "Seeds reference data: 81 il, 7 sigorta şirketi, ürün tipleri, kurum tipleri."

    @transaction.atomic
    def handle(self, *args, **options):
        city_count = 0
        for plate_code, name in TURKISH_CITIES:
            # external_id == plate_code confirmed via GET /internal-api/cities
            # (İstanbul id=34 etc. match official plate codes exactly).
            _, created = City.objects.update_or_create(
                plate_code=plate_code, defaults={"name": name, "external_id": plate_code}
            )
            city_count += created

        company_count = 0
        for data in INSURANCE_COMPANIES:
            _, created = InsuranceCompany.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "slug": data["slug"],
                    "external_id": data["external_id"],
                },
            )
            company_count += created

        product_type_count = 0
        for data in PRODUCT_TYPES:
            _, created = ProductType.objects.update_or_create(
                code=data["code"],
                defaults={"name": data["name"], "external_id": data["external_id"]},
            )
            product_type_count += created

        institution_type_count = 0
        for data in INSTITUTION_TYPES:
            _, created = InstitutionType.objects.update_or_create(
                code=data["code"],
                defaults={"name": data["name"], "external_id": data["external_id"]},
            )
            institution_type_count += created

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed tamamlandı. Yeni: {city_count} il, {company_count} şirket, "
                f"{product_type_count} ürün tipi, {institution_type_count} kurum tipi "
                f"(zaten var olanlar güncellendi/atlandı)."
            )
        )
