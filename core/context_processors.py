def ringkasan(request):
    """Angka ringkas untuk sidebar."""
    try:
        from berita.models import Berita
        from core.models import Periode

        return {
            "sb_berita_baru": Berita.objects.filter(status="baru").count(),
            "sb_periode": Periode.objects.filter(status="aktif").first(),
        }
    except Exception:
        return {}