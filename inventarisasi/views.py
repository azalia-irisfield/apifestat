from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.models import Kategori, Periode

from .models import OPD, Indikator, NilaiIndikator
from .services.hitung import hitung_indikator, susun_narasi
from .services.sheets import tarik_dari_opd, unduh_sheet


def pohon_komponen(request):
    konteks = {
        "sektoral": Kategori.objects.filter(
            jenis="sektoral", induk__isnull=True, is_aktif=True
        ).prefetch_related("anak"),
        "pengeluaran": Kategori.objects.filter(
            jenis="pengeluaran", induk__isnull=True, is_aktif=True
        ).prefetch_related("anak"),
    }
    return render(request, "inventarisasi/pohon.html", konteks)


def detail_komponen(request, pk):
    komponen = get_object_or_404(Kategori, pk=pk)

    periode_id = request.GET.get("periode", "")
    periode = (Periode.objects.filter(pk=periode_id).first() if periode_id
               else Periode.objects.filter(status="aktif").first()
               or Periode.objects.order_by("-tahun", "-triwulan").first())

    if request.method == "POST" and periode:
        for ind in Indikator.objects.filter(komponen=komponen, is_aktif=True):
            raw = request.POST.get(f"nilai_{ind.id}", "").strip().replace(",", ".")
            nilai = None
            if raw:
                try:
                    nilai = float(raw)
                except ValueError:
                    messages.error(request, f"Nilai untuk {ind.nama} bukan angka.")
                    continue
            NilaiIndikator.objects.update_or_create(
                indikator=ind, periode=periode, defaults={"nilai": nilai}
            )
        messages.success(request, f"Data {periode.nama_periode} tersimpan.")
        return redirect(f"{request.path}?periode={periode.id}")

    hasil, per_opd = [], {}
    if periode:
        komponen_terkait = komponen.keturunan()
        for ind in Indikator.objects.filter(
            komponen__in=komponen_terkait, is_aktif=True
        ).select_related("opd", "komponen"):
            h = hitung_indikator(ind, periode)
            hasil.append(h)
            per_opd.setdefault(ind.opd, []).append(h)

    konteks = {
        "komponen": komponen,
        "jalur": komponen.jalur,
        "anak": komponen.anak.filter(is_aktif=True),
        "periode": periode,
        "pilihan_periode": Periode.objects.order_by("-tahun", "-triwulan"),
        "hasil": hasil,
        "per_opd": per_opd.items(),
        "narasi_qtoq": susun_narasi(hasil, "qtoq"),
        "narasi_yoy": susun_narasi(hasil, "yoy"),
        "narasi_ctoc": susun_narasi(hasil, "ctoc"),
    }
    return render(request, "inventarisasi/detail.html", konteks)


def tarik_sheet(request, pk):
    opd = get_object_or_404(OPD, pk=pk)
    try:
        hasil = tarik_dari_opd(opd)
        messages.success(request, f"{len(hasil)} nilai ditarik dari {opd.nama}.")
    except Exception as exc:
        messages.error(request, f"Gagal menarik data {opd.nama}: {exc}")
    return redirect(request.META.get("HTTP_REFERER") or "inventarisasi:pohon")


def pratinjau_sheet(request, pk):
    opd = get_object_or_404(OPD, pk=pk)
    baris, kolom, galat = [], [], None
    try:
        mentah = unduh_sheet(opd.id_spreadsheet, opd.gid_sheet or "0")
        lebar = min(max((len(r) for r in mentah[:25]), default=0), 20)
        baris = [(i, (r + [""] * lebar)[:lebar]) for i, r in enumerate(mentah[:25], start=1)]
        kolom = list(range(1, lebar + 1))
    except Exception as exc:
        galat = str(exc)
    return render(request, "inventarisasi/pratinjau.html",
                  {"opd": opd, "baris": baris, "kolom": kolom, "galat": galat})