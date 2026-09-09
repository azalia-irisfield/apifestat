import re
from datetime import date

from django.core.management.base import BaseCommand

from berita.models import Berita
from core.models import Periode

BULAN = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11,
    "desember": 12, "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "agu": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12,
}


def cari_tanggal(teks, tanggal_terbit):
    """Mencari tanggal peristiwa yang disebut di dalam teks berita.

    Tahun disimpulkan dari tanggal terbit bila tidak disebutkan. Bila tanggal
    hasil simpulan jatuh di masa depan, tahunnya dimundurkan satu.
    """
    if not teks:
        return None
    t = teks.lower()
    tahun_terbit = tanggal_terbit.year

    def bentuk(tahun, bulan, hari, tanpa_tahun=False):
        try:
            hasil = date(int(tahun), int(bulan), int(hari))
        except ValueError:
            return None
        # Berita tidak melaporkan masa depan: mundurkan setahun bila perlu
        if tanpa_tahun and (hasil - tanggal_terbit).days > 3:
            try:
                hasil = date(int(tahun) - 1, int(bulan), int(hari))
            except ValueError:
                return None
        return hasil

    kandidat = []

    # 11/3/2026 atau 11-3-2026
    for h, b, th in re.findall(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", t):
        kandidat.append(bentuk(th, b, h))

    # 17 Februari 2026
    pola = r"\b(\d{1,2})\s+(" + "|".join(BULAN) + r")\s+(\d{4})\b"
    for h, nama, th in re.findall(pola, t):
        kandidat.append(bentuk(th, BULAN[nama], h))

    # 17 Februari, tanpa tahun
    pola = r"\b(\d{1,2})\s+(" + "|".join(BULAN) + r")\b(?!\s*\d{4})"
    for h, nama in re.findall(pola, t):
        kandidat.append(bentuk(tahun_terbit, BULAN[nama], h, tanpa_tahun=True))

    # 26/4 atau 26-4, tanpa tahun. Tidak diikuti angka lain agar
    # "1/3 warga" atau "skor 2-1" tidak ikut tertangkap.
    for h, b in re.findall(r"(?<![\d/-])(\d{1,2})[/-](\d{1,2})(?![\d/-])", t):
        if 1 <= int(b) <= 12 and 1 <= int(h) <= 31:
            kandidat.append(bentuk(tahun_terbit, b, h, tanpa_tahun=True))

    for k in kandidat:
        if k:
            return k
    return None


class Command(BaseCommand):
    help = "Mendeteksi tanggal peristiwa dari teks berita dan menyesuaikan periodenya"

    def add_arguments(self, parser):
        parser.add_argument("--pratinjau", action="store_true",
                            help="Tampilkan hasil tanpa menyimpan")
        parser.add_argument("--timpa", action="store_true",
                            help="Timpa tanggal peristiwa yang sudah terisi")
        parser.add_argument("--batas-hari", type=int, default=400,
                            help="Selisih maksimal terhadap tanggal terbit")

    def handle(self, *args, **opsi):
        qs = Berita.objects.all()
        if not opsi["timpa"]:
            qs = qs.filter(tanggal_peristiwa__isnull=True)

        terisi = dilewati = periode_berubah = 0

        for b in qs.iterator():
            tanggal = cari_tanggal(f"{b.judul} {b.ringkasan}", b.tanggal_berita)

            if not tanggal:
                dilewati += 1
                continue

            selisih = (b.tanggal_berita - tanggal).days
            # Peristiwa tidak boleh jauh di masa depan atau terlalu lampau
            if selisih < -3 or selisih > opsi["batas_hari"]:
                dilewati += 1
                continue
            if tanggal == b.tanggal_berita:
                dilewati += 1
                continue

            periode_baru = Periode.objects.filter(
                tanggal_mulai__lte=tanggal, tanggal_selesai__gte=tanggal
            ).first()

            tanda = ""
            if periode_baru and periode_baru != b.periode:
                tanda = f"  [periode: {b.periode} -> {periode_baru}]"
                periode_berubah += 1

            self.stdout.write(
                f"{b.tanggal_berita} -> {tanggal}  {b.judul[:55]}{tanda}"
            )

            if not opsi["pratinjau"]:
                b.tanggal_peristiwa = tanggal
                if periode_baru:
                    b.periode = periode_baru
                b.save(update_fields=["tanggal_peristiwa", "periode", "updated_at"])
            terisi += 1

        awalan = "PRATINJAU — " if opsi["pratinjau"] else ""
        self.stdout.write(self.style.SUCCESS(
            f"{awalan}{terisi} berita terdeteksi, {periode_berubah} berubah periode, "
            f"{dilewati} dilewati."
        ))