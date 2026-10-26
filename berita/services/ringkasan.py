"""Penyusun ringkasan berita secara ekstraktif (tanpa layanan AI eksternal).

Alur:
1. Bersihkan isi artikel dari "sampah" khas portal: breadcrumb, judul yang
   terulang, sub-judul, Penulis/Editor, dateline (TRIBUNKALTARA.COM, MALINAU -),
   "Baca juga", iklan.
2. Pecah menjadi kalimat (aman untuk angka 1.000 / 1,7 dan singkatan Rp., Kab.).
3. Pilih kalimat terpenting: kalimat pembuka (lead) selalu masuk, lalu 1-2
   kalimat berikutnya yang paling informatif (angka, satuan, nama wilayah),
   tetap dalam urutan aslinya, dengan batas panjang total.
"""

import re

PANJANG_MAKS = 450       # batas karakter ringkasan
KALIMAT_MAKS = 3         # batas jumlah kalimat
JENDELA_KANDIDAT = 8     # hanya kalimat-kalimat awal yang dipertimbangkan

# Dateline: "TRIBUNKALTARA.COM, MALINAU -", "MALINAU, KOMPAS.com -",
# "Malinau (ANTARA) -", "KALTARAPOS.ID, TARAKAN –"
POLA_DATELINE = re.compile(
    r"(?:^|\s)"
    r"(?:[A-Z][A-Za-z.]*\.(?:COM|CO\.ID|ID|NET|com|co\.id|id|net)"
    r"|[A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?\s*\((?:ANTARA|antara|Antaranews)\)"
    r"|[A-Z]{3,}(?:\s[A-Z]{3,})?,\s*[A-Za-z.]+\.(?:com|id|co\.id))"
    r"[^.\n]{0,40}?\s[-–—]{1,2}\s"
)

POLA_SAMPAH = [
    r"Penulis\s*:[^|]*\|\s*Editor\s*:\s*\S+(?:\s\S+){0,3}",
    r"(?:Penulis|Editor|Reporter|Pewarta|Wartawan|Laporan Wartawan[^,]*)\s*:\s*[A-Z][\w.]*(?:\s[A-Z][\w.]*){0,3}",
    r"Baca [Jj]uga\s*:?[^.!?]*[.!?]?",
    r"ADVERTISEMENT|SCROLL TO CONTINUE WITH CONTENT|Advertisement",
    r"\(\s*(?:[a-z]{2,4}/){1,3}[a-z]{2,4}\s*\)",       # kode redaksi (adv/sar/mdk)
    r"Ikuti (?:berita|kami)[^.!?]*(?:Google News|WhatsApp|Telegram)[^.!?]*[.!?]?",
]

SINGKATAN = {"rp", "kab", "kec", "prov", "no", "dr", "drs", "ir", "h", "hj",
             "st", "jl", "jln", "tbk", "pt", "cv", "dll", "dsb", "sdh", "sd",
             "smp", "sma", "spd", "sh", "se", "mm", "mt", "msi", "si", "dkk",
             "a.n", "u.p", "bpk", "ibu", "sdr", "kol", "brigjen", "kombes"}

KATA_ANGKA = re.compile(
    r"\d|persen|%|\brp\b|ribu|juta|miliar|triliun|ton|hektare|\bha\b|"
    r"unit|kilometer|\bkm\b|kg|liter", re.I)
KATA_WILAYAH = re.compile(r"malinau|kaltara|kalimantan utara", re.I)
KATA_KUTIPAN = re.compile(r"\b(?:ujar|kata|ungkap|jelas|tutur|tegas)nya\b|^[\"“]", re.I)


def _normal(teks):
    teks = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", teks or "")
    return re.sub(r"\s+", " ", teks).strip()


def bersihkan_isi(teks, judul=""):
    """Membuang bagian non-berita sehingga teks dimulai dari paragraf pertama."""
    teks = _normal(teks)
    if not teks:
        return ""

    # Mulai dari dateline bila ada di bagian awal (membuang breadcrumb,
    # judul, sub-judul, dan byline yang berada sebelum dateline)
    cocok = POLA_DATELINE.search(teks[:700])
    if cocok:
        teks = teks[cocok.end():]

    for pola in POLA_SAMPAH:
        teks = re.sub(pola, " ", teks)

    # Judul yang terulang di dalam isi
    if judul and len(judul) > 20:
        teks = re.sub(re.escape(judul.strip()), " ", teks, flags=re.I)

    return _normal(teks).lstrip("-–—: ")


def pecah_kalimat(teks):
    """Memecah teks menjadi kalimat dengan memperhatikan angka dan singkatan."""
    kalimat, mulai = [], 0
    for m in re.finditer(r"[.!?][\"”’)]*\s+(?=[\"“(]?[A-Z0-9])", teks):
        potong = teks[mulai:m.end()].strip()
        kata_akhir = re.findall(r"([\w.]+)[.!?][\"”’)]*\s*$", potong)
        akhir = kata_akhir[0].lower().rstrip(".") if kata_akhir else ""
        # Jangan memotong setelah singkatan atau inisial tunggal ("M. Supri")
        if akhir in SINGKATAN or (len(akhir) == 1 and akhir.isalpha()):
            continue
        kalimat.append(potong)
        mulai = m.end()
    sisa = teks[mulai:].strip()
    if sisa:
        kalimat.append(sisa)
    return kalimat


def _skor(kalimat, posisi):
    skor = 3.0 / (posisi + 1)                       # makin awal makin penting
    skor += min(len(KATA_ANGKA.findall(kalimat)), 3) * 0.8
    if KATA_WILAYAH.search(kalimat):
        skor += 0.7
    if KATA_KUTIPAN.search(kalimat):
        skor -= 1.0                                  # kutipan narasumber kurang padat
    if len(kalimat) < 40:
        skor -= 1.5                                  # terlalu pendek, biasanya sisa
    return skor


def buat_ringkasan(teks, judul="", panjang_maks=PANJANG_MAKS):
    """Menghasilkan ringkasan 1-3 kalimat utuh dari isi artikel."""
    isi = bersihkan_isi(teks, judul)
    if not isi:
        return ""

    kalimat = pecah_kalimat(isi)
    # Kalimat terakhir yang terpotong (isi dibatasi saat scraping) dibuang
    if len(kalimat) > 1 and not re.search(r"[.!?][\"”’)]*$", kalimat[-1]):
        kalimat = kalimat[:-1]
    kalimat = [k for k in kalimat[:JENDELA_KANDIDAT] if len(k) >= 25] or kalimat[:1]

    terpilih = [0]
    total = len(kalimat[0])
    urutan = sorted(range(1, len(kalimat)), key=lambda i: _skor(kalimat[i], i), reverse=True)
    for i in urutan:
        if len(terpilih) >= KALIMAT_MAKS:
            break
        if _skor(kalimat[i], i) <= 0:
            continue
        if total + 1 + len(kalimat[i]) <= panjang_maks:
            terpilih.append(i)
            total += 1 + len(kalimat[i])

    hasil = " ".join(kalimat[i] for i in sorted(terpilih))

    # Lead tunggal yang terlalu panjang: potong di batas kata
    if len(hasil) > panjang_maks + 150:
        hasil = hasil[:panjang_maks].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return hasil