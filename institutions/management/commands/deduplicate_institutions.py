from collections import defaultdict
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from institutions.models import HealthInstitution, InstitutionContract


class Command(BaseCommand):
    help = "Veritabanındaki mükerrer (duplicate) sağlık kurumlarını ad, şehir ve ilçe bazında tespit eder ve tek kayıt altında birleştirir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Veritabanında değişiklik yapmadan sadece tespit edilen mükerrer kayıtları ve yapılacak işlemleri listeler.",
        )
        parser.add_argument(
            "--ignore-district",
            action="store_true",
            help="İlçe farklı/biri null olsa bile aynı ad ve şehirdeki tüm kurumları birleştirir.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        ignore_district = options["ignore_district"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY-RUN MODU: Veritabanı üzerinde değişiklik yapılmayacaktır ---"))

        institutions = HealthInstitution.objects.select_related("city", "district", "institution_type").all()
        self.stdout.write(f"Toplam {institutions.count()} sağlık kurumu inceleniyor...")

        # Kurumları grupla
        # Grup anahtarı: (normalize_name, city_id, district_id) veya ignore_district ise (normalize_name, city_id)
        groups = defaultdict(list)
        for inst in institutions:
            norm_name = " ".join(inst.name.strip().lower().split())
            city_id = inst.city_id or 0
            district_id = 0 if ignore_district else (inst.district_id or 0)
            groups[(norm_name, city_id, district_id)].append(inst)

        duplicate_groups = {k: v for k, v in groups.items() if len(v) > 1}
        self.stdout.write(self.style.NOTICE(f"Tespit edilen mükerrer (duplicate) kurum grubu sayısı: {len(duplicate_groups)}"))

        total_merged_institutions = 0
        total_reassigned_contracts = 0
        total_merged_contracts = 0

        for key, inst_list in duplicate_groups.items():
            norm_name, city_id, district_id = key
            # En iyi (canonical) kurumu seç: En çok kontratı olan veya en eski yaratılan
            inst_list.sort(key=lambda x: (x.contracts.count(), -x.pk if x.pk else 0), reverse=True)
            primary = inst_list[0]
            duplicates = inst_list[1:]

            self.stdout.write(
                self.style.WARNING(
                    f"\n[GRUP] '{primary.name}' (Şehir: {primary.city.name if primary.city else 'Bilinmiyor'}, İlçe: {primary.district.name if primary.district else 'Bilinmiyor'})"
                )
            )
            self.stdout.write(f"  Ana Kayıt (Primary): ID={primary.pk} (Slug: {primary.slug}, Kontrat Sayısı: {primary.contracts.count()})")

            for dup in duplicates:
                self.stdout.write(f"  Mükerrer (Silinecek): ID={dup.pk} (Slug: {dup.slug}, Kontrat Sayısı: {dup.contracts.count()})")

            if not dry_run:
                with transaction.atomic():
                    # 1. Eksik alanları dup kayıtlardan tamamla
                    fields_updated = False
                    for dup in duplicates:
                        if not primary.address and dup.address:
                            primary.address = dup.address
                            fields_updated = True
                        if not primary.phone and dup.phone:
                            primary.phone = dup.phone
                            fields_updated = True
                        if primary.latitude is None and dup.latitude is not None:
                            primary.latitude = dup.latitude
                            fields_updated = True
                        if primary.longitude is None and dup.longitude is not None:
                            primary.longitude = dup.longitude
                            fields_updated = True
                        if not primary.district_id and dup.district_id:
                            primary.district_id = dup.district_id
                            fields_updated = True
                        if not primary.institution_type_id and dup.institution_type_id:
                            primary.institution_type_id = dup.institution_type_id
                            fields_updated = True
                        if not primary.raw_payload and dup.raw_payload:
                            primary.raw_payload = dup.raw_payload
                            fields_updated = True

                    if fields_updated:
                        primary.save()

                    # 2. Kontratları aktar veya birleştir
                    for dup in duplicates:
                        for contract in dup.contracts.all():
                            # Aynı (company, product_type, external_id) primary'de var mı?
                            existing_contract = InstitutionContract.objects.filter(
                                institution=primary,
                                company=contract.company,
                                product_type=contract.product_type,
                                external_id=contract.external_id,
                            ).first()

                            if existing_contract:
                                # Kontrat zaten var -> ilişkileri (policy_applications ve networks) ana kontrata aktar
                                existing_contract.policy_applications.add(*contract.policy_applications.all())
                                existing_contract.networks.add(*contract.networks.all())
                                if contract.coverage_notes and not existing_contract.coverage_notes:
                                    existing_contract.coverage_notes = contract.coverage_notes
                                    existing_contract.save(update_fields=["coverage_notes"])
                                contract.delete()
                                total_merged_contracts += 1
                            else:
                                # Kontrat ana kayıtta yok -> sadece institution_id'sini güncelle
                                contract.institution = primary
                                contract.save(update_fields=["institution"])
                                total_reassigned_contracts += 1

                        # 3. Mükerrer kurumu sil
                        dup.delete()
                        total_merged_institutions += 1
            else:
                for dup in duplicates:
                    total_merged_institutions += 1
                    total_reassigned_contracts += dup.contracts.count()

        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"[DRY-RUN SONUÇ] Birleştirilecek Mükerrer Kurum: {total_merged_institutions}"))
            self.stdout.write(self.style.SUCCESS(f"[DRY-RUN SONUÇ] Taşınacak/Birleştirilecek Kontrat: {total_reassigned_contracts}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"BAŞARILI: Toplam {total_merged_institutions} mükerrer kurum silinerek ana kayıtlara birleştirildi."))
            self.stdout.write(self.style.SUCCESS(f"Taşınan Kontrat Sayısı: {total_reassigned_contracts}"))
            self.stdout.write(self.style.SUCCESS(f"Birleştirilen (Zaten Var Olan) Kontrat Sayısı: {total_merged_contracts}"))
