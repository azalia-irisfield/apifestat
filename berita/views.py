from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import VerifikasiBeritaForm
from .models import Berita, LogScraping, Portal, Kategori, BeritaKategori
from .services.scraper import jalankan_scraping
from core.models import Kategori

from django.db.models import Q
from django.core.paginator import Paginator

from .models import SheetODON
from .services.odon import (alamat_tempel, baris_berita, baris_tersedia,
                            kirim_ke_sheet, kredensial_tersedia)

from django.http import JsonResponse
from core.utils import catat


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
        qs = qs.filter(
            Q(tanggal_peristiwa__gte=f["dari"])
            | Q(tanggal_peristiwa__isnull=True, tanggal_berita__gte=f["dari"])
        )
    if f["sampai"]:
        qs = qs.filter(
            Q(tanggal_peristiwa__lte=f["sampai"])
            | Q(tanggal_peristiwa__isnull=True, tanggal_berita__lte=f["sampai"])
        )
    if f["lingkup"]:
        qs = qs.filter(lingkup=f["lingkup"])

    qs = qs.distinct()
    jumlah_hasil = qs.count()

    paginator = Paginator(qs, 25)
    hal = paginator.get_page(request.GET.get("page"))

    daftar = list(hal.object_list)
    for b in daftar:
        b.id_kategori = [k.id for k in b.kategori.all()]

    konteks = {
        "daftar": daftar,
        "hal": hal,
        "jumlah_hasil": jumlah_hasil,
        "f": f,
        "ada_filter": any(f.values()),
        "pilihan_status": Berita.Status.choices,
        "pilihan_dampak": Berita.Dampak.choices,
        "pilihan_lingkup": Berita.Lingkup.choices,
        "pilihan_kategori": Kategori.objects.filter(
            is_aktif=True, induk__isnull=True
        ).exclude(kode__startswith="TOTAL").order_by("jenis", "urutan"),
        "portal_aktif": Portal.objects.filter(is_aktif=True),
        "log_terakhir": LogScraping.objects.first(),
        "jumlah_baru": Berita.objects.filter(status=Berita.Status.BARU).count(),
    }
    return render(request, "berita/daftar.html", konteks)


def proses_scraping(request):
    if request.method != "POST":
        return redirect("berita:daftar")

    portal_id = request.POST.get("portal")
    portal = get_object_or_404(Portal, pk=portal_id, is_aktif=True)
    batas = 5 if portal.tipe_sumber == Portal.TipeSumber.HTML else 20
    log = jalankan_scraping(portal, batas=batas)

    if log.status == LogScraping.Status.SUKSES:
        messages.success(
            request,
            f"Scraping {portal.nama_portal} selesai. Ditemukan {log.jumlah_ditemukan}, "
            f"disimpan {log.jumlah_disimpan}, duplikat {log.jumlah_duplikat}, "
            f"di luar wilayah {log.jumlah_diabaikan}."
        )
    else:
        messages.error(request, f"Scraping gagal: {log.pesan}")
    catat(request, "scraping", "Portal", portal.pk,
        f"{portal.nama_portal}: {log.jumlah_disimpan} berita disimpan")
    return redirect("berita:daftar")


def verifikasi_berita(request, pk):
    berita = get_object_or_404(Berita, pk=pk)
    if request.method == "POST":
        form = VerifikasiBeritaForm(request.POST, instance=berita)
        if form.is_valid():
            form.save()
            catat(request, "verifikasi", "Berita", berita.pk, berita.judul[:80])
            messages.success(request, "Berita berhasil disimpan.")
            return redirect("berita:daftar")
    else:
        form = VerifikasiBeritaForm(instance=berita)
    return render(request, "berita/verifikasi.html", {"form": form, "berita": berita})

def ubah_cepat(request, pk):
    """Mengubah kategori dan dampak langsung dari daftar."""
    if request.method != "POST":
        return redirect("berita:daftar")

    berita = get_object_or_404(Berita, pk=pk)
    kategori_id = request.POST.get("kategori", "")
    dampak = request.POST.get("dampak", "")

    berita.dampak = dampak
    if dampak and kategori_id:
        berita.status = Berita.Status.TERVERIFIKASI
    berita.save(update_fields=["dampak", "status", "updated_at"])

    if kategori_id:
        kategori = get_object_or_404(Kategori, pk=kategori_id)
        arah = BeritaKategori.ARAH_DARI_DAMPAK.get(dampak, "")
        berita.beritakategori_set.exclude(kategori=kategori).delete()
        BeritaKategori.objects.update_or_create(
            berita=berita, kategori=kategori, defaults={"arah_dampak": arah}
        )
    else:
        berita.beritakategori_set.all().delete()

    messages.success(request, f"Berita “{berita.judul[:50]}…” diperbarui.")
    catat(request, "ubah", "Berita", berita.pk, f"Ubah cepat: {berita.judul[:80]}")
    return redirect(request.POST.get("next") or "berita:daftar")

def pilih_baris_odon(request, pk):
    """Menampilkan baris kosong yang tersedia pada sheet ODON."""
    berita = get_object_or_404(Berita, pk=pk)
    sheet = SheetODON.objects.filter(is_aktif=True).first()

    if not sheet:
        return JsonResponse({"galat": "Sheet ODON belum diatur di menu Pengaturan."}, status=400)

    try:
        baris = baris_tersedia(sheet)
    except Exception as exc:
        return JsonResponse({"galat": str(exc)}, status=400)

    isi = baris_berita(berita)
    return JsonResponse({
        "judul": berita.judul,
        "isi": isi,
        "teks_salin": "\t".join(isi.values()),
        "baris": baris,
        "bisa_kirim": kredensial_tersedia(),
    })


def catat_odon(request, pk):
    if request.method != "POST":
        return redirect("berita:daftar")

    berita = get_object_or_404(Berita, pk=pk)
    sheet = SheetODON.objects.filter(is_aktif=True).first()
    nomor = request.POST.get("baris", "")

    if not sheet or not nomor.isdigit():
        messages.error(request, "Baris tujuan tidak sah.")
        return redirect(request.POST.get("next") or "berita:daftar")

    try:
        kirim_ke_sheet(sheet, int(nomor), berita)
        messages.success(
            request, f"Berita dicatat ke sheet ODON pada baris {nomor}."
        )
        catat(request, "catat_odon", "Berita", berita.pk, f"Baris {nomor} pada sheet ODON")
    except Exception as exc:
        messages.error(request, f"Gagal menulis ke sheet: {exc}")

    return redirect(request.POST.get("next") or "berita:daftar")