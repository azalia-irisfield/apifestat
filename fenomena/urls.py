from django.urls import path

from . import views

app_name = "fenomena"

urlpatterns = [
    path("", views.daftar_fenomena, name="daftar"),
    path("susun/<int:pk>/", views.susun_fenomena, name="susun"),
    path("ekspor/", views.ekspor, name="ekspor"),
    path("susun-massal/", views.susun_massal, name="susun_massal"),
]