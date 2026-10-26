# from datetime import datetime

# from django.core.management.base import BaseCommand

# from berita.models import Berita, BeritaKategori, Portal
# from berita.services.scraper import (jalankan_scraping, tentukan_lingkup,
#                                      usulkan_kategori)


# class Command(BaseCommand):
#     help = "Tugas harian: scraping seluruh portal aktif lalu klasifikasi otomatis"

#     def add_arguments(self, parser):
#         parser.add_argument("--batas-rss", type=int, default=25)
#         parser.add_argument("--batas-html", type=int, default=10)

#     def catat(self, pesan):
#         waktu = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
#         self.stdout.write(f"[{waktu}] {pesan}")

#     def handle(self, *args, **opsi):
#         self.catat("=== Tugas harian APIFESTAT dimulai ===")

#         total_simpan = 0
#         for portal in Portal.objects.filter(is_aktif=True):
#             batas = (opsi["batas_rss"] if portal.tipe_sumber == Portal.TipeSumber.RSS
#                      else opsi["batas_html"])
#             self.catat(f"Scraping {portal.nama_portal} (batas {batas})")
#             try:
#                 log = jalankan_scraping(portal, batas=batas)
#             except Exception as exc:
#                 self.catat(f"  GAGAL: {exc}")
#                 continue

#             if log.status == "sukses":
#                 self.catat(f"  ditemukan {log.jumlah_ditemukan}, "
#                            f"disimpan {log.jumlah_disimpan}, "
#                            f"duplikat {log.jumlah_duplikat}, "
#                            f"di luar wilayah {log.jumlah_diabaikan}")
#                 total_simpan += log.jumlah_disimpan
#             else:
#                 self.catat(f"  gagal: {log.pesan}")

#         # Klasifikasi dan lingkup untuk berita yang belum diproses
#         diproses = 0
#         for b in Berita.objects.filter(status=Berita.Status.BARU, kategori__isnull=True):
#             b.lingkup = tentukan_lingkup(b.judul, b.ringkasan)
#             b.save(update_fields=["lingkup"])
#             for k, skor in usulkan_kategori(b.judul, b.ringkasan):
#                 BeritaKategori.objects.get_or_create(
#                     berita=b, kategori=k, defaults={"skor_otomatis": skor}
#                 )
#             diproses += 1

#         self.catat(f"Klasifikasi otomatis: {diproses} berita diproses")
#         self.catat(f"=== Selesai. {total_simpan} berita baru tersimpan ===\n")

from datetime import datetime, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from berita.models import Berita, Portal
from berita.services.klasifikasi import klasifikasi_berita
from berita.services.scraper import jalankan_scraping, tentukan_lingkup


class Command(BaseCommand):
    help = "Tugas harian: scraping seluruh portal aktif lalu klasifikasi otomatis"

    def add_arguments(self, parser):
        parser.add_argument("--batas-rss", type=int, default=25)
        parser.add_argument("--batas-html", type=int, default=10)
        parser.add_argument("--tanpa-odon", action="store_true",
                            help="Lewati pengisian otomatis sheet ODON")

    def catat(self, pesan):
        waktu = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.stdout.write(f"[{waktu}] {pesan}")

    def handle(self, *args, **opsi):
        self.catat("=== Tugas harian APIFESTAT dimulai ===")

        total_simpan = 0
        for portal in Portal.objects.filter(is_aktif=True):
            batas = (opsi["batas_rss"] if portal.tipe_sumber == Portal.TipeSumber.RSS
                     else opsi["batas_html"])
            self.catat(f"Scraping {portal.nama_portal} (batas {batas})")
            try:
                log = jalankan_scraping(portal, batas=batas)
            except Exception as exc:
                self.catat(f"  GAGAL: {exc}")
                continue

            if log.status == "sukses":
                self.catat(f"  ditemukan {log.jumlah_ditemukan}, "
                           f"disimpan {log.jumlah_disimpan}, "
                           f"duplikat {log.jumlah_duplikat}, "
                           f"di luar wilayah {log.jumlah_diabaikan}")
                total_simpan += log.jumlah_disimpan
            else:
                self.catat(f"  gagal: {log.pesan}")

        # Klasifikasi ulang berita 2 hari terakhir yang belum berkategori
        # (mis. Gemini sempat gagal). Dibatasi 2 hari agar berita non-ekonomi
        # yang memang tanpa kategori tidak dikirim ulang setiap kali.
        batas = timezone.now() - timedelta(days=2)
        belum = list(Berita.objects.filter(status=Berita.Status.BARU, kategori__isnull=True,
                                           created_at__gte=batas))
        for b in belum:
            b.lingkup = tentukan_lingkup(b.judul, b.ringkasan)
            b.save(update_fields=["lingkup"])
        n_gemini, n_cadangan = klasifikasi_berita(belum)
        self.catat(f"Klasifikasi otomatis: {n_gemini} oleh Gemini, "
                   f"{n_cadangan} oleh kata kunci")

        # Pengisian ODON untuk H-1. Aman dijalankan 4x sehari: tanggal yang
        # sudah terisi di sheet otomatis dilewati.
        if not opsi["tanpa_odon"]:
            self.catat("Pengisian ODON tanggal kemarin")
            try:
                call_command("isi_odon", stdout=self.stdout)
            except Exception as exc:
                self.catat(f"  ODON dilewati: {exc}")
        self.catat(f"=== Selesai. {total_simpan} berita baru tersimpan ===\n")