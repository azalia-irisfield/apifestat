"""Layanan pengambilan berita dari portal (SP-02 pada dokumen rancangan)."""

import re
from datetime import datetime

import feedparser
from bs4 import BeautifulSoup
from django.utils import timezone

from core.models import KataKunci, Periode
from berita.models import Berita, BeritaKategori, LogScraping

USER_AGENT = "APIFESTAT/1.0 (BPS Kabupaten Malinau; keperluan statistik internal)"


def bersihkan_html(teks):
    """Membuang tag HTML dan boilerplate WordPress dari ringkasan."""
    if not teks:
        return ""
    bersih = BeautifulSoup(teks, "html.parser").get_text(separator=" ")
    bersih = re.sub(r"The post .*? first appeared on .*?\.?$", "", bersih, flags=re.I | re.S)
    bersih = re.sub(r"\s+", " ", bersih).strip()
    return bersih[:1500]


def tentukan_periode(tanggal):
    """Mencari periode yang mencakup tanggal berita. Kosong bila tidak ada (Lainnya)."""
    return Periode.objects.filter(
        tanggal_mulai__lte=tanggal, tanggal_selesai__gte=tanggal
    ).first()


def usulkan_kategori(judul, ringkasan, maksimal=2):
    """Mencocokkan teks berita dengan kamus kata kunci, mengembalikan (kategori, skor)."""
    teks = f"{judul} {ringkasan}".lower()
    skor = {}
    for kk in KataKunci.objects.select_related("kategori").all():
        if kk.kata_kunci.lower() in teks:
            skor[kk.kategori] = skor.get(kk.kategori, 0) + kk.bobot
    urut = sorted(skor.items(), key=lambda x: x[1], reverse=True)
    return urut[:maksimal]


def ambil_dari_rss(portal, batas=20):
    """Mengambil daftar artikel dari RSS feed portal."""
    feed = feedparser.parse(portal.url_sumber, agent=USER_AGENT)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Feed tidak dapat dibaca: {feed.bozo_exception}")

    hasil = []
    for entry in feed.entries[:batas]:
        if entry.get("published_parsed"):
            tanggal = datetime(*entry.published_parsed[:6]).date()
        else:
            tanggal = timezone.localdate()
        hasil.append({
            "judul": entry.get("title", "").strip()[:300],
            "url": entry.get("link", "").strip()[:500],
            "tanggal": tanggal,
            "ringkasan": bersihkan_html(entry.get("summary", "")),
        })
    return hasil


def jalankan_scraping(portal, batas=20, pengguna=None):
    """Menjalankan SP-02 untuk satu portal dan mencatat hasilnya ke log."""
    log = LogScraping.objects.create(
        portal=portal, waktu_mulai=timezone.now(), dijalankan_oleh=pengguna
    )
    try:
        if portal.tipe_sumber != Portal.TipeSumber.RSS:
            raise NotImplementedError("Penarik HTML belum tersedia, gunakan portal bertipe RSS.")

        artikel = ambil_dari_rss(portal, batas=batas)
        log.jumlah_ditemukan = len(artikel)
        disimpan = duplikat = diabaikan = 0

        for a in artikel:
            if not sesuai_wilayah(portal, a["judul"], a["ringkasan"]):
                diabaikan += 1
                continue

            hash_konten = Berita.hitung_hash(a["judul"], a["url"])
            sudah_ada = Berita.objects.filter(url=a["url"]).exists() or \
                Berita.objects.filter(hash_konten=hash_konten).exists()
            if sudah_ada:
                duplikat += 1
                continue

            berita = Berita.objects.create(
                portal=portal,
                periode=tentukan_periode(a["tanggal"]),
                judul=a["judul"],
                url=a["url"],
                tanggal_berita=a["tanggal"],
                ringkasan=a["ringkasan"],
                hash_konten=hash_konten,
                status=Berita.Status.BARU,
                sumber_input=Berita.SumberInput.SCRAPING,
                lingkup=tentukan_lingkup(a["judul"], a["ringkasan"]),
                dibuat_oleh=pengguna,
            )

            for kategori, skor in usulkan_kategori(a["judul"], a["ringkasan"]):
                BeritaKategori.objects.create(
                    berita=berita, kategori=kategori, skor_otomatis=skor
                )
            disimpan += 1

        log.jumlah_disimpan = disimpan
        log.jumlah_duplikat = duplikat
        log.jumlah_diabaikan = diabaikan
        log.status = LogScraping.Status.SUKSES
    except Exception as exc:
        log.status = LogScraping.Status.GAGAL
        log.pesan = str(exc)[:2000]
    finally:
        log.waktu_selesai = timezone.now()
        log.save()

    return log

def sesuai_wilayah(portal, judul, ringkasan):
    """Memeriksa apakah berita menyebut wilayah yang dipantau (Malinau/Kaltara)."""
    if not portal.filter_wilayah.strip():
        return True
    teks = f"{judul} {ringkasan}".lower()
    kata = [k.strip().lower() for k in portal.filter_wilayah.split(",") if k.strip()]
    return any(k in teks for k in kata)

KATA_MALINAU = ["malinau"]
KATA_KALTARA = ["kalimantan utara", "kaltara", "tarakan", "bulungan",
                "nunukan", "tana tidung", "tanjung selor"]


def tentukan_lingkup(judul, ringkasan):
    """Menentukan apakah berita berlingkup Malinau, Kaltara, atau lainnya."""
    teks = f"{judul} {ringkasan}".lower()
    if any(k in teks for k in KATA_MALINAU):
        return Berita.Lingkup.MALINAU
    if any(k in teks for k in KATA_KALTARA):
        return Berita.Lingkup.KALTARA
    return Berita.Lingkup.LAINNYA


from berita.models import Portal  # diletakkan di bawah untuk menghindari impor melingkar