"""Klasifikasi kategori PDRB dan dampak berita menggunakan Gemini.

- Satu berita boleh mendapat beberapa kategori (Lapangan Usaha dan/atau
  Pengeluaran), dipilih dari tabel kategori di database.
- Satu kategori Lapangan Usaha ditandai sebagai kategori utama (dipakai ODON),
  dengan skor_otomatis lebih tinggi dari kategori pendukung.
- Dampak dipilih dari empat label ODON.
- Bila GEMINI_API_KEY kosong atau Gemini gagal, sistem memakai kamus kata kunci
  dan kamus dampak sebagai cadangan agar proses harian tetap berjalan.
"""

import json
import logging
import re
import time

from django.conf import settings

from berita.models import Berita, BeritaKategori
from berita.services.dampak import tebak_dampak
from core.models import Kategori

log = logging.getLogger(__name__)

UKURAN_KELOMPOK = 10     # berita per permintaan Gemini
JEDA_PERMINTAAN = 4      # detik antarpermintaan, aman untuk kuota gratis
MAKS_KATEGORI = 4
SKOR_UTAMA = 10
SKOR_PENDUKUNG = 5

DAMPAK_SAH = [k for k, _ in Berita.Dampak.choices]

INSTRUKSI = """Anda adalah analis Neraca Wilayah BPS Kabupaten Malinau. Tugas Anda
mengklasifikasikan berita ekonomi untuk mendukung penyusunan PDRB triwulanan.

Untuk setiap berita, tentukan:
1. "kategori": daftar kode kategori PDRB yang relevan (0 sampai {maks} kode), hanya
   dari DAFTAR KATEGORI di bawah. Pilih kode paling spesifik yang tepat (misalnya
   A.1.a untuk padi, bukan hanya A). Berita boleh berkategori Lapangan Usaha dan
   Pengeluaran sekaligus. Kosongkan bila berita tidak berkaitan dengan aktivitas
   ekonomi (misalnya kriminal, politik murni, olahraga).
2. "kategori_utama": satu kode Lapangan Usaha (sektoral) yang paling menjadi pokok
   berita, harus salah satu dari "kategori". Isi "" bila tidak ada kode sektoral.
3. "dampak": pengaruh peristiwa terhadap perekonomian Malinau, salah satu dari:
   - meningkatkan_ntb : menambah volume produksi/aktivitas riil (pembangunan,
     panen, peresmian, kunjungan wisatawan naik, penyaluran bantuan, investasi)
   - menurunkan_ntb   : mengurangi produksi/aktivitas riil (banjir, longsor, jalan
     putus, gagal panen, usaha tutup, pemangkasan anggaran, aktivitas terhenti)
   - meningkatkan_harga : mendorong kenaikan harga/tarif/biaya (kelangkaan, pasokan
     terganggu, kenaikan tarif, harga melonjak)
   - menurunkan_harga : menekan harga/tarif/biaya (operasi pasar, pasar murah,
     subsidi ongkos angkut, pasokan melimpah, harga turun)
   Pilih jenis Harga hanya bila pokok berita memang tentang harga/tarif/biaya;
   selain itu pilih jenis NTB.
4. "relevansi": angka 0-3, seberapa layak berita dijadikan fenomena pendukung PDRB
   KABUPATEN MALINAU. Nilailah ketat; nilai 3 hanya untuk berita yang benar-benar kuat.
   - 3 : peristiwa ekonomi nyata DI MALINAU yang mengubah produksi/aktivitas usaha,
         harga, investasi, atau belanja, idealnya disertai angka (panen, produksi
         tambang, harga komoditas, proyek fisik berjalan, kunjungan wisatawan,
         gangguan pasokan, bencana yang menghentikan usaha)
   - 2 : berita ekonomi di Malinau yang dampaknya belum langsung atau belum terukur
         (rencana, kebijakan, usulan anggaran, event yang akan datang); ATAU peristiwa
         di daerah lain yang jelas berdampak langsung ke Malinau (misalnya pasokan BBM
         atau barang ke Malinau, jalan penghubung ke Malinau)
   - 1 : hanya menyinggung ekonomi (pengumuman layanan, jadwal/tarif angkutan rutin,
         pemadaman listrik terjadwal, pelatihan, rapat, kunjungan pejabat, kisah
         perorangan); ATAU berita ekonomi kabupaten/kota lain (Bulungan, Tarakan,
         Nunukan, Tana Tidung) yang tidak berdampak langsung ke Malinau
   - 0 : bukan berita ekonomi: kriminal (pencurian, curanmor, narkoba, penipuan)
         meskipun menyebut barang atau usaha, kecelakaan, orang hilang, satwa liar,
         prakiraan cuaca, organisasi/olahraga, politik, pendidikan/kesehatan tanpa
         sisi ekonomi. Untuk relevansi 0, kosongkan "kategori".
5. "alasan": satu kalimat singkat (maks 20 kata) dasar pilihan Anda.

DAFTAR KATEGORI (kode - nama):
{kategori}
"""

SKEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "STRING"},
            "kategori": {"type": "ARRAY", "items": {"type": "STRING"}},
            "kategori_utama": {"type": "STRING"},
            "dampak": {"type": "STRING", "enum": DAMPAK_SAH},
            "relevansi": {"type": "INTEGER"},
            "alasan": {"type": "STRING"},
        },
        "required": ["id", "kategori", "kategori_utama", "dampak", "relevansi", "alasan"],
    },
}


def daftar_model():
    """Model utama lalu model cadangan, tanpa duplikat."""
    utama = getattr(settings, "GEMINI_MODEL", "") or "gemini-flash-latest"
    cadangan = getattr(settings, "GEMINI_MODEL_CADANGAN", "") or "gemini-flash-lite-latest"
    return list(dict.fromkeys([utama, cadangan]))


# Pembatas relevansi berbasis judul untuk pola yang jelas, karena Gemini
# kadang tetap memberi nilai tinggi meski instruksinya melarang.
POLA_BUKAN_EKONOMI = re.compile(
    r"curanmor|\bmaling\b|pencuri|pencurian|\bbegal\b|narkoba|sabu|penipuan|"
    r"pembunuhan|penganiayaan|ditangkap|diamankan polisi|\bdpo\b|prakiraan cuaca|"
    r"\bbmkg\b.*cuaca|orang hilang|ditemukan meninggal|tenggelam", re.I)
POLA_RUTIN = re.compile(
    r"jadwal (?:bus|damri|kapal|feri|speedboat|pesawat|penerbangan)|cek jadwal|"
    r"jadwal dan tarif|mati lampu|pemadaman listrik|info pemadaman", re.I)


def batasi_relevansi(judul, relevansi):
    """Menurunkan relevansi untuk berita kriminal/cuaca (0) dan informasi rutin (maks 1)."""
    if relevansi is None:
        return None
    if POLA_BUKAN_EKONOMI.search(judul or ""):
        return 0
    if POLA_RUTIN.search(judul or ""):
        return min(relevansi, 1)
    return relevansi


def gemini_tersedia():
    return bool(getattr(settings, "GEMINI_API_KEY", ""))


def peta_kategori():
    """Kode -> objek Kategori aktif (kode sektoral dan pengeluaran tidak bentrok)."""
    return {k.kode: k for k in Kategori.objects.filter(is_aktif=True)
            .exclude(kode__startswith="TOTAL").order_by("jenis", "urutan")}


def daftar_kategori_teks(peta):
    baris = []
    for k in peta.values():
        jenis = "Lapangan Usaha" if k.jenis == Kategori.Jenis.SEKTORAL else "Pengeluaran"
        baris.append(f"{k.kode} - {k.nama} [{jenis}]")
    return "\n".join(baris)


def tanya_gemini(item, peta):
    """item: daftar dict {id, judul, teks}. Mengembalikan dict id -> hasil mentah."""
    from google import genai
    from google.genai import types

    klien = genai.Client(api_key=settings.GEMINI_API_KEY)
    instruksi = INSTRUKSI.format(maks=MAKS_KATEGORI, kategori=daftar_kategori_teks(peta))
    hasil = {}

    for awal in range(0, len(item), UKURAN_KELOMPOK):
        kelompok = item[awal:awal + UKURAN_KELOMPOK]
        isi = "\n\n".join(
            f"[BERITA id={x['id']}]\nJudul: {x['judul']}\nIsi: {(x['teks'] or '')[:1500]}"
            for x in kelompok
        )
        berhasil, sibuk = False, False
        for model in daftar_model():
            for percobaan in range(3):
                try:
                    resp = klien.models.generate_content(
                        model=model,
                        contents=isi,
                        config=types.GenerateContentConfig(
                            system_instruction=instruksi,
                            response_mime_type="application/json",
                            response_schema=SKEMA,
                            temperature=0,
                        ),
                    )
                    for r in json.loads(resp.text):
                        hasil[str(r.get("id"))] = r
                    berhasil = True
                    break
                except Exception as exc:
                    pesan = str(exc)
                    # 503 = server Google sedang penuh, 429 = kuota/batas laju model ini
                    sibuk = any(k in pesan for k in ("503", "UNAVAILABLE", "429",
                                                     "RESOURCE_EXHAUSTED"))
                    log.warning("Gemini %s gagal (percobaan %s): %s",
                                model, percobaan + 1, pesan[:150])
                    if percobaan < 2:
                        time.sleep(10 * (percobaan + 1) if sibuk else 3)
            if berhasil:
                break
            # Model ini tetap gagal setelah 3 kali: coba model cadangan

        if not berhasil and sibuk:
            # Semua model penuh/kuota habis: sisa berita langsung memakai kata kunci
            log.warning("Gemini tidak tersedia saat ini, sisa berita memakai kata kunci.")
            break
        if awal + UKURAN_KELOMPOK < len(item):
            time.sleep(JEDA_PERMINTAAN)
    return hasil


