"""Pengisian otomatis spreadsheet ODON: satu berita terpilih per tanggal.

Aturan pemilihan berita untuk tanggal D (tanggal terbit = D):
1. Hanya berita yang punya kategori Lapangan Usaha (A-U). Berita yang hanya
   berkategori Pengeluaran (1-8) tidak ikut; berita ganda (Pengeluaran +
   Lapangan Usaha) tetap ikut dengan kategori Lapangan Usahanya.
2. Berita berstatus Ditolak dan berita yang URL-nya sudah ada di sheet dilewati.
3. Urutan prioritas:
   a. Lingkup: Malinau, lalu Kaltara, lalu lainnya.
   b. Kelompok kategori: B, A, E, G, I, P, Q (sesuai urutan itu), lalu R,S,T,U,
      lalu kategori lainnya.
   c. Berita terverifikasi didahulukan, lalu keyakinan dampak, lalu skor kategori.

Aturan penulisan untuk tanggal D:
- Ada baris bertanggal D yang sudah berisi berita -> dilewati (dianggap sudah diisi).
- Ada baris bertanggal D yang masih kosong (boleh berisi nama petugas di kolom
  judul) -> berita ditulis ke baris itu.
- Tidak ada baris bertanggal D -> baris baru disisipkan sesuai urutan tanggal.
"""

import re
import time
from datetime import date, timedelta

from berita.models import Berita
from berita.services.dampak import tebak_dampak
from berita.services.klasifikasi import batasi_relevansi
from berita.services.odon import (alamat_tempel, indeks_ke_kolom,
                                  kategori_odon, periode_odon)

PRIORITAS_UTAMA = ["B", "A", "E", "G", "I", "P", "Q"]
MUNDUR_HARI = 7          # berita H-1 s.d. H-7 boleh dipakai bila belum terpakai
RELEVANSI_LAMPAU = 2     # relevansi minimal untuk berita dari hari sebelumnya
PRIORITAS_KEDUA = ["R,S,T,U"]
URUTAN_LINGKUP = {"malinau": 0, "kaltara": 1}
JEDA_TULIS = 1.2   # detik, batas Google Sheets API sekitar 60 tulisan per menit


# ---------------------------------------------------------------- tanggal

