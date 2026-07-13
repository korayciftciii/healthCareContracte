import time

from django.core.management.base import BaseCommand

from geo.models import City, District
from scraper.client import TamamlayiciSaglikClient
from scraper.exceptions import ScraperError


class Command(BaseCommand):
    help = (
        "Tüm iller için GET /internal-api/districts?cityId=... çağrısı yapıp "
        "District tablosunu gerçek ilçe id/isimleriyle doldurur. "
        "Ağ üzerinden çalışır, 81 istek atar (--delay ile hız ayarlanabilir)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delay", type=float, default=0.3, help="İstekler arası bekleme (saniye)."
        )

    def handle(self, *args, **options):
        client = TamamlayiciSaglikClient()
        delay = options["delay"]
        total_created = 0
        total_updated = 0

        cities = City.objects.exclude(external_id__isnull=True).order_by("plate_code")
        for city in cities:
            try:
                districts = client.get_districts(city_id=city.external_id)
            except ScraperError as exc:
                self.stderr.write(self.style.ERROR(f"{city.name}: {exc}"))
                continue

            for item in districts:
                _, created = District.objects.update_or_create(
                    city=city,
                    name=item["name"],
                    defaults={"external_id": item["id"]},
                )
                if created:
                    total_created += 1
                else:
                    total_updated += 1

            self.stdout.write(f"{city.name}: {len(districts)} ilçe işlendi.")
            time.sleep(delay)

        self.stdout.write(
            self.style.SUCCESS(
                f"Tamamlandı. Yeni: {total_created}, güncellenen: {total_updated} ilçe."
            )
        )
