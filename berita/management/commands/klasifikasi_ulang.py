from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from berita.models import Berita
from berita.services.klasifikasi import gemini_tersedia, klasifikasi_berita


def baca(teks):
    try:
        return datetime.strptime(teks, "%d/%m/%Y").date()
    except ValueError:
        raise CommandError(f"Format tanggal harus dd/mm/yyyy, bukan '{teks}'.")


class Command(BaseCommand):
    help = ("Menentukan ulang kategori (bisa lebih dari satu) dan dampak berita "
            "berstatus Baru dengan Gemini. Berita terverifikasi tidak disentuh.")

    def add_arguments(self, parser):
        parser.add_argument("--dari", required=True, help="Tanggal terbit awal, dd/mm/yyyy")
        parser.add_argument("--sampai", required=True, help="Tanggal terbit akhir, dd/mm/yyyy")

    def handle(self, *args, **opsi):
        if not gemini_tersedia():
            raise CommandError("GEMINI_API_KEY belum diisi di .env.")

        qs = Berita.objects.filter(
            status=Berita.Status.BARU,
            tanggal_berita__gte=baca(opsi["dari"]),
            tanggal_berita__lte=baca(opsi["sampai"]),
        ).order_by("tanggal_berita", "id")

        daftar = list(qs)
        self.stdout.write(f"{len(daftar)} berita akan diklasifikasikan ulang...")
        n_gemini, n_cadangan = klasifikasi_berita(daftar)
        self.stdout.write(self.style.SUCCESS(
            f"Selesai: {n_gemini} oleh Gemini, {n_cadangan} oleh kata kunci (cadangan)."))
