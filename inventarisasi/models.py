from django.db import models

from core.models import Kategori, Pengguna, Periode


class OPD(models.Model):
    class Jenis(models.TextChoices):
        OPD = "opd", "OPD"
        PELAKU_USAHA = "pelaku_usaha", "Pelaku Usaha"
        SURVEI = "survei", "Survei BPS"

    class Orientasi(models.TextChoices):
        KOLOM = "kolom", "Periode di kolom (indikator per baris)"
        BARIS = "baris", "Periode di baris (indikator per kolom)"
        KOLOM_BERTAHUN = "kolom_bertahun", "Periode di kolom, tahun sebagai baris pemisah"

    nama = models.CharField(max_length=150)
    singkatan = models.CharField(max_length=30, blank=True)
    jenis = models.CharField(max_length=20, choices=Jenis.choices, default=Jenis.OPD)
    nama_pic = models.CharField(max_length=100, blank=True)
    kontak_pic = models.CharField(max_length=100, blank=True)
    petugas = models.ForeignKey(Pengguna, on_delete=models.SET_NULL, null=True, blank=True)
    is_aktif = models.BooleanField(default=True, verbose_name="Aktif")

    url_spreadsheet = models.URLField(max_length=255, blank=True)
    id_spreadsheet = models.CharField(
        max_length=100, blank=True,
        help_text="Bagian alamat setelah /d/ dan sebelum /edit"
    )
    gid_sheet = models.CharField(
        max_length=30, blank=True, default="0", verbose_name="GID sheet",
        help_text="Angka setelah #gid= pada alamat spreadsheet"
    )
    gid_tambahan = models.CharField(
        max_length=255, blank=True,
        verbose_name="GID sheet tahun lain",
        help_text="Wajib format gid:tahun, dipisah koma. Contoh: 1243746124:2025, 998877:2024. "
                  "Tahun tidak boleh dihilangkan."
    )
    orientasi = models.CharField(
        max_length=20, choices=Orientasi.choices, default=Orientasi.KOLOM
    )
    baris_tahun = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Nomor baris berisi tahun (orientasi kolom)"
    )
    baris_periode = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Nomor baris berisi Triwulan I/II/III/IV (orientasi kolom)"
    )
    kolom_periode = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Nomor kolom berisi I/II/III/IV (orientasi baris)"
    )
    baris_pertama = models.PositiveSmallIntegerField(null=True, blank=True)
    baris_terakhir = models.PositiveSmallIntegerField(null=True, blank=True)
    tahun_data = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Diisi bila sheet hanya memuat satu tahun"
    )
    kolom_label = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Nomor kolom berisi nama baris/tahun (orientasi kolom bertahun)"
    )

    class Meta:
        db_table = "m_opd"
        verbose_name = "Sumber Data"
        verbose_name_plural = "Sumber Data"
        ordering = ["nama"]

    def __str__(self):
        return self.singkatan or self.nama

    @property
    def pemetaan(self):
        return self.pemetaan_untuk(self.gid_sheet or "0", self.tahun_data)

    def pemetaan_untuk(self, gid, tahun):
        return {
            "gid": gid,
            "orientasi": self.orientasi,
            "baris_tahun": self.baris_tahun,
            "baris_periode": self.baris_periode,
            "kolom_periode": self.kolom_periode,
            "baris_pertama": self.baris_pertama,
            "baris_terakhir": self.baris_terakhir,
            "tahun": tahun,
        }

    @property
    def daftar_sheet(self):
        """Seluruh pasangan (gid, tahun) yang perlu ditarik."""
        hasil = [(self.gid_sheet or "0", self.tahun_data)]
        for bagian in self.gid_tambahan.split(","):
            bagian = bagian.strip()
            if not bagian:
                continue
            gid, _, tahun = bagian.partition(":")
            hasil.append((gid.strip(), int(tahun) if tahun.strip().isdigit() else None))
        return hasil


class Indikator(models.Model):
    """Satu baris data yang ditarik dari spreadsheet sumber."""

    komponen = models.ForeignKey(Kategori, on_delete=models.CASCADE, related_name="indikator")
    opd = models.ForeignKey(OPD, on_delete=models.RESTRICT, related_name="indikator")
    nama = models.CharField(max_length=200, help_text="Contoh: Produksi air, Volume sampah ditangani")
    frasa = models.CharField(
        max_length=200, blank=True,
        help_text="Frasa untuk narasi, contoh: volume sampah yang ditangani"
    )
    satuan = models.CharField(max_length=30, blank=True)
    sel_sumber = models.CharField(
        max_length=100, blank=True, verbose_name="Nomor baris/kolom pada sheet",
        help_text="Nomor baris bila orientasi kolom, atau nomor kolom bila orientasi baris"
    )
    urutan = models.PositiveSmallIntegerField(default=0)
    is_aktif = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        db_table = "m_indikator"
        verbose_name = "Indikator"
        verbose_name_plural = "Indikator"
        ordering = ["komponen", "opd", "urutan", "nama"]

    def __str__(self):
        return f"{self.nama} ({self.opd})"


class NilaiIndikator(models.Model):
    indikator = models.ForeignKey(Indikator, on_delete=models.CASCADE, related_name="nilai")
    periode = models.ForeignKey(Periode, on_delete=models.RESTRICT, related_name="nilai_indikator")
    nilai = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    catatan = models.CharField(max_length=255, blank=True)
    sumber_input = models.CharField(max_length=15, default="manual")
    dibuat_oleh = models.ForeignKey(Pengguna, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "t_nilai_indikator"
        verbose_name = "Nilai Indikator"
        verbose_name_plural = "Nilai Indikator"
        ordering = ["indikator", "-periode__tahun", "-periode__triwulan"]
        constraints = [
            models.UniqueConstraint(fields=["indikator", "periode"], name="uniq_indikator_periode")
        ]

    def __str__(self):
        return f"{self.indikator} - {self.periode}"