def rapikan(mentah, peta):
    """Memvalidasi jawaban Gemini: buang kode asing, pastikan utama sektoral."""
    kode = []
    for k in mentah.get("kategori") or []:
        k = str(k).strip()
        if k in peta and k not in kode:
            kode.append(k)
    kode = kode[:MAKS_KATEGORI]

    utama = str(mentah.get("kategori_utama") or "").strip()
    if utama not in kode or peta[utama].jenis != Kategori.Jenis.SEKTORAL:
        utama = next((k for k in kode if peta[k].jenis == Kategori.Jenis.SEKTORAL), "")

    dampak = mentah.get("dampak")
    if dampak not in DAMPAK_SAH:
        dampak = ""
    try:
        relevansi = min(max(int(mentah.get("relevansi")), 0), 3)
    except (TypeError, ValueError):
        relevansi = None
    if relevansi == 0:
        kode, utama = [], ""
    return kode, utama, dampak, relevansi, str(mentah.get("alasan") or "")[:300]


def _simpan(berita, pasangan, dampak, catatan, relevansi=None):
    """pasangan: daftar (Kategori, skor). Mengganti kategori otomatis lama."""
    # Kategori isian petugas (skor_otomatis kosong) tidak disentuh
    berita.beritakategori_set.filter(skor_otomatis__isnull=False).delete()
    if not berita.dampak and dampak:
        berita.dampak = dampak
    berita.relevansi = relevansi
    berita.save(update_fields=["dampak", "relevansi"])
    arah = BeritaKategori.ARAH_DARI_DAMPAK.get(berita.dampak, "")
    for kategori, skor in pasangan:
        BeritaKategori.objects.get_or_create(
            berita=berita, kategori=kategori,
            defaults={"skor_otomatis": skor, "arah_dampak": arah, "catatan": catatan},
        )


def _cadangan(berita, teks):
    from berita.services.scraper import usulkan_kategori
    pasangan = usulkan_kategori(berita.judul, teks, maksimal=MAKS_KATEGORI)
    dampak, _, alasan = tebak_dampak(berita.judul, teks)
    _simpan(berita, pasangan, dampak, f"Kata kunci: {alasan}"[:300])


def klasifikasi_berita(daftar, isi=None):
    """Mengklasifikasikan daftar berita. isi: dict berita.id -> teks lengkap (opsional).

    Mengembalikan (jumlah_gemini, jumlah_cadangan).
    """
    daftar = list(daftar)
    if not daftar:
        return 0, 0
    isi = isi or {}
    teks = {b.id: isi.get(b.id) or b.ringkasan for b in daftar}

    jawaban = {}
    if gemini_tersedia():
        peta = peta_kategori()
        try:
            jawaban = tanya_gemini(
                [{"id": str(b.id), "judul": b.judul, "teks": teks[b.id]} for b in daftar], peta)
        except Exception as exc:
            log.warning("Gemini tidak dapat dipakai, beralih ke kata kunci: %s", exc)

    n_gemini = n_cadangan = 0
    for b in daftar:
        mentah = jawaban.get(str(b.id))
        if mentah is None:
            _cadangan(b, teks[b.id])
            n_cadangan += 1
            continue
        kode, utama, dampak, relevansi, alasan = rapikan(mentah, peta)
        relevansi = batasi_relevansi(b.judul, relevansi)
        if relevansi == 0:
            kode, utama = [], ""
        pasangan = [(peta[k], SKOR_UTAMA if k == utama else SKOR_PENDUKUNG) for k in kode]
        _simpan(b, pasangan, dampak, f"Gemini: {alasan}", relevansi)
        n_gemini += 1
    return n_gemini, n_cadangan