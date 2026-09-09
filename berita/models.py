import hashlib

from django.db import models

from core.models import Kategori, Pengguna, Periode


class Portal(models.Model):
    class TipeSumber(models.TextChoices):
        RSS = "rss", "RSS Feed"
        HTML = "html", "Halaman HTML"

    nama_portal = models.CharField(max_length=100)
    url_dasar = models.URLField(max_length=255)
    url_sumber = models.URLField(max_length=255, help_text="Alamat RSS atau halaman indeks")
    tipe_sumber = models.CharField(max_length=10, choices=TipeSumber.choices, default=TipeSumber.RSS)
    konfigurasi = models.JSONField(blank=True, null=True, help_text="Selector untuk tipe HTML")
    jeda_detik = models.PositiveSmallIntegerField(default=2)
    is_aktif = models.BooleanField(default=True, verbose_name="Aktif")
    keterangan = models.TextField(blank=True)

    filter_wilayah = models.CharField(
        max_length=255, blank=True,
        default="malinau,kalimantan utara,kaltara",
        help_text="Kata kunci wilayah dipisah koma. Berita yang tidak memuat salah satunya "
                  "akan diabaikan. Kosongkan untuk menerima semua berita."
    )

    class Meta:
        db_table = "m_portal"
        verbose_name = "Portal Berita"
        verbose_name_plural = "Portal Berita"
        ordering = ["nama_portal"]

    def __str__(self):
        return self.nama_portal


