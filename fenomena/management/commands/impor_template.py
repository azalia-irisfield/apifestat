from django.core.management.base import BaseCommand

from core.models import Kategori
from fenomena.services.xlsx_util import baca


def segmen(kode_no):
    """'A. 1. a.' -> ('A', '1', 'a')"""
    bagian = [b.strip() for b in (kode_no or "").split(".")]
    return tuple(b for b in bagian if b)


class Command(BaseCommand):
    help = "Membaca template fenomena provinsi dan menyusun daftar komponen beserta hierarkinya"

    def add_arguments(self, parser):
        parser.add_argument("berkas", type=str)
        parser.add_argument("--jenis", choices=["sektoral", "pengeluaran"], required=True)

    def handle(self, *args, **opsi):
        sel = baca(opsi["berkas"])
        jenis = opsi["jenis"]
        maks_baris = max(r for r, _ in sel)

        baris_komponen = []
        for r in range(6, maks_baris + 1):
            if str(sel.get((r, 3), "")).strip().lower() != "q-to-q":
                continue
            baris_komponen.append({
                "no": str(sel.get((r, 1), "")).strip(),
                "nama": str(sel.get((r, 2), "")).strip(),
                "id": sel.get((r, 4)),
            })

        peta, dibuat, diperbarui = {}, 0, 0
        for urut, b in enumerate(baris_komponen, start=1):
            if not b["nama"]:
                continue
            seg = segmen(b["no"])
            kode = ".".join(seg) if seg else f"TOTAL{b['id']}"
            induk = peta.get(seg[:-1]) if len(seg) > 1 else None

            obj, baru = Kategori.objects.update_or_create(
                jenis=jenis, kode=kode,
                defaults={
                    "nama": b["nama"],
                    "induk": induk,
                    "urutan": urut,
                    "id_template": int(b["id"]) if b["id"] else None,
                    "kode_template": b["no"],
                    "is_aktif": True,
                },
            )
            peta[seg] = obj
            dibuat += baru
            diperbarui += (not baru)

        self.stdout.write(self.style.SUCCESS(
            f"Selesai. {dibuat} komponen dibuat, {diperbarui} diperbarui, "
            f"total {len(baris_komponen)} baris terbaca."
        ))