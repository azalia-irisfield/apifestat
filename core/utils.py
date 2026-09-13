"""Pencatatan aktivitas pengguna."""


def catat(request, aksi, entitas="", entitas_id=None, keterangan=""):
    """Mencatat satu aktivitas pengguna. Kegagalan pencatatan diabaikan
    agar tidak pernah mengganggu jalannya fungsi utama."""
    try:
        from core.models import LogAktivitas

        LogAktivitas.objects.create(
            pengguna=getattr(request, "pengguna", None),
            aksi=aksi,
            entitas=entitas,
            entitas_id=entitas_id,
            keterangan=keterangan[:255],
            alamat_ip=request.META.get("REMOTE_ADDR", "")[:45],
        )
    except Exception:
        pass