from django.contrib import messages
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from berita.models import Berita
from core.models import Kategori, Periode

from .models import Fenomena, FenomenaBerita, FenomenaRincian
from .services.ekspor import isi_template
from .services.susun import gabung_usulan

from django.urls import reverse
from core.utils import catat
from django.utils import timezone

def periode_aktif(request):
    pid = request.POST.get("periode") or request.GET.get("periode", "")
    return (Periode.objects.filter(pk=pid).first() if pid
            else Periode.objects.filter(status="aktif").first()
            or Periode.objects.order_by("-tahun", "-triwulan").first())

def daftar_fenomena(request):
    periode = periode_aktif(request)
    jenis = request.GET.get("jenis", "sektoral")

    kategori = Kategori.objects.filter(
        jenis=jenis, is_aktif=True, id_template__isnull=False
    ).order_by("urutan")

    sudah = {f.kategori_id: f for f in Fenomena.objects.filter(periode=periode)} if periode else {}

    daftar = []
    for k in kategori:
        f = sudah.get(k.id)
        daftar.append({
            "kategori": k,
            "fenomena": f,
            "jumlah_narasi": f.rincian_set.exclude(narasi="").count() if f else 0,
        })

    total = len(daftar)
    selesai = sum(1 for d in daftar if d["jumlah_narasi"] == 3)

    konteks = {
        "periode": periode,
        "jenis": jenis,
        "pilihan_periode": Periode.objects.order_by("-tahun", "-triwulan"),
        "daftar": daftar,
        "total": total,
        "selesai": selesai,
        "belum": total - selesai,
        "persen": round(selesai / total * 100) if total else 0,
    }
    return render(request, "fenomena/daftar.html", konteks)


def susun_fenomena(request, pk):
    kategori = get_object_or_404(Kategori, pk=pk)
    periode = periode_aktif(request)
    if not periode:
        messages.error(request, "Belum ada periode. Tambahkan melalui admin.")
        return redirect("fenomena:daftar")

    fenomena, _ = Fenomena.objects.get_or_create(periode=periode, kategori=kategori)
    rincian = {j: fenomena.rincian(j) for j, _ in FenomenaRincian.Jenis.choices}

    if request.method == "POST":
        aksi = request.POST.get("aksi", "simpan")

        if aksi.startswith("usulan_") or aksi.startswith("ganti_"):
            mode, jenis = aksi.split("_", 1)

            terpilih = set(map(int, request.POST.getlist("berita")))
            FenomenaBerita.objects.filter(fenomena=fenomena).exclude(
                berita_id__in=terpilih).delete()
            for bid in terpilih:
                FenomenaBerita.objects.get_or_create(
                    fenomena=fenomena, berita_id=bid, jenis="")

            r = rincian[jenis]
            usulan = gabung_usulan(fenomena, jenis)

            if mode == "ganti" or not r.narasi.strip():
                r.narasi = usulan
                pesan = f"Narasi {jenis} disusun ulang dari data terbaru."
            else:
                r.narasi = (r.narasi + "\n\n" + usulan).strip()
                pesan = f"Usulan narasi {jenis} ditambahkan di bawah narasi yang ada."

            r.save()
            messages.success(request, pesan)
            return redirect(f"{request.path}?periode={periode.id}")

        for jenis, r in rincian.items():
            angka = request.POST.get(f"angka_{jenis}", "").strip().replace(",", ".")
            r.angka = angka or None
            r.data_dasar = request.POST.get(f"dasar_{jenis}", "").strip()
            r.data_pendukung = request.POST.get(f"pendukung_{jenis}", "").strip()
            r.indikator_teks = request.POST.get(f"indikator_{jenis}", "").strip()
            r.narasi = request.POST.get(f"narasi_{jenis}", "").strip()
            r.save()

        terpilih = set(map(int, request.POST.getlist("berita")))
        FenomenaBerita.objects.filter(fenomena=fenomena).exclude(berita_id__in=terpilih).delete()
        for bid in terpilih:
            FenomenaBerita.objects.get_or_create(fenomena=fenomena, berita_id=bid, jenis="")

        fenomena.status = request.POST.get("status", Fenomena.Status.DRAFT)
        fenomena.save()
        messages.success(request, "Fenomena tersimpan.")
        catat(request, "simpan", "Fenomena", fenomena.pk,
              f"{kategori.kode} {periode.nama_periode} ({fenomena.status})")
        return redirect(f"{request.path}?periode={periode.id}")

    komponen = kategori.keturunan()
    berita_relevan = Berita.objects.filter(
        status=Berita.Status.TERVERIFIKASI, periode=periode, kategori__in=komponen
    ).distinct().order_by("-tanggal_berita")

    terpilih = set(
        FenomenaBerita.objects.filter(fenomena=fenomena).values_list("berita_id", flat=True)
    )

    konteks = {
        "kategori": kategori,
        "jalur": kategori.jalur,
        "periode": periode,
        "pilihan_periode": Periode.objects.order_by("-tahun", "-triwulan"),
        "fenomena": fenomena,
        "rincian": rincian,
        "berita_relevan": berita_relevan,
        "terpilih": terpilih,
        "pilihan_status": Fenomena.Status.choices,
    }
    return render(request, "fenomena/susun.html", konteks)


