from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from berita.models import SheetODON
from berita.services.odon import kredensial_tersedia
from berita.services.odon_otomatis import isi_odon


def baca(teks):
    try:
        return datetime.strptime(teks, "%d/%m/%Y").date()
    except ValueError:
        raise CommandError(f"Format tanggal harus dd/mm/yyyy, bukan '{teks}'.")


class Command(BaseCommand):
    help = ("Mengisi sheet ODON dengan satu berita per tanggal. "
            "Tanpa argumen, mengisi tanggal kemarin (H-1).")

    def add_arguments(self, parser):
        parser.add_argument("--tanggal", help="Satu tanggal, format dd/mm/yyyy")
        parser.add_argument("--dari", help="Awal rentang, format dd/mm/yyyy")
        parser.add_argument("--sampai", help="Akhir rentang, format dd/mm/yyyy")
        parser.add_argument("--dry-run", action="store_true",
                            help="Tampilkan rencana pengisian tanpa menulis ke sheet")

    def handle(self, *args, **opsi):
        if opsi["tanggal"]:
            daftar = [baca(opsi["tanggal"])]
        elif opsi["dari"]:
            awal = baca(opsi["dari"])
            akhir = baca(opsi["sampai"]) if opsi["sampai"] else timezone.localdate() - timedelta(days=1)
            if akhir < awal:
                raise CommandError("Tanggal --sampai lebih awal dari --dari.")
            daftar = [awal + timedelta(days=i) for i in range((akhir - awal).days + 1)]
        else:
            daftar = [timezone.localdate() - timedelta(days=1)]

        sheet = SheetODON.objects.filter(is_aktif=True).first()
        if not sheet:
            raise CommandError("Sheet ODON aktif belum diatur di menu Pengaturan.")
        if not opsi["dry_run"] and not kredensial_tersedia():
            raise CommandError(
                "Kredensial Google (GOOGLE_KREDENSIAL di .env) belum tersedia, "
                "sehingga sistem belum bisa menulis ke sheet. Gunakan --dry-run untuk simulasi."
            )

        mode = "SIMULASI" if opsi["dry_run"] else "PENGISIAN"
        self.stdout.write(f"{mode} ODON {daftar[0]:%d/%m/%Y} s.d. {daftar[-1]:%d/%m/%Y} "
                          f"ke '{sheet.nama}'\n")

        hasil = isi_odon(sheet, daftar, simulasi=opsi["dry_run"], cetak=self.stdout.write)

        kata = "akan ditulis" if opsi["dry_run"] else "ditulis"
        self.stdout.write(self.style.SUCCESS(
            f"\nSelesai: {hasil['ditulis']} {kata}, {hasil['sudah_ada']} sudah terisi, "
            f"{hasil['tanpa_berita']} tanpa berita."))
