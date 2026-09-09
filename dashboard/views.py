from datetime import date

from django.db.models import Count, Q
from django.shortcuts import render

from berita.models import Berita
from core.models import Kategori, Periode
from fenomena.models import Fenomena
from inventarisasi.models import OPD, Indikator, NilaiIndikator


def beranda(request):
    pid = request.GET.get("periode", "")
    periode = (Periode.objects.filter(pk=pid).first() if pid
               else Periode.objects.filter(status="aktif").first()
               or Periode.objects.order_by("-tahun", "-triwulan").first())

    konteks = {
        "periode": periode,
        "pilihan_periode": Periode.objects.order_by("-tahun", "-triwulan"),
    }
    if not periode:
        return render(request, "dashboard/beranda.html", konteks)

    # ---------- angka kunci ----------
    berita_periode = Berita.objects.filter(periode=periode)
    menunggu = berita_periode.filter(status=Berita.Status.BARU).count()

    komponen_utama = Kategori.objects.filter(
        is_aktif=True, id_template__isnull=False
    ).exclude(kode__startswith="TOTAL")

    total_komponen = komponen_utama.count()
    fenomena_lengkap = sum(
        1 for f in Fenomena.objects.filter(periode=periode).prefetch_related("rincian_set")
        if f.rincian_set.exclude(narasi="").count() == 3
    )

    opd_aktif = OPD.objects.filter(is_aktif=True)
    opd_terisi = (
        opd_aktif.annotate(
            n=Count("indikator__nilai", filter=Q(indikator__nilai__periode=periode))
        ).filter(n__gt=0).count()
    )

    sisa_hari = (periode.tanggal_selesai - date.today()).days

    # ---------- peta kesiapan komponen ----------
    def susun_peta(jenis):
        baris = []
        for k in komponen_utama.filter(jenis=jenis, induk__isnull=True).order_by("urutan"):
            anak = k.keturunan()

            n_berita = Berita.objects.filter(
                periode=periode, status=Berita.Status.TERVERIFIKASI, kategori__in=anak
            ).distinct().count()

            n_malinau = Berita.objects.filter(
                periode=periode, status=Berita.Status.TERVERIFIKASI,
                kategori__in=anak, lingkup=Berita.Lingkup.MALINAU
            ).distinct().count()

            n_indikator = Indikator.objects.filter(komponen__in=anak, is_aktif=True).count()
            n_terisi = NilaiIndikator.objects.filter(
                indikator__komponen__in=anak, periode=periode, nilai__isnull=False
            ).count()

            f = Fenomena.objects.filter(periode=periode, kategori=k).first()
            n_narasi = f.rincian_set.exclude(narasi="").count() if f else 0

            if n_narasi == 3:
                keadaan = "siap"
            elif n_berita or n_terisi:
                keadaan = "sebagian"
            else:
                keadaan = "kosong"

            baris.append({
                "kategori": k, "n_berita": n_berita, "n_malinau": n_malinau,
                "n_indikator": n_indikator, "n_terisi": n_terisi,
                "n_narasi": n_narasi, "keadaan": keadaan,
            })
        return baris

    peta_sektoral = susun_peta("sektoral")
    peta_pengeluaran = susun_peta("pengeluaran")

    konteks.update({
        "menunggu": menunggu,
        "total_berita": berita_periode.count(),
        "total_komponen": total_komponen,
        "fenomena_lengkap": fenomena_lengkap,
        "persen_fenomena": round(fenomena_lengkap / total_komponen * 100) if total_komponen else 0,
        "opd_total": opd_aktif.count(),
        "opd_terisi": opd_terisi,
        "persen_opd": round(opd_terisi / opd_aktif.count() * 100) if opd_aktif.count() else 0,
        "sisa_hari": sisa_hari,
        "peta_sektoral": peta_sektoral,
        "peta_pengeluaran": peta_pengeluaran,
        "belum_siap": sum(1 for b in peta_sektoral + peta_pengeluaran if b["keadaan"] == "kosong"),
        "berita_terbaru": berita_periode.filter(
            status=Berita.Status.BARU
        ).select_related("portal").order_by("-tanggal_berita")[:8],
        "opd_belum": opd_aktif.annotate(
            n=Count("indikator__nilai", filter=Q(indikator__nilai__periode=periode))
        ).filter(n=0).select_related("petugas")[:10],
    })
    return render(request, "dashboard/beranda.html", konteks)