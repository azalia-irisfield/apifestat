from django.urls import path

from . import views

app_name = "berita"

urlpatterns = [
    path("", views.daftar_berita, name="daftar"),
    path("scraping/", views.proses_scraping, name="scraping"),
    path("<int:pk>/verifikasi/", views.verifikasi_berita, name="verifikasi"),
]