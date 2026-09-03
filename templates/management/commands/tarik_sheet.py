from django.core.management.base import BaseCommand

from inventarisasi.models import OPD
from inventarisasi.services.sheets import tarik_dari_opd


class Command(BaseCommand):
    help = "Menarik data inventarisasi dari spreadsheet OPD"

    def add_arguments(self, parser):
        parser.add_argument("--opd", type=int, help="ID OPD tertentu")
        parser.add_argument("--pratinjau", action="store_true", help="Tampilkan tanpa menyimpan")

    def handle(self, *args, **options):
        qs = OPD.objects.filter(is_aktif=True).exclude(id_spreadsheet="")
        if options["opd"]:
            qs = qs.filter(pk=options["opd"])

        for opd in qs:
            self.stdout.write(f"Menarik {opd.nama} ...")
            try:
                hasil = tarik_dari_opd(opd, simpan=not options["pratinjau"])
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  gagal: {exc}"))
                continue
            for ind, periode, nilai in hasil:
                self.stdout.write(f"  {periode.nama_periode:22} {ind.nama:35} {nilai}")
            self.stdout.write(self.style.SUCCESS(f"  {len(hasil)} nilai diproses"))