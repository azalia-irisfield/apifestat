import re
import time

from django.core.management.base import BaseCommand

from berita.models import Berita
from berita.services.ringkasan import PANJANG_MAKS, bersihkan_isi, buat_ringkasan
from berita.services.scraper import ambil_artikel


def sudah_rapi(teks, judul):
    """Ringkasan pendek, berakhir dengan tanda baca, dan tanpa dateline/byline
    dianggap sudah rapi (bisa jadi hasil suntingan manual), jadi tidak ditimpa."""
    teks = (teks or "").strip()
    return (0 < len(teks) <= PANJANG_MAKS + 150
            and re.search(r"[.!?…][\"”’)]*$", teks)
            and len(teks) - len(bersihkan_isi(teks, judul)) <= 5)


class Command(BaseCommand):
    help = "Menyusun ulang ringkasan berita hasil scraping yang masih berupa potongan isi"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Tampilkan contoh hasil tanpa menyimpan")
        parser.add_argument("--semua", action="store_true",
                            help="Ikut proses ringkasan yang tampak sudah rapi/hasil suntingan")
        parser.add_argument("--ambil-ulang", action="store_true",
                            help="Buka ulang halaman artikel untuk isi lengkap (lebih lambat)")

    def handle(self, *args, **opsi):
        qs = Berita.objects.filter(sumber_input=Berita.SumberInput.SCRAPING).exclude(ringkasan="")
        diubah = dilewati = gagal = 0

        for b in qs.iterator():
            if not opsi["semua"] and sudah_rapi(b.ringkasan, b.judul):
                dilewati += 1
                continue

            teks = b.ringkasan
            if opsi["ambil_ulang"]:
                artikel = ambil_artikel(b.url)
                time.sleep(1)
                if artikel and artikel.get("isi"):
                    teks = artikel["isi"]

            baru = buat_ringkasan(teks, b.judul)
            if not baru or baru == b.ringkasan:
                gagal += 1
                continue

            if opsi["dry_run"]:
                if diubah < 5:
                    self.stdout.write(f"\n[{b.id}] {b.judul}\n  LAMA: {b.ringkasan[:150]}…\n  BARU: {baru}")
            else:
                b.ringkasan = baru
                b.save(update_fields=["ringkasan"])
            diubah += 1

        aksi = "akan diubah" if opsi["dry_run"] else "diubah"
        self.stdout.write(self.style.SUCCESS(
            f"\nSelesai: {diubah} {aksi}, {dilewati} dilewati (sudah rapi), "
            f"{gagal} tidak berubah."))