class Berita(models.Model):
    class Status(models.TextChoices):
        BARU = "baru", "Baru"
        TERVERIFIKASI = "terverifikasi", "Terverifikasi"
        DITOLAK = "ditolak", "Ditolak"

    class Dampak(models.TextChoices):
        NAIK_NTB = "meningkatkan_ntb", "Meningkatkan NTB"
        TURUN_NTB = "menurunkan_ntb", "Menurunkan NTB"
        NAIK_HARGA = "meningkatkan_harga", "Meningkatkan Harga"
        TURUN_HARGA = "menurunkan_harga", "Menurunkan Harga"

    class Lingkup(models.TextChoices):
        MALINAU = "malinau", "Malinau"
        KALTARA = "kaltara", "Kaltara"
        LAINNYA = "lainnya", "Lainnya"

    lingkup = models.CharField(
        max_length=15, choices=Lingkup.choices,
        default=Lingkup.LAINNYA, db_index=True,
        help_text="Malinau diprioritaskan; Kaltara dipakai bila kategori belum ada beritanya"
    )

    class SumberInput(models.TextChoices):
        SCRAPING = "scraping", "Scraping"
        MANUAL = "manual", "Manual"

    portal = models.ForeignKey(
        Portal, on_delete=models.SET_NULL, null=True, blank=True, related_name="berita"
    )
    periode = models.ForeignKey(
        Periode, on_delete=models.RESTRICT, null=True, blank=True, related_name="berita",
        help_text="Kosongkan bila berita tidak masuk periode mana pun (Lainnya)"
    )
    judul = models.CharField(max_length=300)
    url = models.URLField(max_length=500, unique=True)
    penerbit = models.CharField(
        max_length=100, blank=True,
        help_text="Nama media asal, terisi otomatis untuk feed agregator"
    )
    tanggal_berita = models.DateField(db_index=True, verbose_name="Tanggal terbit")
    tanggal_peristiwa = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name="Tanggal peristiwa",
        help_text="Tanggal kejadian yang disebut di dalam berita. "
                  "Kosongkan bila sama dengan tanggal terbit."
    )
    ringkasan = models.TextField(blank=True)
    dampak = models.CharField(max_length=25, choices=Dampak.choices, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BARU, db_index=True)
    hash_konten = models.CharField(max_length=64, db_index=True, blank=True)
    sumber_input = models.CharField(max_length=15, choices=SumberInput.choices, default=SumberInput.SCRAPING)
    kategori = models.ManyToManyField(
        Kategori, through="BeritaKategori", related_name="berita", blank=True
    )
    dibuat_oleh = models.ForeignKey(
        Pengguna, on_delete=models.SET_NULL, null=True, blank=True, related_name="berita"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "t_berita"
        verbose_name = "Berita"
        verbose_name_plural = "Berita"
        ordering = ["-tanggal_berita", "-id"]
        indexes = [models.Index(fields=["periode", "status"], name="idx_berita_periode")]

    def __str__(self):
        return self.judul

    @staticmethod
    def hitung_hash(judul, url):
        return hashlib.sha256(f"{judul.strip().lower()}|{url.strip()}".encode()).hexdigest()
    @property
    def tanggal_acuan(self):
        """Tanggal yang dipakai untuk menentukan periode PDRB."""
        return self.tanggal_peristiwa or self.tanggal_berita

    def save(self, *args, **kwargs):
        if not self.hash_konten:
            self.hash_konten = self.hitung_hash(self.judul, self.url)
        super().save(*args, **kwargs)

    # @property
    # def dampak_gabungan(self):
    #     """Menggabungkan arah dan jenis dampak seperti format kolom Dampak pada ODON."""
    #     relasi = self.beritakategori_set.first()
    #     if not relasi or not relasi.arah_dampak or not self.jenis_dampak:
    #         return "-"
    #     return f"{relasi.get_arah_dampak_display()} {self.get_jenis_dampak_display()}"


class BeritaKategori(models.Model):
    class ArahDampak(models.TextChoices):
        MENINGKATKAN = "meningkatkan", "Meningkatkan"
        MENURUNKAN = "menurunkan", "Menurunkan"
        NETRAL = "netral", "Netral"

    ARAH_DARI_DAMPAK = {
        "meningkatkan_ntb": "meningkatkan",
        "menurunkan_ntb": "menurunkan",
        "meningkatkan_harga": "meningkatkan",
        "menurunkan_harga": "menurunkan",
    }

    berita = models.ForeignKey(Berita, on_delete=models.CASCADE)
    kategori = models.ForeignKey(Kategori, on_delete=models.RESTRICT)
    arah_dampak = models.CharField(max_length=15, choices=ArahDampak.choices, blank=True)
    skor_otomatis = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    catatan = models.TextField(blank=True)

    class Meta:
        db_table = "r_berita_kategori"
        verbose_name = "Kategori Berita"
        verbose_name_plural = "Kategori Berita"
        constraints = [
            models.UniqueConstraint(fields=["berita", "kategori"], name="uniq_berita_kategori")
        ]

    def __str__(self):
        return f"{self.berita.judul[:40]} → {self.kategori.kode}"


class LogScraping(models.Model):
    class Status(models.TextChoices):
        SUKSES = "sukses", "Sukses"
        SEBAGIAN = "sebagian", "Sebagian"
        GAGAL = "gagal", "Gagal"

    portal = models.ForeignKey(Portal, on_delete=models.SET_NULL, null=True, related_name="log")
    waktu_mulai = models.DateTimeField()
    waktu_selesai = models.DateTimeField(null=True, blank=True)
    jumlah_ditemukan = models.IntegerField(default=0)
    jumlah_disimpan = models.IntegerField(default=0)
    jumlah_duplikat = models.IntegerField(default=0)
    jumlah_diabaikan = models.IntegerField(default=0, verbose_name="Di luar wilayah")
    status = models.CharField(max_length=15, choices=Status.choices, blank=True)
    pesan = models.TextField(blank=True)
    dijalankan_oleh = models.ForeignKey(
        Pengguna, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        db_table = "t_log_scraping"
        verbose_name = "Log Scraping"
        verbose_name_plural = "Log Scraping"
        ordering = ["-waktu_mulai"]

    def __str__(self):
        return f"{self.portal} - {self.waktu_mulai:%d/%m/%Y %H:%M}"

class SheetODON(models.Model):
    """Konfigurasi tujuan pencatatan One Day One News."""

    nama = models.CharField(max_length=100, default="Sheet ODON")
    id_spreadsheet = models.CharField(max_length=100)
    gid_sheet = models.CharField(max_length=30, default="0", verbose_name="GID sheet")
    nama_tab = models.CharField(max_length=50, help_text="Nama tab, contoh: 2026")
    baris_pertama = models.PositiveSmallIntegerField(default=6)
    kol_tanggal = models.PositiveSmallIntegerField(default=2, verbose_name="Kolom waktu input")
    kol_judul = models.PositiveSmallIntegerField(default=3)
    kol_kategori = models.PositiveSmallIntegerField(default=4)
    kol_ringkasan = models.PositiveSmallIntegerField(default=5)
    kol_dampak = models.PositiveSmallIntegerField(default=6)
    kol_sumber = models.PositiveSmallIntegerField(default=7)
    kol_periode = models.PositiveSmallIntegerField(default=8)
    is_aktif = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        db_table = "m_sheet_odon"
        verbose_name = "Sheet ODON"
        verbose_name_plural = "Sheet ODON"

    def __str__(self):
        return f"{self.nama} ({self.nama_tab})"