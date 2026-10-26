"""Penentuan dampak berita secara otomatis berbasis kamus kata (rule-based).

Keluaran salah satu dari empat label ODON:
meningkatkan_ntb, menurunkan_ntb, meningkatkan_harga, menurunkan_harga.

Langkah:
1. Tentukan JENIS dampak (NTB atau Harga) dari banyaknya penanda harga
   (harga, tarif, inflasi, pasar murah, ...) dibanding penanda aktivitas
   ekonomi (produksi, pembangunan, panen, kunjungan, ...).
2. Tentukan ARAH (meningkatkan/menurunkan):
   - Harga: frasa khusus dulu (operasi pasar = menurunkan harga, kelangkaan =
     meningkatkan harga), lalu kata arah yang berdekatan dengan kata harga.
   - NTB: jumlah bobot kata "naik" (pembangunan, panen, peresmian, ...) dibanding
     kata "turun" (banjir, terhambat, gagal panen, ...). Seri -> meningkatkan,
     karena sebagian besar berita ekonomi daerah bersifat menambah aktivitas.
Judul diberi bobot dua kali isi karena paling mewakili pokok berita.
"""

import re

# ---------------------------------------------------------------------------
# Kamus. Format: (pola regex, bobot). Pola dicocokkan pada teks huruf kecil.
# ---------------------------------------------------------------------------

PENANDA_HARGA = [
    (r"\bharga\b", 3), (r"\binflasi\b", 3), (r"\bdeflasi\b", 3), (r"\btarif\b", 2),
    (r"\bmahal\b", 2), (r"\bmurah\b", 2), (r"\bongkos\b", 2), (r"\bhet\b", 2),
    (r"biaya (?:angkut|logistik|hidup|pengiriman)", 2), (r"\bihk\b", 3),
    (r"\bsphp\b", 3), (r"operasi pasar", 3), (r"pasar murah", 3),
    (r"(?:pangan|sembako) murah", 3), (r"stabilisasi harga", 3),
    (r"\blangka\b|kelangkaan", 2), (r"daya beli", 1), (r"\btpid\b", 3),
]

PENANDA_NTB = [
    (r"produksi|memproduksi", 2), (r"\bpanen", 2), (r"pembangunan|dibangun|membangun", 2),
    (r"\bproyek\b", 2), (r"investasi|investor", 2), (r"realisasi", 1),
    (r"kunjungan|wisatawan|pengunjung", 2), (r"penerbangan|penumpang", 2),
    (r"beroperasi|operasional", 1), (r"peresmian|resmikan", 2),
    (r"ekspor", 2), (r"penyaluran|disalurkan|menyalurkan", 1), (r"kapasitas", 1),
    (r"\bjalan\b|jembatan|bandara|pelabuhan|gudang|pabrik|bendungan|irigasi", 1),
    (r"tambang|batu bara|batubara", 2), (r"\bumkm\b|pelaku usaha", 1),
    (r"tenaga kerja|lapangan kerja|perekrutan", 1), (r"\btanam\b|penanaman", 2),
    (r"pengiriman|bongkar muat|distribusi", 1), (r"anggaran|apbd|belanja", 1),
]

# Frasa harga yang sudah pasti arahnya
HARGA_TURUN_KHUSUS = [
    (r"operasi pasar", 4), (r"pasar murah", 4), (r"(?:pangan|sembako|beras) murah", 4),
    (r"stabilisasi harga|menstabilkan harga|mengendalikan (?:harga|inflasi)", 3),
    (r"\bsphp\b", 3), (r"subsidi ongkos angkut|\bsoa\b", 3), (r"harga (?:\w+ ){0,3}turun", 3),
    (r"penurunan harga|harga (?:\w+ ){0,3}(?:anjlok|merosot)", 4), (r"deflasi", 3),
    (r"inflasi (?:\w+ ){0,4}(?:terkendali|rendah|melandai|turun)", 3),
    (r"(?:turun|menurun)kan (?:harga|tarif)", 4),
    (r"pasokan (?:\w+ ){0,4}(?:aman|melimpah|cukup)", 2), (r"diskon|potongan harga", 3),
]
HARGA_NAIK_KHUSUS = [
    (r"kelangkaan|\blangka\b", 4), (r"lonjakan harga|harga (?:\w+ ){0,3}melonjak", 4),
    (r"kenaikan (?:harga|tarif)", 4), (r"harga (?:\w+ ){0,3}naik", 3),
    (r"\bmahal\b|kemahalan", 3), (r"inflasi (?:\w+ ){0,4}(?:naik|tinggi|meningkat)", 3),
    (r"(?:naik|menaik)kan (?:harga|tarif)", 4), (r"\btembus\b|menembus", 2),
    (r"pasokan (?:\w+ ){0,4}(?:terbatas|berkurang|terganggu|tersendat)", 3),
    (r"biaya (?:\w+ ){0,2}(?:tinggi|membengkak)", 2),
]

