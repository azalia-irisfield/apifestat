"""Penyusunan usulan narasi fenomena dari data inventarisasi dan berita."""

from inventarisasi.models import Indikator
from inventarisasi.services.hitung import hitung_indikator, susun_narasi


def usulan_dari_inventarisasi(kategori, periode, jenis):
    """Narasi otomatis dari indikator milik kategori ini dan seluruh subkomponennya."""
    komponen = kategori.keturunan()
    hasil = [
        hitung_indikator(ind, periode)
        for ind in Indikator.objects.filter(komponen__in=komponen, is_aktif=True)
    ]
    return susun_narasi(hasil, jenis)


def usulan_dari_berita(fenomena, jenis=""):
    """Daftar poin dari berita yang ditautkan ke fenomena."""
    from fenomena.models import FenomenaBerita

    qs = FenomenaBerita.objects.filter(fenomena=fenomena).select_related("berita")
    if jenis:
        qs = qs.filter(jenis__in=["", jenis])

    baris = []
    for fb in qs.order_by("urutan", "id"):
        b = fb.berita
        tanda = "+" if b.dampak.startswith("meningkatkan") else "-"
        teks = fb.kutipan.strip() or b.ringkasan.strip()[:400] or b.judul
        baris.append(f"({tanda}) {teks}\n(Sumber: {b.url} )")
    return "\n".join(baris)


def gabung_usulan(fenomena, jenis):
    bagian = [
        usulan_dari_inventarisasi(fenomena.kategori, fenomena.periode, jenis),
        usulan_dari_berita(fenomena, jenis),
    ]
    return "\n\n".join(b for b in bagian if b.strip())