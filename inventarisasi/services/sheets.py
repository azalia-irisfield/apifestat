"""Penarikan data inventarisasi dari Google Sheets melalui ekspor CSV publik."""

import csv
import io
import re
from decimal import Decimal, InvalidOperation

import requests

from core.models import Periode
from inventarisasi.models import Indikator, NilaiIndikator

USER_AGENT = "APIFESTAT/1.0 (BPS Kabupaten Malinau)"
ROMAWI = {"I": 1, "II": 2, "III": 3, "IV": 4}


def url_csv(id_spreadsheet, gid="0"):
    return (f"https://docs.google.com/spreadsheets/d/{id_spreadsheet}"
            f"/export?format=csv&gid={gid}")


def unduh_sheet(id_spreadsheet, gid="0"):
    """Mengunduh satu sheet sebagai daftar baris."""
    r = requests.get(url_csv(id_spreadsheet, gid),
                     headers={"User-Agent": USER_AGENT}, timeout=30)
    if r.status_code == 404:
        raise ValueError("Spreadsheet atau gid tidak ditemukan.")
    if "text/html" in r.headers.get("Content-Type", ""):
        raise ValueError(
            "Spreadsheet belum dapat diakses publik. Ubah berbagi menjadi "
            "“Anyone with the link — Viewer”."
        )
    r.raise_for_status()
    r.encoding = "utf-8"
    return list(csv.reader(io.StringIO(r.text)))


def sel(baris, r, k):
    """Membaca sel pada baris ke-r kolom ke-k, keduanya berbasis 1."""
    try:
        return baris[r - 1][k - 1].strip()
    except IndexError:
        return ""


def ke_angka(teks):
    """Mengubah teks sel menjadi angka. Mengembalikan None bila kosong."""
    if teks is None:
        return None
    t = str(teks).strip().replace("\u00a0", " ")
    t = t.replace("Rp", "").replace("%", "").strip()
    if t in ("", "-", "–", "—"):
        return None
    negatif = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    t = re.sub(r"[^\d,.\-]", "", t)
    if t.count(",") and t.count("."):
        t = t.replace(",", "")          # koma sebagai pemisah ribuan
    elif t.count(",") and not t.count("."):
        t = t.replace(",", ".")         # koma sebagai desimal
    try:
        nilai = Decimal(t)
    except (InvalidOperation, ValueError):
        return None
    return -nilai if negatif else nilai


def isi_ke_kanan(deret):
    """Mengisi sel kosong dengan nilai terakhir yang tidak kosong (sel tergabung)."""
    hasil, terakhir = [], ""
    for x in deret:
        x = (x or "").strip()
        if x:
            terakhir = x
        hasil.append(terakhir)
    return hasil


def cari_periode(tahun, triwulan):
    return Periode.objects.filter(tahun=tahun, triwulan=triwulan).first()


def kolom_periode(baris, cfg):
    """Memetakan indeks kolom ke objek Periode, untuk sheet berorientasi kolom."""
    br_tahun = cfg.get("baris_tahun")
    br_periode = cfg["baris_periode"]

    deret_periode = baris[br_periode - 1] if len(baris) >= br_periode else []
    deret_tahun = (isi_ke_kanan(baris[br_tahun - 1])
                   if br_tahun and len(baris) >= br_tahun else [])

    peta = {}
    for i, teks in enumerate(deret_periode):
        cocok = re.search(r"triwulan\s+(IV|III|II|I)\b", (teks or ""), re.I)
        if not cocok:
            continue
        tw = ROMAWI[cocok.group(1).upper()]

        tahun = cfg.get("tahun")
        if br_tahun and i < len(deret_tahun):
            th = re.search(r"(20\d{2})", deret_tahun[i] or "")
            if th:
                tahun = int(th.group(1))
        if not tahun:
            continue

        periode = cari_periode(tahun, tw)
        if periode:
            peta[i + 1] = periode
    return peta


def tarik_orientasi_kolom(baris, cfg, indikator_list):
    """Periode berada di kolom, indikator di baris (contoh: sheet PDAM)."""
    peta = kolom_periode(baris, cfg)
    if not peta:
        raise ValueError("Tidak ditemukan kolom Triwulan pada sheet.")

    hasil = []
    for ind in indikator_list:
        if not str(ind.sel_sumber).strip().isdigit():
            continue
        r = int(ind.sel_sumber)
        for k, periode in peta.items():
            nilai = ke_angka(sel(baris, r, k))
            if nilai is not None:
                hasil.append((ind, periode, nilai))
    return hasil


