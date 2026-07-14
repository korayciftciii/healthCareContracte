from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import InsuranceCompany, Network
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

# Confirmed directly from GET /internal-api/networks?companyIds[]=..&productTypeId=..
# (canlı test edildi — hem 7 şirketimiz hem platformdaki diğer 12 şirket dahil tam
# 19 şirketlik listeyle çapraz kontrol edildi). ÖNEMLİ: aynı şirketin TSS ve ÖSS
# network id/isim setleri TAMAMEN farklı ve ortak id yok (örn. AXA TSS: 22/23/473,
# AXA ÖSS: 3814/3815/3816) — bu yüzden her satır (company_code, product_code) ile
# scope'lanıyor. MAPFRE'nin hiçbir network'ü yok (TSS/ÖSS ikisinde de boş dönüyor,
# platform genelinde doğrulandı) — bu bir hata değil, gerçek durum.
NETWORKS = [
    # --- TSS (productTypeId=1) ---
    {"company_code": "AXA", "product_code": "TSS", "external_id": 22, "name": "Sağlığım Tamam Nw."},
    {"company_code": "AXA", "product_code": "TSS", "external_id": 23, "name": "Sağlığım Tamam B Nw."},
    {"company_code": "AXA", "product_code": "TSS", "external_id": 473, "name": "AXA Sağlığım Tamam Tutumlu Sigortası"},
    {"company_code": "ALLIANZ", "product_code": "TSS", "external_id": 3860, "name": "Turkuaz Network"},
    {"company_code": "ALLIANZ", "product_code": "TSS", "external_id": 3861, "name": "Turuncu Network"},
    {"company_code": "ALLIANZ", "product_code": "TSS", "external_id": 3862, "name": "Kırmızı Network"},
    {"company_code": "ANADOLU", "product_code": "TSS", "external_id": 3708, "name": "Tamamlayıcı Network"},
    {"company_code": "ANADOLU", "product_code": "TSS", "external_id": 3709, "name": "Tamamlayıcı Eko Network"},
    {"company_code": "ACIBADEM", "product_code": "TSS", "external_id": 216, "name": "T1 Network"},
    {"company_code": "ACIBADEM", "product_code": "TSS", "external_id": 217, "name": "T2 Network"},
    {"company_code": "HDI", "product_code": "TSS", "external_id": 3817, "name": "T1 network"},
    {"company_code": "HDI", "product_code": "TSS", "external_id": 3818, "name": "T2 network"},
    {"company_code": "TURKIYE", "product_code": "TSS", "external_id": 3872, "name": "Altın Network"},
    {"company_code": "TURKIYE", "product_code": "TSS", "external_id": 3873, "name": "Platin Network"},
    {"company_code": "TURKIYE", "product_code": "TSS", "external_id": 3874, "name": "Bronz Network"},
    # MAPFRE / TSS: network yok.

    # --- ÖSS (productTypeId=3) ---
    {"company_code": "AXA", "product_code": "OSS", "external_id": 3814, "name": "Network 1"},
    {"company_code": "AXA", "product_code": "OSS", "external_id": 3815, "name": "Network 2"},
    {"company_code": "AXA", "product_code": "OSS", "external_id": 3816, "name": "Network 3"},
    {"company_code": "ALLIANZ", "product_code": "OSS", "external_id": 2, "name": "Yeşil Network"},
    {"company_code": "ALLIANZ", "product_code": "OSS", "external_id": 3, "name": "Sarı Network"},
    {"company_code": "ALLIANZ", "product_code": "OSS", "external_id": 4, "name": "Beyaz Network"},
    {"company_code": "ANADOLU", "product_code": "OSS", "external_id": 3482, "name": "Geniş Network"},
    {"company_code": "ANADOLU", "product_code": "OSS", "external_id": 3483, "name": "Eko Network"},
    {"company_code": "ANADOLU", "product_code": "OSS", "external_id": 3484, "name": "Tüm Network"},
    {"company_code": "ACIBADEM", "product_code": "OSS", "external_id": 106, "name": "A1 Network"},
    {"company_code": "ACIBADEM", "product_code": "OSS", "external_id": 107, "name": "A2 Network"},
    {"company_code": "ACIBADEM", "product_code": "OSS", "external_id": 108, "name": "A3 Network"},
    {"company_code": "ACIBADEM", "product_code": "OSS", "external_id": 109, "name": "A4 Network"},
    {"company_code": "ACIBADEM", "product_code": "OSS", "external_id": 110, "name": "A5 Network"},
    {"company_code": "ACIBADEM", "product_code": "OSS", "external_id": 111, "name": "A6 Network"},
    {"company_code": "HDI", "product_code": "OSS", "external_id": 330, "name": "A1 Network"},
    {"company_code": "HDI", "product_code": "OSS", "external_id": 331, "name": "A2 Network"},
    {"company_code": "HDI", "product_code": "OSS", "external_id": 332, "name": "A3 Network"},
    {"company_code": "HDI", "product_code": "OSS", "external_id": 333, "name": "A4 Network"},
    {"company_code": "HDI", "product_code": "OSS", "external_id": 334, "name": "A5 Network"},
    {"company_code": "TURKIYE", "product_code": "OSS", "external_id": 3875, "name": "A+ Network"},
    {"company_code": "TURKIYE", "product_code": "OSS", "external_id": 3876, "name": "A Network"},
    {"company_code": "TURKIYE", "product_code": "OSS", "external_id": 3877, "name": "B Network"},
    {"company_code": "TURKIYE", "product_code": "OSS", "external_id": 3878, "name": "C Network"},
    # MAPFRE / OSS: network yok.
]


class Command(BaseCommand):
    help = "Seeds reference data: 81 il, 7 sigorta şirketi, ürün tipleri, kurum tipleri, network'ler."

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

        companies_by_code = {c.code: c for c in InsuranceCompany.objects.all()}
        product_types_by_code = {p.code: p for p in ProductType.objects.all()}

        network_count = 0
        for data in NETWORKS:
            company = companies_by_code[data["company_code"]]
            product_type = product_types_by_code[data["product_code"]]
            _, created = Network.objects.update_or_create(
                company=company,
                product_type=product_type,
                external_id=data["external_id"],
                defaults={"name": data["name"]},
            )
            network_count += created

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed tamamlandı. Yeni: {city_count} il, {company_count} şirket, "
                f"{product_type_count} ürün tipi, {institution_type_count} kurum tipi, "
                f"{network_count} network (zaten var olanlar güncellendi/atlandı)."
            )
        )
