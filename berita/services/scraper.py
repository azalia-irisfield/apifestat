"""Layanan pengambilan berita dari portal (SP-02 pada dokumen rancangan)."""

import re
from datetime import datetime

import feedparser
from bs4 import BeautifulSoup
from django.utils import timezone

from core.models import KataKunci, Periode
from berita.models import Berita, BeritaKategori, LogScraping

import base64
import requests

from urllib.parse import urljoin

import trafilatura
from bs4 import BeautifulSoup

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 "
              "APIFESTAT/1.0 (+BPS Kabupaten Malinau)")

def bersihkan_html(teks):
    """Membuang tag HTML dan boilerplate WordPress dari ringkasan."""
    if not teks:
        return ""
    bersih = BeautifulSoup(teks, "html.parser").get_text(separator=" ")
    bersih = re.sub(r"The post .*? first appeared on .*?\.?$", "", bersih, flags=re.I | re.S)
    bersih = re.sub(r"\s+", " ", bersih).strip()
    return bersih[:1500]

def bersihkan_judul(judul):
    """Membuang imbuhan nama penerbit di akhir judul dari feed agregator."""
    return re.sub(r"\s+-\s+[^-]{3,40}$", "", judul).strip()

def bongkar_url_google(url):
    """Membaca URL asli yang tersembunyi di dalam tautan Google News.

    Mengembalikan URL asli bila berhasil, atau URL semula bila gagal.
    """
    if "news.google.com" not in url:
        return url
    try:
        kode = url.rstrip("/").split("/")[-1].split("?")[0]
        data = base64.urlsafe_b64decode(kode + "=" * (-len(kode) % 4))
        # Cari pola http/https di dalam data biner hasil dekode
        cocok = re.search(rb"https?://[\w\-./%?=&+#~:,@!$'()*;]+", data)
        if cocok:
            asli = cocok.group(0).decode("utf-8", "ignore")
            if "google.com" not in asli and len(asli) > 15:
                return asli
    except Exception:
        pass
    return url

def ikuti_pengalihan(url, batas_waktu=8):
    """Membuka tautan Google News untuk memperoleh alamat berita aslinya."""
    if "news.google.com" not in url:
        return url
    try:
        try:
            r = requests.get(
                url_indeks,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
                },
                timeout=15,
            )
            r.raise_for_status()
        except Exception as exc:
            raise ValueError(f"Gagal membuka {url_indeks}: {exc}") from exc
        if "news.google.com" not in r.url:
            return r.url
        # Sebagian artikel dialihkan lewat JavaScript, alamatnya ada di isi halaman
        cocok = re.search(r'data-n-au="(https?://[^"]+)"', r.text)
        if cocok:
            return cocok.group(1)
    except Exception:
        pass
    return url

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

        judul_asli = entry.get("title", "").strip()
        judul = bersihkan_judul(judul_asli)
        ringkasan = bersihkan_html(entry.get("summary", ""))

        url_bersih = bongkar_url_google(entry.get("link", "").strip())
        if "news.google.com" in url_bersih:
            url_bersih = ikuti_pengalihan(url_bersih)

        if ringkasan[:60].lower() == judul_asli[:60].lower():
            ringkasan = ambil_ringkasan_asli(url_bersih)

        sumber = entry.get("source", {})
        penerbit = sumber.get("title", "") if isinstance(sumber, dict) else ""

        hasil.append({
            "judul": judul[:300],
            "url": url_bersih[:500],
            "tanggal": tanggal,
            "ringkasan": ringkasan,
            "penerbit": penerbit[:100],
        })
    return hasil

def ambil_tautan_artikel(portal, halaman_maks=1):
    """Mengumpulkan URL artikel dari halaman indeks portal berdasarkan pola URL."""
    import time

    cfg = portal.konfigurasi or {}
    pola = cfg.get("pola_artikel")
    if not pola:
        raise ValueError("Konfigurasi portal belum memuat 'pola_artikel'.")

    pola_halaman = cfg.get("pola_halaman")
    tautan, terlihat = [], set()

    for n in range(1, halaman_maks + 1):
        if n == 1:
            url_indeks = portal.url_sumber
        elif pola_halaman:
            url_indeks = pola_halaman.replace("{n}", str(n))
        else:
            break

        try:
            r = requests.get(url_indeks, headers={"User-Agent": USER_AGENT}, timeout=15)
            r.raise_for_status()
        except Exception:
            break

        sup = BeautifulSoup(r.text, "html.parser")
        for a in sup.find_all("a", href=True):
            penuh = urljoin(portal.url_dasar, a["href"]).split("#")[0]
            if re.search(pola, penuh) and penuh not in terlihat:
                terlihat.add(penuh)
                tautan.append(penuh)

        if n < halaman_maks:
            time.sleep(portal.jeda_detik)

    return tautan

