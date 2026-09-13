from django.core.paginator import Paginator
from django.shortcuts import render

from core.models import LogAktivitas, Pengguna


def log_aktivitas(request):
    qs = LogAktivitas.objects.select_related("pengguna")

    f = {
        "pengguna": request.GET.get("pengguna", ""),
        "aksi": request.GET.get("aksi", ""),
    }
    if f["pengguna"]:
        qs = qs.filter(pengguna_id=f["pengguna"])
    if f["aksi"]:
        qs = qs.filter(aksi=f["aksi"])

    hal = Paginator(qs, 50).get_page(request.GET.get("page"))

    return render(request, "core/log.html", {
        "hal": hal,
        "f": f,
        "pilihan_pengguna": Pengguna.objects.filter(is_aktif=True),
        "pilihan_aksi": LogAktivitas.objects.values_list("aksi", flat=True).distinct(),
    })