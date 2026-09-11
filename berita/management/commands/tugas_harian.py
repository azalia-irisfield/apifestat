from datetime import datetime

from django.core.management.base import BaseCommand

from berita.models import Berita, BeritaKategori, Portal
from berita.services.scraper import (jalankan_scraping, tentukan_lingkup,
                                     usulkan_kategori)


class Command(BaseCommand):
    help = "Tugas harian: scraping seluruh portal aktif lalu klasifikasi otomatis"

    def add_arguments(self, parser):
        parser.add_argument("--batas-rss", type=int, default=25)
        parser.add_argument("--batas-html", type=int, default=10)

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

        # Klasifikasi dan lingkup untuk berita yang belum diproses
        diproses = 0
        for b in Berita.objects.filter(status=Berita.Status.BARU, kategori__isnull=True):
            b.lingkup = tentukan_lingkup(b.judul, b.ringkasan)
            b.save(update_fields=["lingkup"])
            for k, skor in usulkan_kategori(b.judul, b.ringkasan):
                BeritaKategori.objects.get_or_create(
                    berita=b, kategori=k, defaults={"skor_otomatis": skor}
                )
            diproses += 1

        self.catat(f"Klasifikasi otomatis: {diproses} berita diproses")
        self.catat(f"=== Selesai. {total_simpan} berita baru tersimpan ===\n")