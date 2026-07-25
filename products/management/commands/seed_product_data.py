from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import InsuranceCompany, Network, PolicyApplication
from products.models import ProductType, InstitutionType
PRODUCT_TYPES = [
    {"code": "TSS", "name": "Tamamlayıcı Sağlık Sigortası"},
    {"code": "OSS", "name": "Özel Sağlık Sigortası"},
]

INSTITUTION_TYPES = [
    {"code": "HASTANE", "name": "Hastane"},
    {"code": "FIZIK_TEDAVI", "name": "Fizik Tedavi Merkezi"},
    {"code": "DOKTOR", "name": "Doktor"},
    {"code": "TIP_MERKEZI", "name": "Tıp Merkezi & Poliklinik"},
    {"code": "DIS", "name": "Diş Hekimi & Kliniği"},
    {"code": "TANI_GORUNTULEME", "name": "Tanı & Görüntüleme Merkezi"},
    {"code": "EVDE_BAKIM", "name": "Evde Bakım"},
    {"code": "OPTIK", "name": "Optik"},
    {"code": "MEDIKAL", "name": "Medikal ve Tıbbi Malzeme"},
    {"code": "BAKIM_EVI", "name": "Bakım Evi"},
    {"code": "LABORATUAR", "name": "Laboratuvar"},
    {"code": "ASISTANS", "name": "Asistans"},
    {"code": "ECZANE", "name": "Eczane"},
    {"code": "AMBULANS", "name": "Ambulans"},
    {"code": "DIGER", "name": "Diğer"},
]

class Command(BaseCommand):
    @transaction.atomic
    def handle(self, *args, **options):
        # 2. Ürün Tipleri
        for data in PRODUCT_TYPES:
            ProductType.objects.update_or_create(
                code=data["code"], defaults={"name": data["name"]}
            )

        # 3. Kurum Tipleri
        for data in INSTITUTION_TYPES:
            InstitutionType.objects.update_or_create(
                code=data["code"], defaults={"name": data["name"]}
            )
        tss_type = ProductType.objects.get(code="TSS")
        oss_type = ProductType.objects.get(code="OSS")

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed başarıyla tamamlandı!\n"
            )
        )
