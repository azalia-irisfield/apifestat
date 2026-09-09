from django.db import models

from berita.models import Berita
from core.models import Kategori, Pengguna, Periode
from inventarisasi.models import Indikator


class Fenomena(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        FINAL = "final", "Final"

    periode = models.ForeignKey(Periode, on_delete=models.RESTRICT, related_name="fenomena")
    kategori = models.ForeignKey(Kategori, on_delete=models.RESTRICT, related_name="fenomena")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    disusun_oleh = models.ForeignKey(Pengguna, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "t_fenomena"
        verbose_name = "Fenomena"
        verbose_name_plural = "Fenomena"
        ordering = ["periode", "kategori__urutan"]
        constraints = [
            models.UniqueConstraint(fields=["periode", "kategori"], name="uniq_periode_kategori")
        ]

    def __str__(self):
        return f"{self.kategori.kode} - {self.periode}"

    def rincian(self, jenis):
        obj, _ = FenomenaRincian.objects.get_or_create(fenomena=self, jenis=jenis)
        return obj

    @property
    def terisi(self):
        return self.rincian_set.exclude(narasi="").exists()


class FenomenaRincian(models.Model):
    """Satu baris pada template: satu jenis pertumbuhan untuk satu komponen."""

    class Jenis(models.TextChoices):
        QTOQ = "qtoq", "q-to-q"
        YOY = "yoy", "y-o-y"
        CTOC = "ctoc", "c-to-c"

    KODE_TEMPLATE = {"qtoq": "q-to-q", "yoy": "y-o-y", "ctoc": "c-to-c"}

    fenomena = models.ForeignKey(Fenomena, on_delete=models.CASCADE, related_name="rincian_set")
    jenis = models.CharField(max_length=10, choices=Jenis.choices)
    angka = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                verbose_name="Angka pertumbuhan (%)")
    data_dasar = models.TextField(blank=True)
    data_pendukung = models.TextField(blank=True)
    indikator_teks = models.TextField(blank=True, verbose_name="Indikator")
    narasi = models.TextField(blank=True, verbose_name="Fenomena")

    class Meta:
        db_table = "t_fenomena_rincian"
        verbose_name = "Rincian Fenomena"
        verbose_name_plural = "Rincian Fenomena"
        constraints = [
            models.UniqueConstraint(fields=["fenomena", "jenis"], name="uniq_fenomena_jenis")
        ]

    def __str__(self):
        return f"{self.fenomena} [{self.get_jenis_display()}]"


class FenomenaBerita(models.Model):
    fenomena = models.ForeignKey(Fenomena, on_delete=models.CASCADE)
    berita = models.ForeignKey(Berita, on_delete=models.CASCADE)
    jenis = models.CharField(max_length=10, blank=True,
                             help_text="Kosongkan bila berlaku untuk semua jenis pertumbuhan")
    urutan = models.PositiveSmallIntegerField(default=0)
    kutipan = models.TextField(blank=True)

    class Meta:
        db_table = "r_fenomena_berita"
        verbose_name = "Berita Fenomena"
        verbose_name_plural = "Berita Fenomena"
        constraints = [
            models.UniqueConstraint(fields=["fenomena", "berita", "jenis"],
                                    name="uniq_fenomena_berita")
        ]


class FenomenaIndikator(models.Model):
    fenomena = models.ForeignKey(Fenomena, on_delete=models.CASCADE)
    indikator = models.ForeignKey(Indikator, on_delete=models.CASCADE)
    jenis = models.CharField(max_length=10, blank=True)
    urutan = models.PositiveSmallIntegerField(default=0)
    catatan = models.TextField(blank=True)

    class Meta:
        db_table = "r_fenomena_indikator"
        verbose_name = "Indikator Fenomena"
        verbose_name_plural = "Indikator Fenomena"