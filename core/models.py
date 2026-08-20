import secrets

from django.db import models


def buat_token():
    """Menghasilkan token acak untuk parameter akses pada URL."""
    return secrets.token_urlsafe(32)


class Pengguna(models.Model):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        PENGGUNA = "pengguna", "Pengguna"

    nama = models.CharField(max_length=100)
    nip = models.CharField(max_length=20, unique=True)
    jabatan = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PENGGUNA)
    token_akses = models.CharField(max_length=64, unique=True, default=buat_token)
    is_aktif = models.BooleanField(default=True, verbose_name="Aktif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "m_pengguna"
        verbose_name = "Pengguna"
        verbose_name_plural = "Pengguna"
        ordering = ["nama"]

    def __str__(self):
        return f"{self.nama} ({self.get_role_display()})"


class Periode(models.Model):
    class Status(models.TextChoices):
        AKTIF = "aktif", "Aktif"
        TUTUP = "tutup", "Tutup"

    tahun = models.PositiveSmallIntegerField()
    triwulan = models.PositiveSmallIntegerField(
        help_text="1-4 untuk triwulanan, 0 untuk periode tahunan"
    )
    nama_periode = models.CharField(max_length=30)
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.AKTIF)

    class Meta:
        db_table = "m_periode"
        verbose_name = "Periode"
        verbose_name_plural = "Periode"
        ordering = ["-tahun", "-triwulan"]
        constraints = [
            models.UniqueConstraint(fields=["tahun", "triwulan"], name="uniq_tahun_triwulan")
        ]

    def __str__(self):
        return self.nama_periode


class Kategori(models.Model):
    class Jenis(models.TextChoices):
        SEKTORAL = "sektoral", "Sektoral (Lapangan Usaha)"
        PENGELUARAN = "pengeluaran", "Pengeluaran"

    jenis = models.CharField(max_length=15, choices=Jenis.choices)
    kode = models.CharField(max_length=10)
    nama = models.CharField(max_length=150)
    urutan = models.PositiveSmallIntegerField(default=0)
    is_aktif = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        db_table = "m_kategori"
        verbose_name = "Kategori PDRB"
        verbose_name_plural = "Kategori PDRB"
        ordering = ["jenis", "urutan"]
        constraints = [
            models.UniqueConstraint(fields=["jenis", "kode"], name="uniq_jenis_kode")
        ]

    def __str__(self):
        return f"{self.kode} - {self.nama}"


class KataKunci(models.Model):
    kategori = models.ForeignKey(
        Kategori, on_delete=models.CASCADE, related_name="kata_kunci"
    )
    kata_kunci = models.CharField(max_length=100)
    bobot = models.PositiveSmallIntegerField(default=1)

    class Meta:
        db_table = "m_kata_kunci"
        verbose_name = "Kata Kunci"
        verbose_name_plural = "Kata Kunci"
        ordering = ["kategori", "kata_kunci"]

    def __str__(self):
        return f"{self.kata_kunci} → {self.kategori.kode}"