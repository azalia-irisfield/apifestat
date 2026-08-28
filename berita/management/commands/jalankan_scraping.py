from django.core.management.base import BaseCommand

from berita.models import Portal
from berita.services.scraper import jalankan_scraping


class Command(BaseCommand):
    help = "Menjalankan scraping berita dari seluruh portal aktif"

    def add_arguments(self, parser):
        parser.add_argument("--portal", type=int, help="ID portal tertentu")
        parser.add_argument("--batas", type=int, default=20, help="Jumlah artikel maksimal")
        parser.add_argument("--halaman", type=int, default=1,
            help="Jumlah halaman indeks yang ditelusuri (portal HTML)")
        parser.add_argument("--sejak", type=str,
            help="Tarik berita sejak tanggal ini, format YYYY-MM-DD")

    def handle(self, *args, **options):
        from datetime import datetime
        sejak = None
        if options["sejak"]:
            sejak = datetime.strptime(options["sejak"], "%Y-%m-%d").date()

        qs = Portal.objects.filter(is_aktif=True)
        if options["portal"]:
            qs = qs.filter(pk=options["portal"])

        if not qs.exists():
            self.stdout.write(self.style.WARNING("Tidak ada portal aktif."))
            return

        for portal in qs:
            self.stdout.write(f"Scraping {portal.nama_portal} ...")
            log = jalankan_scraping(portal, batas=options["batas"],
                halaman_maks=options["halaman"],
                tanggal_minimal=sejak)
            if log.status == "sukses":
                self.stdout.write(self.style.SUCCESS(
                    f"  ditemukan {log.jumlah_ditemukan}, "
                    f"disimpan {log.jumlah_disimpan}, duplikat {log.jumlah_duplikat}"
                ))
            else:
                self.stdout.write(self.style.ERROR(f"  gagal: {log.pesan}"))