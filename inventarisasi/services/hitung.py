"""Perhitungan pertumbuhan q-to-q, y-on-y, dan c-to-c."""

from decimal import Decimal

from core.models import Periode
from inventarisasi.models import NilaiIndikator


def periode_qtoq(p):
    if p.triwulan > 1:
        return Periode.objects.filter(tahun=p.tahun, triwulan=p.triwulan - 1).first()
    return Periode.objects.filter(tahun=p.tahun - 1, triwulan=4).first()


def periode_yoy(p):
    return Periode.objects.filter(tahun=p.tahun - 1, triwulan=p.triwulan).first()


def ambil_nilai(indikator, periode):
    if not periode:
        return None
    n = NilaiIndikator.objects.filter(indikator=indikator, periode=periode).first()
    return n.nilai if n and n.nilai is not None else None


def persen(sekarang, sebelum):
    if sekarang is None or sebelum in (None, 0):
        return None
    return float((sekarang - sebelum) / abs(sebelum) * 100)


def kumulatif(indikator, tahun, sampai_triwulan):
    qs = NilaiIndikator.objects.filter(
        indikator=indikator, periode__tahun=tahun,
        periode__triwulan__lte=sampai_triwulan, periode__triwulan__gte=1,
    ).exclude(nilai__isnull=True)
    total = sum((n.nilai for n in qs), Decimal("0"))
    return total if qs.exists() else None


def hitung_indikator(indikator, periode):
    """Mengembalikan seluruh angka pertumbuhan untuk satu indikator pada satu periode."""
    p_qtoq = periode_qtoq(periode)
    p_yoy = periode_yoy(periode)

    kini = ambil_nilai(indikator, periode)
    lalu = ambil_nilai(indikator, p_qtoq)
    tahun_lalu = ambil_nilai(indikator, p_yoy)

    kum_kini = kumulatif(indikator, periode.tahun, periode.triwulan)
    kum_lalu = kumulatif(indikator, periode.tahun - 1, periode.triwulan)

    return {
        "indikator": indikator,
        "nilai": kini,
        "nilai_qtoq": lalu,
        "nilai_yoy": tahun_lalu,
        "qtoq": persen(kini, lalu),
        "yoy": persen(kini, tahun_lalu),
        "ctoc": persen(kum_kini, kum_lalu),
        "periode_qtoq": p_qtoq,
        "periode_yoy": p_yoy,
    }


def arah(nilai):
    if nilai is None:
        return None
    if abs(nilai) < 0.005:
        return "konstan"
    return "peningkatan" if nilai > 0 else "penurunan"


PEMBANDING = {
    "qtoq": "triwulan sebelumnya (qtoq)",
    "yoy": "tahun sebelumnya pada triwulan yang sama (yoy)",
    "ctoc": "periode kumulatif tahun sebelumnya (ctoc)",
}


def susun_narasi(hasil, jenis="qtoq"):
    """Menyusun usulan narasi bergaya ODON, dikelompokkan menjadi (+), (-), dan (x)."""
    naik, turun, tetap = [], [], []

    for h in hasil:
        nilai = h.get(jenis)
        a = arah(nilai)
        if a is None:
            continue

        ind = h["indikator"]
        frasa = ind.frasa or ind.nama.lower()

        if a == "konstan":
            tetap.append(
                f"(x) Tidak terdapat perubahan pada {frasa} dibandingkan {PEMBANDING[jenis]}"
            )
            continue

        baris = (f"({'+' if a == 'peningkatan' else '-'}) Terdapat {a} pada {frasa} "
                 f"sebesar {abs(nilai):.2f}% dibandingkan {PEMBANDING[jenis]}")
        (naik if a == "peningkatan" else turun).append(baris)

    bagian = []
    if naik:
        bagian.append("Peningkatan:\n" + "\n".join(naik))
    if turun:
        bagian.append("Penurunan:\n" + "\n".join(turun))
    if tetap:
        bagian.append("Konstan:\n" + "\n".join(tetap))
    return "\n\n".join(bagian)