# Kata arah umum (dipakai untuk NTB dan sebagai cadangan untuk harga)
ARAH_NAIK = [
    (r"\bnaik\b|kenaikan", 2), (r"meningkat|peningkatan|ditingkatkan", 2),
    (r"bertambah|penambahan|menambah", 2), (r"melonjak|lonjakan", 2),
    (r"\btumbuh\b|pertumbuhan|bertumbuh", 2), (r"surplus", 2), (r"menguat", 1),
    (r"pembangunan|dibangun|membangun", 2), (r"peresmian|resmikan", 3),
    (r"beroperasi|mulai operasi|dibuka|pembukaan|membuka", 2), (r"panen raya", 3),
    (r"realisasi|terealisasi", 1), (r"penyaluran|disalurkan|menyalurkan|bantuan", 2),
    (r"investasi", 2), (r"perluasan|ekspansi|pengembangan", 2),
    (r"rehabilitasi|perbaikan|peningkatan jalan", 1), (r"percepatan", 1),
    (r"rekor|tertinggi", 2), (r"\bramai\b|membludak|padat", 2), (r"festival|pameran|expo", 2),
    (r"hibah", 1), (r"\bbaru\b", 1), (r"tanam perdana|penanaman|penebaran|tebar benih", 2),
    (r"lancar|kembali normal|pulih", 2), (r"ekspor", 1),
]
ARAH_TURUN = [
    (r"\bturun\b|penurunan|menurun", 2), (r"merosot|anjlok|terjun bebas", 3),
    (r"berkurang|pengurangan|mengurangi", 2), (r"melemah|pelemahan", 2), (r"defisit", 2),
    (r"banjir", 3), (r"longsor", 3), (r"kebakaran|karhutla", 3), (r"kekeringan|kemarau", 2),
    (r"\brusak\b|kerusakan", 2), (r"terputus|\bputus\b", 3), (r"terhambat|hambatan|kendala", 2),
    (r"terganggu|gangguan", 2), (r"ditutup|penutupan|tutup", 2), (r"terhenti|berhenti|mangkrak", 3),
    (r"mogok", 3), (r"gagal panen|\bpuso\b", 4), (r"\bhama\b|wabah|\bpmk\b", 2),
    (r"pemangkasan|efisiensi anggaran|pemotongan anggaran", 3), (r"ditunda|penundaan", 2),
    (r"\bsepi\b|lesu", 3), (r"pemadaman|byarpet", 3), (r"kelangkaan|\blangka\b", 2),
    (r"\bphk\b|pemutusan hubungan kerja", 3), (r"dibatalkan|pembatalan", 2),
    (r"tenggelam|kecelakaan", 1), (r"cuaca buruk|gelombang tinggi", 2),
]

PENYANGKAL = r"(?:tidak|tak|belum|bukan|tanpa)\s+(?:\w+\s+)?$"

LABEL = {
    ("ntb", "naik"): "meningkatkan_ntb",
    ("ntb", "turun"): "menurunkan_ntb",
    ("harga", "naik"): "meningkatkan_harga",
    ("harga", "turun"): "menurunkan_harga",
}


def _hitung(teks, kamus, catatan=None):
    """Menjumlahkan bobot pola yang muncul, mengabaikan yang didahului penyangkal."""
    total = 0
    for pola, bobot in kamus:
        for m in re.finditer(pola, teks):
            awal = teks[max(0, m.start() - 20):m.start()]
            if re.search(PENYANGKAL, awal):
                continue
            total += bobot
            if catatan is not None:
                catatan.append(m.group(0))
    return total


def _skor(judul, isi, kamus, catatan=None):
    return 2 * _hitung(judul, kamus, catatan) + _hitung(isi, kamus, catatan)


def _jendela_harga(teks, lebar=60):
    """Potongan teks di sekitar kata harga/tarif/inflasi untuk membaca arah harga."""
    potongan = []
    for m in re.finditer(r"\bharga\b|\btarif\b|\binflasi\b|\bongkos\b|\bbiaya\b", teks):
        potongan.append(teks[max(0, m.start() - lebar):m.end() + lebar])
    return " ".join(potongan)


def tebak_dampak(judul, ringkasan=""):
    """Mengembalikan (kode_dampak, keyakinan 0-1, alasan singkat)."""
    judul = (judul or "").lower()
    isi = (ringkasan or "").lower()

    # 1. Jenis dampak
    skor_harga = _skor(judul, isi, PENANDA_HARGA)
    skor_ntb = _skor(judul, isi, PENANDA_NTB)
    harga_di_judul = _hitung(judul, PENANDA_HARGA) > 0
    jenis = "harga" if (skor_harga > skor_ntb or (harga_di_judul and skor_harga >= 3)) else "ntb"

    # 2. Arah dampak
    bukti = []
    if jenis == "harga":
        naik = _skor(judul, isi, HARGA_NAIK_KHUSUS, bukti)
        turun = _skor(judul, isi, HARGA_TURUN_KHUSUS, bukti)
        if naik == turun:
            jendela_j, jendela_i = _jendela_harga(judul), _jendela_harga(isi)
            naik += _skor(jendela_j, jendela_i, ARAH_NAIK[:6], bukti)
            turun += _skor(jendela_j, jendela_i, ARAH_TURUN[:6], bukti)
    else:
        naik = _skor(judul, isi, ARAH_NAIK, bukti)
        turun = _skor(judul, isi, ARAH_TURUN, bukti)

    arah = "turun" if turun > naik else "naik"
    total = naik + turun
    keyakinan = round(abs(naik - turun) / total, 2) if total else 0.0
    # Jenis yang tipis bedanya juga menurunkan keyakinan
    if abs(skor_harga - skor_ntb) <= 2:
        keyakinan = round(keyakinan * 0.7, 2)

    unik = list(dict.fromkeys(bukti))[:6]
    alasan = f"{jenis}: naik {naik} vs turun {turun}" + (f" ({', '.join(unik)})" if unik else "")
    return LABEL[(jenis, arah)], keyakinan, alasan