def baca_tanggal(teks):
    """Membaca tanggal dari sel sheet: 07/09/2026, 7/9/2026, atau 2026-09-07."""
    teks = (teks or "").strip()
    m = re.match(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", teks)
    try:
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", teks)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        pass
    return None


def format_tanggal(tgl):
    return tgl.strftime("%d/%m/%Y")


# ---------------------------------------------------------------- pemilihan

def _peringkat_kategori(kode):
    if kode in PRIORITAS_UTAMA:
        return (0, PRIORITAS_UTAMA.index(kode))
    if kode in PRIORITAS_KEDUA:
        return (1, 0)
    return (2, 0)


def pilih_berita(tanggal, url_terpakai=()):
    """Mengembalikan (berita, kode_kategori, dampak, keyakinan, alasan) atau None."""
    kandidat = []
    qs = (Berita.objects.filter(tanggal_berita__gte=tanggal - timedelta(days=MUNDUR_HARI),
                                tanggal_berita__lte=tanggal)
          .exclude(status=Berita.Status.DITOLAK)
          .prefetch_related("beritakategori_set__kategori"))

    for b in qs:
        if b.url in url_terpakai:
            continue
        # Pembatas judul ikut diterapkan agar hasil lama tidak perlu dinilai ulang
        b.relevansi = batasi_relevansi(b.judul, b.relevansi)
        if b.relevansi == 0:               # bukan berita ekonomi
            continue
        selisih = (tanggal - b.tanggal_berita).days
        # Berita hari sebelumnya hanya dipakai bila kuat
        if selisih > 0 and (b.relevansi or 0) < RELEVANSI_LAMPAU:
            continue
        kode = kategori_odon(b)
        if not kode:                       # hanya Pengeluaran / tanpa kategori
            continue

        if b.dampak:                       # dampak tersimpan (Gemini/petugas) diutamakan
            dampak, yakin, alasan = b.dampak, 1.0, "dampak tersimpan"
        else:
            dampak, yakin, alasan = tebak_dampak(b.judul, b.ringkasan)

        skor_kat = max((float(r.skor_otomatis or 0) for r in b.beritakategori_set.all()),
                       default=0)
        # Relevansi kosong (belum dinilai Gemini) diperlakukan seperti nilai 1
        relevansi = 1 if b.relevansi is None else b.relevansi
        kunci = (
            0 if relevansi >= 2 else 1,    # fenomena layak (2-3) selalu didahulukan
            URUTAN_LINGKUP.get(b.lingkup, 2),
            *_peringkat_kategori(kode),
            -relevansi,
            selisih,                       # bila setara, berita yang lebih baru
            0 if b.status == Berita.Status.TERVERIFIKASI else 1,
            -yakin,
            -skor_kat,
            b.id,
        )
        kandidat.append((kunci, b, kode, dampak, yakin, alasan))

    if not kandidat:
        return None
    kandidat.sort(key=lambda x: x[0])
    _, b, kode, dampak, yakin, alasan = kandidat[0]
    return b, kode, dampak, yakin, alasan


def _teks(nilai):
    """Mencegah teks yang diawali = + - @ terbaca sebagai rumus oleh Sheets."""
    nilai = (nilai or "").strip()
    return "'" + nilai if nilai[:1] in ("=", "+", "-", "@") else nilai


def nilai_baris(berita, kode, dampak):
    """Nilai kolom judul s.d. periode, sesuai urutan kolom sheet ODON."""
    return [
        _teks(berita.judul),
        kode,
        _teks(berita.ringkasan[:1000]),
        Berita.Dampak(dampak).label,
        berita.url,
        periode_odon(berita),
    ]


# ---------------------------------------------------------------- sheet

def _sel(baris, kolom):
    try:
        return (baris[kolom - 1] or "").strip()
    except IndexError:
        return ""


def petakan_sheet(sheet, data):
    """Meringkas isi sheet: baris per tanggal, baris terisi, dan URL yang sudah ada."""
    per_tanggal, terisi, url = {}, set(), set()
    for nomor in range(sheet.baris_pertama, len(data) + 1):
        baris = data[nomor - 1]
        tgl = baca_tanggal(_sel(baris, sheet.kol_tanggal))
        sumber = _sel(baris, sheet.kol_sumber)
        if sumber:
            url.add(sumber)
        if not tgl:
            continue
        per_tanggal.setdefault(tgl, []).append(nomor)
        if sumber or _sel(baris, sheet.kol_ringkasan):
            terisi.add(tgl)
    return per_tanggal, terisi, url


def posisi_sisip(sheet, data, tanggal):
    """Nomor baris untuk baris baru agar tanggal tetap berurutan."""
    posisi = sheet.baris_pertama
    for nomor in range(sheet.baris_pertama, len(data) + 1):
        tgl = baca_tanggal(_sel(data[nomor - 1], sheet.kol_tanggal))
        if tgl and tgl <= tanggal:
            posisi = nomor + 1
    return posisi


def buka_worksheet(sheet):
    import gspread
    from django.conf import settings
    from google.oauth2.service_account import Credentials

    kred = Credentials.from_service_account_file(
        settings.GOOGLE_KREDENSIAL,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    buku = gspread.authorize(kred).open_by_key(sheet.id_spreadsheet)
    try:
        return buku.get_worksheet_by_id(int(sheet.gid_sheet))
    except Exception:
        return buku.worksheet(sheet.nama_tab)


def isi_odon(sheet, daftar_tanggal, simulasi=False, cetak=print):
    """Mengisi sheet ODON untuk setiap tanggal. Mengembalikan ringkasan hasil."""
    if simulasi:
        from inventarisasi.services.sheets import unduh_sheet
        ws = None
        data = unduh_sheet(sheet.id_spreadsheet, sheet.gid_sheet)
    else:
        ws = buka_worksheet(sheet)
        data = ws.get_all_values()

    per_tanggal, terisi, url_terpakai = petakan_sheet(sheet, data)
    hasil = {"ditulis": 0, "sudah_ada": 0, "tanpa_berita": 0}
    disisipkan = False

    for tgl in sorted(daftar_tanggal):
        label = format_tanggal(tgl)
        if tgl in terisi:
            hasil["sudah_ada"] += 1
            cetak(f"{label}  lewat: sudah terisi di sheet")
            continue

        pilihan = pilih_berita(tgl, url_terpakai)
        if not pilihan:
            hasil["tanpa_berita"] += 1
            cetak(f"{label}  lewat: tidak ada berita ekonomi berkategori Lapangan Usaha")
            continue

        berita, kode, dampak, yakin, alasan = pilihan
        nilai = nilai_baris(berita, kode, dampak)
        baris_kosong = per_tanggal.get(tgl)

        if baris_kosong:
            nomor, cara = baris_kosong[0], "isi baris"
        else:
            nomor, cara = posisi_sisip(sheet, data, tgl), "sisip baris"

        rel = "-" if berita.relevansi is None else berita.relevansi
        lemah = "  <- lemah, periksa" if (berita.relevansi or 0) < 2 else ""
        asal = ("" if berita.tanggal_berita == tgl
                else f" [berita {berita.tanggal_berita:%d/%m}]")
        cetak(f"{label}  {cara} {nomor}: [{kode}] {nilai[3]} "
              f"(relevansi {rel}){asal} {berita.judul[:70]}{lemah}")

        if not simulasi:
            if baris_kosong:
                ws.update(range_name=alamat_tempel(sheet, nomor), values=[nilai],
                          value_input_option="USER_ENTERED")
            else:
                baris_baru = [""] * sheet.kol_periode
                # =DATE() agar terbaca sebagai tanggal apa pun pengaturan lokal sheet
                baris_baru[sheet.kol_tanggal - 1] = f"=DATE({tgl.year},{tgl.month},{tgl.day})"
                baris_baru[sheet.kol_judul - 1:sheet.kol_periode] = nilai
                ws.insert_row(baris_baru, index=nomor, value_input_option="USER_ENTERED",
                              inherit_from_before=nomor > sheet.baris_pertama)
                disisipkan = True
            time.sleep(JEDA_TULIS)

            # Dampak hasil tebakan ikut disimpan bila petugas belum mengisinya
            if not berita.dampak:
                berita.dampak = dampak
                berita.save(update_fields=["dampak"])

        # Perbarui salinan lokal agar tanggal berikutnya membaca posisi yang benar
        tampil = [""] * sheet.kol_periode
        tampil[sheet.kol_tanggal - 1] = label
        tampil[sheet.kol_judul - 1:sheet.kol_periode] = nilai
        if baris_kosong:
            data[nomor - 1] = tampil
        else:
            data.insert(nomor - 1, tampil)
            per_tanggal = petakan_sheet(sheet, data)[0]
        terisi.add(tgl)
        url_terpakai.add(berita.url)
        hasil["ditulis"] += 1

    if disisipkan:
        nomori_ulang(sheet, ws, cetak)
    return hasil


def nomori_ulang(sheet, ws, cetak=print):
    """Menyusun ulang kolom No setelah penyisipan baris.

    Dilewati bila kolom No berisi rumus atau berada di kolom tanggal.
    """
    if sheet.kol_tanggal == 1:
        return
    kolom = indeks_ke_kolom(1)
    awal = sheet.baris_pertama
    rumus = ws.get(f"{kolom}{awal}:{kolom}", value_render_option="FORMULA")
    if any(str(r[0]).startswith("=") for r in rumus if r):
        return

    tanggal = ws.get(f"{indeks_ke_kolom(sheet.kol_tanggal)}{awal}:"
                     f"{indeks_ke_kolom(sheet.kol_tanggal)}")
    nomor, nilai = 0, []
    for r in tanggal:
        if r and r[0].strip():
            nomor += 1
            nilai.append([nomor])
        else:
            nilai.append([""])
    if nilai:
        ws.update(range_name=f"{kolom}{awal}:{kolom}{awal + len(nilai) - 1}",
                  values=nilai, value_input_option="USER_ENTERED")
        cetak(f"Kolom No disusun ulang ({nomor} baris).")