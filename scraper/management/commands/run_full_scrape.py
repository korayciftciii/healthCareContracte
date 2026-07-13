from django.core.management.base import BaseCommand, CommandError

from companies.models import InsuranceCompany
from geo.models import City, District
from products.models import InstitutionType, ProductType
from scraper.models import ScrapeJob
from scraper.services import ScrapeJobRunner


class Command(BaseCommand):
    help = (
        "Dashboard'a girmeden, CLI'dan (veya ileride cron/Task Scheduler'dan) bir "
        "ScrapeJob oluşturup çalıştırır. Tüm filtreler opsiyoneldir; boş bırakılan "
        "filtre 'hepsi' anlamına gelir (örn. --company verilmezse 7 şirketin hepsi "
        "taranır). Örnek: python manage.py run_full_scrape --city 34"
    )

    def add_arguments(self, parser):
        parser.add_argument("--company", help="Şirket kodu (örn. AXA). Boşsa: tüm şirketler.")
        parser.add_argument("--city", type=int, help="İl plaka kodu (örn. 34). Boşsa: tüm iller.")
        parser.add_argument("--district", help="İlçe adı (--city ile birlikte kullanılmalı).")
        parser.add_argument(
            "--product-type", help="Ürün kodu (TSS/OSS). Boşsa: tüm ürün tipleri."
        )
        parser.add_argument("--institution-type", help="Kurum tipi kodu. Boşsa: tüm tipler.")

    def handle(self, *args, **options):
        company = self._resolve(InsuranceCompany, code=options["company"])
        product_type = self._resolve(ProductType, code=options["product_type"])
        institution_type = self._resolve(InstitutionType, code=options["institution_type"])
        city = None
        district = None
        if options["city"]:
            city = self._resolve(City, plate_code=options["city"])
            if options["district"]:
                district = District.objects.filter(city=city, name__iexact=options["district"]).first()
                if not district:
                    raise CommandError(f"İlçe bulunamadı: {options['district']} ({city.name})")
        elif options["district"]:
            raise CommandError("--district kullanmak için --city de belirtmelisin.")

        job = ScrapeJob.objects.create(
            company=company,
            city=city,
            district=district,
            product_type=product_type,
            institution_type=institution_type,
        )
        self.stdout.write(f"ScrapeJob #{job.pk} oluşturuldu, çalıştırılıyor...")

        ScrapeJobRunner().run(job)
        job.refresh_from_db()

        self.stdout.write(job.log)
        style = self.style.SUCCESS if job.status == ScrapeJob.Status.SUCCESS else self.style.WARNING
        self.stdout.write(
            style(
                f"Bitti. status={job.status} pages={job.pages_fetched} "
                f"created={job.created_count} updated={job.updated_count}"
            )
        )
        if job.error_message:
            self.stdout.write(self.style.ERROR(f"error: {job.error_message}"))

    def _resolve(self, model, *, code=None, plate_code=None):
        if code:
            obj = model.objects.filter(code=code).first()
            if not obj:
                raise CommandError(f"{model.__name__} bulunamadı: code={code}")
            return obj
        if plate_code:
            obj = model.objects.filter(plate_code=plate_code).first()
            if not obj:
                raise CommandError(f"{model.__name__} bulunamadı: plate_code={plate_code}")
            return obj
        return None
