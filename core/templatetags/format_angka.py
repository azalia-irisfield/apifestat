from decimal import Decimal

from django import template

register = template.Library()


def _bersihkan(nilai):
    """Membuang nol desimal yang tidak bermakna."""
    d = Decimal(str(nilai)).normalize()
    if d == d.to_integral_value():
        d = d.quantize(Decimal(1))
    return d


@register.filter
def rapi(nilai):
    """Angka dengan pemisah ribuan titik dan desimal koma, gaya Indonesia."""
    if nilai is None or nilai == "":
        return "—"
    try:
        d = _bersihkan(nilai)
    except Exception:
        return nilai

    utuh, _, pecahan = f"{abs(d):f}".partition(".")
    utuh = f"{int(utuh):,}".replace(",", ".")
    tanda = "-" if d < 0 else ""
    return f"{tanda}{utuh},{pecahan}" if pecahan else f"{tanda}{utuh}"


@register.filter
def angka_isian(nilai):
    """Nilai untuk kotak isian: tanpa pemisah ribuan agar mudah disunting."""
    if nilai is None or nilai == "":
        return ""
    try:
        return f"{_bersihkan(nilai):f}"
    except Exception:
        return nilai

@register.filter
def rapi_isian(nilai):
    """Sama seperti rapi, tetapi mengembalikan kosong bila tidak ada nilai."""
    if nilai is None or nilai == "":
        return ""
    return rapi(nilai)