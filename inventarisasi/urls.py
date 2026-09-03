from django.urls import path

from . import views

app_name = "inventarisasi"

urlpatterns = [
    path("", views.pohon_komponen, name="pohon"),
    path("komponen/<int:pk>/", views.detail_komponen, name="detail"),
    path("opd/<int:pk>/tarik/", views.tarik_sheet, name="tarik"),
    path("opd/<int:pk>/pratinjau/", views.pratinjau_sheet, name="pratinjau"),
]