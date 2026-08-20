from django.shortcuts import render

from core.models import Kategori, Periode


def beranda(request):
    konteks = {
        "jumlah_sektoral": Kategori.objects.filter(jenis=Kategori.Jenis.SEKTORAL).count(),
        "jumlah_pengeluaran": Kategori.objects.filter(jenis=Kategori.Jenis.PENGELUARAN).count(),
        "periode_aktif": Periode.objects.filter(status=Periode.Status.AKTIF).first(),
        "daftar_kategori": Kategori.objects.filter(is_aktif=True),
    }
    return render(request, "dashboard/beranda.html", konteks)