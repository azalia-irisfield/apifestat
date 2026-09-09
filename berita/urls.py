from django.urls import path

from . import views

app_name = "berita"

urlpatterns = [
    path("", views.daftar_berita, name="daftar"),
    path("scraping/", views.proses_scraping, name="scraping"),
    path("<int:pk>/verifikasi/", views.verifikasi_berita, name="verifikasi"),
    path("<int:pk>/ubah-cepat/", views.ubah_cepat, name="ubah_cepat"),
    path("<int:pk>/odon/", views.pilih_baris_odon, name="odon_baris"),
    path("<int:pk>/odon/catat/", views.catat_odon, name="odon_catat"),
]