def tarik_orientasi_baris(baris, cfg, indikator_list):
    """Periode berada di baris, indikator di kolom (contoh: sheet sampah DLH)."""

    tahun = cfg.get("tahun")
    k_periode = cfg["kolom_periode"]
    r_awal = cfg.get("baris_pertama", 1)
    r_akhir = cfg.get("baris_terakhir", r_awal + 20)

    if not tahun:
            raise ValueError(
                "Orientasi baris membutuhkan tahun. Isi kolom 'Tahun data' untuk sheet utama, "
                "dan format gid:tahun pada 'GID sheet tahun lain'."
            )

    hasil = []
    for r in range(r_awal, r_akhir + 1):
        teks = sel(baris, r, k_periode)
        cocok = re.fullmatch(r"\s*(IV|III|II|I)\s*", teks or "", re.I)
        if not cocok:
            continue
        periode = cari_periode(tahun, ROMAWI[cocok.group(1).upper()])
        if not periode:
            continue
        for ind in indikator_list:
            if not str(ind.sel_sumber).strip().isdigit():
                continue
            nilai = ke_angka(sel(baris, r, int(ind.sel_sumber)))
            if nilai is not None:
                hasil.append((ind, periode, nilai))
    return hasil

def kolom_periode_sederhana(baris, cfg):
    """Memetakan kolom ke nomor triwulan, tanpa memperhatikan tahun."""
    br = cfg["baris_periode"]
    deret = baris[br - 1] if len(baris) >= br else []
    peta = {}
    for i, teks in enumerate(deret):
        cocok = re.search(r"triwulan\s+(IV|III|II|I)\b", (teks or ""), re.I)
        if cocok:
            peta[i + 1] = ROMAWI[cocok.group(1).upper()]
    return peta


def tarik_orientasi_kolom_bertahun(baris, cfg, indikator_list):
    """Triwulan di kolom, tahun muncul sebagai baris pemisah di antara data.

    Indikator dikenali dari teks pada kolom label, bukan dari nomor baris.
    """
    peta_tw = kolom_periode_sederhana(baris, cfg)
    if not peta_tw:
        raise ValueError("Tidak ditemukan kolom Triwulan pada sheet.")

    k_label = cfg.get("kolom_label") or 1
    berdasar_label = {
        str(i.sel_sumber).strip().lower(): i
        for i in indikator_list if str(i.sel_sumber).strip()
    }

    hasil, tahun = [], None
    for r in range(cfg["baris_periode"] + 1, len(baris) + 1):
        label = sel(baris, r, k_label)
        if not label:
            continue

        th = re.fullmatch(r"\s*(20\d{2})\s*", label)
        if th:
            tahun = int(th.group(1))
            continue

        ind = berdasar_label.get(label.strip().lower())
        if not ind or not tahun:
            continue

        for k, tw in peta_tw.items():
            periode = cari_periode(tahun, tw)
            nilai = ke_angka(sel(baris, r, k))
            if periode and nilai is not None:
                hasil.append((ind, periode, nilai))
    return hasil

def tarik_dari_opd(opd, simpan=True):
    """Menarik nilai indikator dari seluruh sheet milik satu OPD."""
    if not opd.id_spreadsheet:
        raise ValueError(f"{opd} belum memiliki ID spreadsheet.")

    indikator_list = list(Indikator.objects.filter(opd=opd, is_aktif=True))
    hasil = []

    for gid, tahun in opd.daftar_sheet:
        cfg = opd.pemetaan_untuk(gid, tahun)
        baris = unduh_sheet(opd.id_spreadsheet, str(gid))

        orientasi = cfg.get("orientasi", "kolom")
        if orientasi == "baris":
            hasil += tarik_orientasi_baris(baris, cfg, indikator_list)
        elif orientasi == "kolom_bertahun":
            hasil += tarik_orientasi_kolom_bertahun(baris, cfg, indikator_list)
        else:
            hasil += tarik_orientasi_kolom(baris, cfg, indikator_list)

    if simpan:
        for ind, periode, nilai in hasil:
            NilaiIndikator.objects.update_or_create(
                indikator=ind, periode=periode,
                defaults={"nilai": nilai, "sumber_input": "sinkronisasi"},
            )
    return hasil