def ekspor(request):
    periode = periode_aktif(request)

    if request.method == "POST":
        berkas = request.FILES.get("template")
        jenis = request.POST.get("jenis", "sektoral")
        pid = request.POST.get("periode")
        periode = get_object_or_404(Periode, pk=pid)

        if not berkas:
            messages.error(request, "Berkas template belum dipilih.")
            return redirect("fenomena:ekspor")

        try:
            buf, terisi, kosong = isi_template(berkas, periode, jenis)
        except Exception as exc:
            messages.error(request, f"Gagal memproses template: {exc}")
            return redirect("fenomena:ekspor")

        nama = (f"Fenomena_{'Lapangan_Usaha' if jenis == 'sektoral' else 'Pengeluaran'}"
                f"_MALINAU_{periode.tahun}Q{periode.triwulan}.xlsx")
        return FileResponse(buf, as_attachment=True, filename=nama)

    return render(request, "fenomena/ekspor.html", {
        "periode": periode,
        "pilihan_periode": Periode.objects.order_by("-tahun", "-triwulan"),
    })

def susun_massal(request):
    """Membuat fenomena dan mengisi usulan narasi untuk seluruh komponen sekaligus."""
    if request.method != "POST":
        return redirect("fenomena:daftar")

    periode = periode_aktif(request)
    jenis = request.POST.get("jenis", "sektoral")
    timpa = request.POST.get("timpa") == "1"

    if not periode:
        messages.error(request, "Belum ada periode aktif.")
        return redirect("fenomena:daftar")

    kategori = Kategori.objects.filter(
        jenis=jenis, is_aktif=True, id_template__isnull=False
    ).order_by("urutan")

    dibuat = diisi = dilewati = 0

    for k in kategori:
        fenomena, baru = Fenomena.objects.get_or_create(periode=periode, kategori=k)
        dibuat += baru

        for j, _ in FenomenaRincian.Jenis.choices:
            r = fenomena.rincian(j)
            if r.narasi and not timpa:
                dilewati += 1
                continue

            usulan = gabung_usulan(fenomena, j)
            if not usulan.strip():
                continue

            r.narasi = usulan
            r.save()
            diisi += 1

    messages.success(
        request,
        f"Penyusunan massal selesai. {dibuat} fenomena baru dibuat, "
        f"{diisi} narasi terisi, {dilewati} dilewati karena sudah ada isinya."
    )
    catat(request, "susun_massal", "Fenomena", None,
          f"{jenis} {periode.nama_periode}: {diisi} narasi terisi")
    return redirect(f"{reverse('fenomena:daftar')}?periode={periode.id}&jenis={jenis}")

def ekspor_pdf(request):
    """Menyiapkan tampilan cetak fenomena untuk disimpan sebagai PDF."""
    periode = periode_aktif(request)
    jenis = request.GET.get("jenis", "sektoral")

    kategori = Kategori.objects.filter(
        jenis=jenis, is_aktif=True, id_template__isnull=False
    ).order_by("urutan")

    peta = {}
    for f in Fenomena.objects.filter(
        periode=periode, kategori__jenis=jenis
    ).select_related("kategori").prefetch_related("rincian_set"):
        peta[f.kategori_id] = {r.jenis: r for r in f.rincian_set.all()}

    baris = []
    for k in kategori:
        r = peta.get(k.id, {})
        if not any(x.narasi for x in r.values()):
            continue
        baris.append({"kategori": k, "rincian": r})

    catat(request, "ekspor_pdf", "Fenomena", None,
          f"{jenis} {periode.nama_periode}: {len(baris)} komponen")

    return render(request, "fenomena/cetak.html", {
        "periode": periode,
        "jenis": jenis,
        "judul_jenis": "Lapangan Usaha" if jenis == "sektoral" else "Pengeluaran",
        "baris": baris,
        "tanggal": timezone.localdate(),
    })