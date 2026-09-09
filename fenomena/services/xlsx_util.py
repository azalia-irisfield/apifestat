"""Pembaca dan penulis xlsx sederhana tanpa openpyxl.

Dipakai karena template dari BPS Provinsi memuat definisi gaya yang tidak dapat
dibaca openpyxl. Modul ini hanya menyentuh sheetData, sehingga seluruh format,
warna, dan sel tergabung pada berkas asli tetap utuh.
"""

import re
import xml.etree.ElementTree as ET
import zipfile

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NSB = "{%s}" % NS

# Karakter yang tidak diizinkan XML 1.0. Tab, LF, dan CR tetap dipertahankan.
_KENDALI = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def bersihkan_teks(nilai):
    """Membuang karakter kendali yang membuat berkas xlsx ditolak Excel."""
    teks = str(nilai).replace("\r\n", "\n").replace("\r", "\n")
    return _KENDALI.sub(" ", teks)

def _huruf(ref):
    return "".join(c for c in ref if c.isalpha())


def _angka(ref):
    return int("".join(c for c in ref if c.isdigit()))


def kolom_ke_indeks(huruf):
    n = 0
    for c in huruf.upper():
        n = n * 26 + (ord(c) - 64)
    return n


def indeks_ke_kolom(n):
    s = ""
    while n:
        n, sisa = divmod(n - 1, 26)
        s = chr(65 + sisa) + s
    return s


def _nama_sheet_pertama(z):
    for n in z.namelist():
        if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n):
            return n
    raise ValueError("Sheet tidak ditemukan di dalam berkas.")


def baca(berkas):
    """Mengembalikan dict {(baris, kolom): nilai} dari sheet pertama."""
    with zipfile.ZipFile(berkas) as z:
        try:
            akar = ET.fromstring(z.read("xl/sharedStrings.xml"))
            teks = ["".join(t.text or "" for t in si.iter(NSB + "t")) for si in akar]
        except KeyError:
            teks = []
        ws = ET.fromstring(z.read(_nama_sheet_pertama(z)))

    hasil = {}
    for row in ws.find(NSB + "sheetData"):
        for c in row:
            ref = c.get("r")
            tipe = c.get("t")
            if tipe == "inlineStr":
                el = c.find(NSB + "is")
                nilai = "".join(t.text or "" for t in el.iter(NSB + "t")) if el is not None else None
            else:
                v = c.find(NSB + "v")
                if v is None:
                    continue
                nilai = teks[int(v.text)] if tipe == "s" else v.text
            if nilai not in (None, ""):
                hasil[(_angka(ref), kolom_ke_indeks(_huruf(ref)))] = nilai
    return hasil

def _pulihkan_tag_akar(asli, hasil):
    """Mengembalikan tag pembuka <worksheet ...> apa adanya dari berkas asli.

    ElementTree membuang deklarasi namespace yang tidak dipakai elemen mana pun,
    padahal mc:Ignorable masih menyebut awalannya. Tanpa pemulihan ini Excel
    menolak berkas yang memuat lebih dari satu awalan pada mc:Ignorable,
    seperti mc:Ignorable="x14ac xr xr2 xr3".
    """
    pola = re.compile(rb"<worksheet\b[^>]*>")
    tag_asli = pola.search(asli)
    if not tag_asli:
        return hasil
    return pola.sub(tag_asli.group(0), hasil, count=1)

def _daftarkan_namespace(xml_bytes):
    """Mendaftarkan ulang seluruh awalan namespace agar tidak berubah saat ditulis.

    Tanpa ini ElementTree mengganti mc: menjadi ns1: sehingga atribut
    mc:Ignorable menunjuk awalan yang tidak ada dan berkas ditolak Excel.
    """
    kepala = xml_bytes[:4000].decode("utf-8", "ignore")
    for awalan, uri in re.findall(r'xmlns:([\w.-]+)="([^"]+)"', kepala):
        ET.register_namespace(awalan, uri)
    bawaan = re.search(r'xmlns="([^"]+)"', kepala)
    ET.register_namespace("", bawaan.group(1) if bawaan else NS)

def tulis(sumber, tujuan, perubahan):
    """Menyalin berkas sumber ke tujuan sambil menulis sel pada `perubahan`.

    perubahan: dict {(baris, kolom): nilai}. Nilai angka ditulis sebagai angka,
    selain itu sebagai teks sebaris.
    """
    with zipfile.ZipFile(sumber) as z:
        nama_sheet = _nama_sheet_pertama(z)
        isi = {n: z.read(n) for n in z.namelist()}

    _daftarkan_namespace(isi[nama_sheet])
    ws = ET.fromstring(isi[nama_sheet])
    data = ws.find(NSB + "sheetData")

    baris_ada = {_angka(r.get("r")): r for r in data if r.get("r")}
    per_baris = {}
    for (r, k), nilai in perubahan.items():
        per_baris.setdefault(r, {})[k] = nilai

    for nomor_baris, sel_baru in per_baris.items():
        row = baris_ada.get(nomor_baris)
        if row is None:
            continue

        sel_ada = {kolom_ke_indeks(_huruf(c.get("r"))): c for c in row}
        gaya_acuan = None
        for k in sorted(sel_ada):
            if sel_ada[k].get("s"):
                gaya_acuan = sel_ada[k].get("s")

        for kolom, nilai in sel_baru.items():
            ref = f"{indeks_ke_kolom(kolom)}{nomor_baris}"
            c = sel_ada.get(kolom)
            if c is None:
                c = ET.Element(NSB + "c", {"r": ref})
                if gaya_acuan:
                    c.set("s", gaya_acuan)
                posisi = sum(1 for k in sel_ada if k < kolom)
                row.insert(posisi, c)
                sel_ada[kolom] = c

            for anak in list(c):
                c.remove(anak)
            c.attrib.pop("t", None)

            if nilai is None or nilai == "":
                continue

            if isinstance(nilai, (int, float)):
                v = ET.SubElement(c, NSB + "v")
                v.text = repr(float(nilai)) if isinstance(nilai, float) else str(nilai)
            else:
                c.set("t", "inlineStr")
                el = ET.SubElement(c, NSB + "is")
                t = ET.SubElement(el, NSB + "t")
                t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                t.text = bersihkan_teks(nilai)

    # isi[nama_sheet] = ET.tostring(ws, encoding="UTF-8", xml_declaration=True)
    keluaran = ET.tostring(ws, encoding="UTF-8", xml_declaration=True)
    isi[nama_sheet] = _pulihkan_tag_akar(isi[nama_sheet], keluaran)
    isi.pop("xl/calcChain.xml", None)

    # calcChain mencatat urutan hitung rumus; setelah nilai sel diubah,
    # berkas ini bisa tidak sinkron dan membuat Excel menolak berkas.
    isi.pop("xl/calcChain.xml", None)

    with zipfile.ZipFile(tujuan, "w", zipfile.ZIP_DEFLATED) as z:
        for nama, data_bytes in isi.items():
            if nama.endswith("/"):
                continue
            z.writestr(nama, data_bytes)
    return tujuan