"""Pengisian template fenomena provinsi."""

import io
import tempfile

from fenomena.models import Fenomena
from fenomena.services.xlsx_util import baca, tulis
import re

KOL_ID, KOL_JENIS = 4, 3
KOL_ANGKA, KOL_DASAR, KOL_PENDUKUNG, KOL_INDIKATOR, KOL_FENOMENA = 6, 7, 8, 9, 10

PETA_JENIS = {"q-to-q": "qtoq", "y-o-y": "yoy", "c-to-c": "ctoc"}

def angka_dari_sel(nilai):
    """Membaca angka pertumbuhan yang sudah tertulis di template."""
    if nilai in (None, ""):
        return None
    try:
        return float(str(nilai).strip().replace(",", "."))
    except ValueError:
        return None

def saring_narasi(narasi, angka):
    """Menyaring poin narasi agar searah dengan angka pertumbuhan.

    Bila angka kosong, seluruh narasi dipakai apa adanya. Bila angka positif,
    hanya poin (+) dan (x) yang diambil; bila negatif, hanya (-) dan (x).
    """
    if angka is None or not narasi.strip():
        return narasi

    if angka > 0:
        tanda_dipakai, judul = {"+", "x"}, "Peningkatan:"
    elif angka < 0:
        tanda_dipakai, judul = {"-", "x"}, "Penurunan:"
    else:
        return narasi

    baris_dipakai, aktif = [], False
    for baris in narasi.splitlines():
        teks = baris.strip()
        if not teks:
            continue

        cocok = re.match(r"^\(([+\-x])\)", teks)
        if cocok:
            aktif = cocok.group(1) in tanda_dipakai
            if aktif:
                baris_dipakai.append(teks)
            continue

        # Baris tanpa penanda: judul kelompok dilewati, lanjutan poin diikutkan
        if teks.lower().rstrip(":") in ("peningkatan", "penurunan", "konstan"):
            aktif = False
            continue
        if aktif:
            baris_dipakai.append(teks)

    if not baris_dipakai:
        return ""
    return judul + "\n" + "\n".join(baris_dipakai)


def isi_template(berkas, periode, jenis_kategori):
    """Mengisi template provinsi dengan fenomena pada satu periode.

    Mengembalikan (buffer berkas, jumlah narasi terisi, daftar komponen kosong).
    """
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        for potongan in berkas.chunks() if hasattr(berkas, "chunks") else [berkas.read()]:
            tmp.write(potongan)
        sumber = tmp.name

    sel = baca(sumber)
    maks_baris = max(r for r, _ in sel)

    data = {}
    for f in Fenomena.objects.filter(
        periode=periode, kategori__jenis=jenis_kategori,
        kategori__id_template__isnull=False,
    ).select_related("kategori").prefetch_related("rincian_set"):
        for r in f.rincian_set.all():
            data[(f.kategori.id_template, r.jenis)] = r

    perubahan = {(3, 3): periode.tahun, (4, 3): f"Q{periode.triwulan}"}
    terisi, kosong = 0, []

    for baris in range(6, maks_baris + 1):
        id_komponen = sel.get((baris, KOL_ID))
        jenis = PETA_JENIS.get(str(sel.get((baris, KOL_JENIS), "")).strip().lower())
        if id_komponen is None or not jenis:
            continue

        r = data.get((int(id_komponen), jenis))
        if not r:
            if jenis == "qtoq":
                kosong.append(str(sel.get((baris, 2), "")).strip())
            continue

        angka_efektif = r.angka
        if angka_efektif is None:
            angka_efektif = angka_dari_sel(sel.get((baris, KOL_ANGKA)))
        else:
            perubahan[(baris, KOL_ANGKA)] = float(r.angka)

        if r.data_dasar:
            perubahan[(baris, KOL_DASAR)] = r.data_dasar
        if r.data_pendukung:
            perubahan[(baris, KOL_PENDUKUNG)] = r.data_pendukung
        if r.indikator_teks:
            perubahan[(baris, KOL_INDIKATOR)] = r.indikator_teks

        narasi = saring_narasi(r.narasi, angka_efektif)
        if narasi:
            perubahan[(baris, KOL_FENOMENA)] = narasi
            terisi += 1

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as out:
        tujuan = out.name
    tulis(sumber, tujuan, perubahan)

    with open(tujuan, "rb") as fh:
        buf = io.BytesIO(fh.read())
    buf.seek(0)
    return buf, terisi, kosong