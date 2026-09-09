"""Penentuan hak akses berdasarkan token pada URL (SP-01, UC-01)."""

from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

BEBAS = ("/masuk-token/", "/static/", "/media/")


class TokenAksesMiddleware:
    """Membaca token sekali, lalu menyimpan identitas pada sesi.

    Token cukup dibuka satu kali; kunjungan berikutnya memakai sesi sehingga
    token tidak menempel pada alamat dan tidak tersimpan di riwayat peramban.
    Pengelola dengan akses permanen dapat masuk melalui halaman pengelola
    tanpa perlu membuka tautan token.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from core.models import Pengguna

        token = request.GET.get("token", "").strip()
        if token:
            p = Pengguna.objects.filter(token_akses=token, is_aktif=True).first()
            if not p:
                return render(request, "akses_ditolak.html",
                              {"alasan": "Tautan akses tidak dikenali atau sudah dinonaktifkan."},
                              status=403)
            request.session["pengguna_id"] = p.id
            request.session.set_expiry(60 * 60 * 24 * 180)

            sisa = request.GET.copy()
            sisa.pop("token")
            tujuan = request.path + (f"?{sisa.urlencode()}" if sisa else "")
            return redirect(tujuan)

        request.pengguna = None
        pid = request.session.get("pengguna_id")
        if pid:
            request.pengguna = Pengguna.objects.filter(pk=pid, is_aktif=True).first()

        # Pengelola dengan akses permanen: cukup login Django sekali
        if not request.pengguna and request.user.is_authenticated:
            request.pengguna = Pengguna.objects.filter(
                akun=request.user, is_aktif=True, akses_permanen=True
            ).first()
            if request.pengguna:
                request.session["pengguna_id"] = request.pengguna.id

        if request.path.startswith("/admin/"):
            return self.get_response(request)

        if not request.pengguna and not request.path.startswith(BEBAS):
            return render(request, "akses_ditolak.html", {
                "alasan": "Halaman ini hanya dapat diakses melalui tautan yang "
                          "diterbitkan pengelola sistem.",
            }, status=403)

        if request.pengguna and request.pengguna.role != "admin":
            if request.path.startswith("/admin/"):
                return HttpResponseForbidden("Halaman ini hanya untuk Admin.")

        return self.get_response(request)