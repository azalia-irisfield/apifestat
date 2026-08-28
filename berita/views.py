from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VerifikasiBeritaForm
from .models import Berita, LogScraping, Portal
from .services.scraper import jalankan_scraping
from core.models import Kategori


def daftar_berita(request):
    qs = Berita.objects.select_related("portal", "periode").prefetch_related("kategori")

    f = {
        "q": request.GET.get("q", "").strip(),
        "status": request.GET.get("status", ""),
        "kategori": request.GET.get("kategori", ""),
        "dampak": request.GET.get("dampak", ""),
        "dari": request.GET.get("dari", ""),
        "sampai": request.GET.get("sampai", ""),
        "lingkup": request.GET.get("lingkup", ""),
    }

    if f["q"]:
        qs = qs.filter(judul__icontains=f["q"])
    if f["status"]:
        qs = qs.filter(status=f["status"])
    if f["kategori"]:
        qs = qs.filter(kategori__id=f["kategori"])
    if f["dampak"]:
        qs = qs.filter(dampak=f["dampak"])
    if f["dari"]:
        qs = qs.filter(tanggal_berita__gte=f["dari"])
    if f["sampai"]:
        qs = qs.filter(tanggal_berita__lte=f["sampai"])
    if f["lingkup"]:
        qs = qs.filter(lingkup=f["lingkup"])

    qs = qs.distinct()

    konteks = {
        "daftar": qs[:200],
        "jumlah_hasil": qs.count(),
        "f": f,
        "ada_filter": any(f.values()),
        "pilihan_status": Berita.Status.choices,
        "pilihan_dampak": Berita.Dampak.choices,
        "pilihan_kategori": Kategori.objects.filter(is_aktif=True),
        "portal_aktif": Portal.objects.filter(is_aktif=True),
        "log_terakhir": LogScraping.objects.first(),
        "jumlah_baru": Berita.objects.filter(status=Berita.Status.BARU).count(),
        "pilihan_lingkup": Berita.Lingkup.choices,
    }
    return render(request, "berita/daftar.html", konteks)


def proses_scraping(request):
    if request.method != "POST":
        return redirect("berita:daftar")

    portal_id = request.POST.get("portal")
    portal = get_object_or_404(Portal, pk=portal_id, is_aktif=True)
    log = jalankan_scraping(portal, batas=20)

    if log.status == LogScraping.Status.SUKSES:
        messages.success(
            request,
            f"Scraping {portal.nama_portal} selesai. Ditemukan {log.jumlah_ditemukan}, "
            f"disimpan {log.jumlah_disimpan}, duplikat {log.jumlah_duplikat}, "
            f"di luar wilayah {log.jumlah_diabaikan}."
        )
    else:
        messages.error(request, f"Scraping gagal: {log.pesan}")
    return redirect("berita:daftar")


def verifikasi_berita(request, pk):
    berita = get_object_or_404(Berita, pk=pk)
    if request.method == "POST":
        form = VerifikasiBeritaForm(request.POST, instance=berita)
        if form.is_valid():
            form.save()
            messages.success(request, "Berita berhasil disimpan.")
            return redirect("berita:daftar")
    else:
        form = VerifikasiBeritaForm(instance=berita)
    return render(request, "berita/verifikasi.html", {"form": form, "berita": berita})