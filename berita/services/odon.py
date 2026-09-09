"""Pencatatan berita terverifikasi ke spreadsheet One Day One News."""

import re

from django.conf import settings

# from fenomena.services.xlsx_util import indeks_ke_kolom
from inventarisasi.services.sheets import unduh_sheet

ROMAWI = {1: "I", 2: "II", 3: "III", 4: "IV"}

def indeks_ke_kolom(n):
    """1 -> A, 27 -> AA"""
    s = ""
    while n:
        n, sisa = divmod(n - 1, 26)
        s = chr(65 + sisa) + s
    return s

def periode_odon(berita):
    """Format periode seperti yang dipakai di sheet ODON: TW III-2026."""
    if not berita.periode:
        return "Lainnya"
    return f"TW {ROMAWI.get(berita.periode.triwulan, '')}-{berita.periode.tahun}"


def kategori_odon(berita):
    """Satu kode kategori lapangan usaha untuk kolom ODON.

    ODON hanya mencatat satu kategori Lapangan Usaha. Bila berita bertaut ke
    beberapa kategori, dipilih kategori sektoral tingkat pertama dengan skor
    kecocokan tertinggi. Komponen pengeluaran diabaikan.
    """
    relasi = (
        berita.beritakategori_set
        .select_related("kategori")
        .filter(kategori__jenis="sektoral")
        .order_by("-skor_otomatis", "kategori__urutan")
    )
    for r in relasi:
        k = r.kategori
        # Naikkan ke kategori induk bila yang tertaut berupa subkomponen
        while k.induk:
            k = k.induk
        return k.kode
    return ""


def baris_berita(berita):
    """Nilai yang akan ditulis ke sheet, urut dari kolom judul sampai periode."""
    return {
        "judul": berita.judul,
        "kategori": kategori_odon(berita),
        "ringkasan": berita.ringkasan[:1000],
        "dampak": berita.get_dampak_display() if berita.dampak else "",
        "sumber": berita.url,
        "periode": periode_odon(berita),
    }


def baris_tersedia(sheet, batas=60):
    """Baris yang tanggalnya sudah terisi tetapi beritanya belum.

    Kolom judul sering diisi nama petugas sebagai penanda sementara, dan akan
    tertimpa saat berita dicatat. Baris seperti itu tetap dianggap tersedia.
    """
    data = unduh_sheet(sheet.id_spreadsheet, sheet.gid_sheet)
    hasil = []

    for nomor in range(sheet.baris_pertama, len(data) + 1):
        baris = data[nomor - 1]

        def sel(k):
            try:
                return (baris[k - 1] or "").strip()
            except IndexError:
                return ""

        tanggal = sel(sheet.kol_tanggal)
        if not tanggal:
            continue

        judul = sel(sheet.kol_judul)
        # Baris dianggap sudah terisi bila kolom sumber atau ringkasan ada isinya
        if sel(sheet.kol_sumber) or sel(sheet.kol_ringkasan):
            continue

        hasil.append({
            "nomor": nomor,
            "tanggal": tanggal,
            "petugas": judul,
        })

    return hasil[-batas:]


def alamat_tempel(sheet, nomor_baris):
    awal = indeks_ke_kolom(sheet.kol_judul)
    akhir = indeks_ke_kolom(sheet.kol_periode)
    return f"{awal}{nomor_baris}:{akhir}{nomor_baris}"


def kredensial_tersedia():
    return bool(getattr(settings, "GOOGLE_KREDENSIAL", "")) and \
        __import__("os").path.exists(settings.GOOGLE_KREDENSIAL)


def kirim_ke_sheet(sheet, nomor_baris, berita):
    """Menulis satu berita ke baris tertentu pada sheet ODON."""
    import gspread
    from google.oauth2.service_account import Credentials

    lingkup = ["https://www.googleapis.com/auth/spreadsheets"]
    kred = Credentials.from_service_account_file(settings.GOOGLE_KREDENSIAL, scopes=lingkup)
    klien = gspread.authorize(kred)

    ws = klien.open_by_key(sheet.id_spreadsheet).worksheet(sheet.nama_tab)
    isi = baris_berita(berita)

    nilai = [[
        isi["judul"], isi["kategori"], isi["ringkasan"],
        isi["dampak"], isi["sumber"], isi["periode"],
    ]]
    ws.update(alamat_tempel(sheet, nomor_baris), nilai, value_input_option="USER_ENTERED")
    return True