def tanggal_dari_meta(html):
    """Membaca tanggal terbit dari meta tag standar bila trafilatura gagal."""
    sup = BeautifulSoup(html, "html.parser")
    for atribut, nilai in [
        ("property", "article:published_time"),
        ("name", "pubdate"),
        ("itemprop", "datePublished"),
    ]:
        tag = sup.find("meta", attrs={atribut: nilai})
        if tag and tag.get("content"):
            try:
                return datetime.strptime(tag["content"][:10], "%Y-%m-%d").date()
            except ValueError:
                continue
    return None

def ambil_artikel(url):
    """Mengekstraksi judul, tanggal, dan ringkasan dari satu halaman artikel."""
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
            },
            timeout=20,
        )
        r.raise_for_status()
        html = r.text
    except Exception:
        return None

    meta = trafilatura.extract_metadata(html)
    isi = trafilatura.extract(html, include_comments=False, include_tables=False) or ""

    judul = bersihkan_judul((meta.title if meta and meta.title else "").strip())
    if not judul:
        sup = BeautifulSoup(html, "html.parser")
        if sup.title:
            judul = sup.title.get_text().split("-")[0].strip()
    if not judul:
        return None

    tanggal = None
    if meta and meta.date:
        try:
            tanggal = datetime.strptime(meta.date[:10], "%Y-%m-%d").date()
        except ValueError:
            tanggal = None

    if tanggal is None:
        tanggal = tanggal_dari_meta(html) or timezone.localdate()

    ringkasan = re.sub(r"\s+", " ", isi).strip()
    # Buang label kanal dan pengulangan judul di awal ekstraksi
    ringkasan = re.sub(r"^Berita\s+\w+\s+Terkini\s*", "", ringkasan)
    if ringkasan.lower().startswith(judul.lower()[:50]):
        ringkasan = ringkasan[len(judul):].strip()

    return {
        "judul": judul[:300],
        "url": url[:500],
        "tanggal": tanggal,
        "ringkasan": ringkasan[:1500],
        "penerbit": (meta.sitename if meta and meta.sitename else "")[:100],
    }


def ambil_dari_html(portal, batas=20, halaman_maks=1, tanggal_minimal=None):
    """Menarik berita dari portal berbasis HTML.

    tanggal_minimal: berhenti bila sudah menemukan beberapa artikel lebih lama
    dari tanggal ini, berguna untuk penarikan arsip.
    """
    import time

    hasil = []
    terlalu_lama = 0

    for url in ambil_tautan_artikel(portal, halaman_maks):
        if len(hasil) >= batas:
            break
        if Berita.objects.filter(url=url).exists():
            continue

        artikel = ambil_artikel(url)
        time.sleep(portal.jeda_detik)

        if not artikel:
            continue

        if tanggal_minimal and artikel["tanggal"] < tanggal_minimal:
            terlalu_lama += 1
            if terlalu_lama >= 8:
                break
            continue

        terlalu_lama = 0
        hasil.append(artikel)

    return hasil

def jalankan_scraping(portal, batas=20, pengguna=None, halaman_maks=1, tanggal_minimal=None):
    """Menjalankan SP-02 untuk satu portal dan mencatat hasilnya ke log."""
    log = LogScraping.objects.create(
        portal=portal, waktu_mulai=timezone.now(), dijalankan_oleh=pengguna
    )
    try:
        if portal.tipe_sumber == Portal.TipeSumber.RSS:
            artikel = ambil_dari_rss(portal, batas=batas)
        else:
            artikel = ambil_dari_html(portal, batas=batas, halaman_maks=halaman_maks,
                tanggal_minimal=tanggal_minimal)

        log.jumlah_ditemukan = len(artikel)
        disimpan = duplikat = diabaikan = 0

        for a in artikel:
            if not sesuai_wilayah(portal, a["judul"], a["ringkasan"]):
                diabaikan += 1
                continue

            hash_konten = Berita.hitung_hash(a["judul"], a["url"])
            sudah_ada = (
                Berita.objects.filter(url=a["url"]).exists()
                or Berita.objects.filter(hash_konten=hash_konten).exists()
                or Berita.objects.filter(judul__iexact=a["judul"]).exists()
            )
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
                penerbit=a.get("penerbit", ""),
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