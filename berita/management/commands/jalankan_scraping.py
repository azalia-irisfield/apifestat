from django.core.management.base import BaseCommand

from berita.models import Portal
from berita.services.scraper import jalankan_scraping


class Command(BaseCommand):
    help = "Menjalankan scraping berita dari seluruh portal aktif"

    def add_arguments(self, parser):
        parser.add_argument("--portal", type=int, help="ID portal tertentu")
        parser.add_argument("--batas", type=int, default=20, help="Jumlah artikel maksimal")

    def handle(self, *args, **options):
        qs = Portal.objects.filter(is_aktif=True)
        if options["portal"]:
            qs = qs.filter(pk=options["portal"])

        if not qs.exists():
            self.stdout.write(self.style.WARNING("Tidak ada portal aktif."))
            return

        for portal in qs:
            self.stdout.write(f"Scraping {portal.nama_portal} ...")
            log = jalankan_scraping(portal, batas=options["batas"])
            if log.status == "sukses":
                self.stdout.write(self.style.SUCCESS(
                    f"  ditemukan {log.jumlah_ditemukan}, "
                    f"disimpan {log.jumlah_disimpan}, duplikat {log.jumlah_duplikat}"
                ))
            else:
                self.stdout.write(self.style.ERROR(f"  gagal: {log.pesan}"))