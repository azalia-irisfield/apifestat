from django.contrib import admin

from .models import OPD, Indikator, NilaiIndikator


class IndikatorInline(admin.TabularInline):
    model = Indikator
    extra = 2
    fields = ("komponen", "nama", "frasa", "satuan", "sel_sumber", "urutan", "is_aktif")


@admin.register(OPD)
class OPDAdmin(admin.ModelAdmin):
    list_display = ("nama", "singkatan", "jenis", "nama_pic", "id_spreadsheet", "is_aktif")
    list_filter = ("jenis", "is_aktif")
    search_fields = ("nama", "singkatan")
    inlines = [IndikatorInline]
    fieldsets = (
        ("Identitas", {
            "fields": ("nama", "singkatan", "jenis", "nama_pic", "kontak_pic", "petugas", "is_aktif")
        }),
        ("Sumber Spreadsheet", {
            "fields": ("url_spreadsheet", "id_spreadsheet", "gid_sheet", "gid_tambahan"),
            "description": "Pastikan spreadsheet dibagikan dengan akses "
                           "“Anyone with the link — Viewer”."
        }),
        ("Tata Letak Tabel", {
            "fields": ("orientasi", "baris_tahun", "baris_periode", "kolom_label",
                       "kolom_periode", "baris_pertama", "baris_terakhir", "tahun_data"),
            "description": "Gunakan menu Pratinjau Sheet untuk melihat nomor baris dan kolom."
        }),
    )


@admin.register(Indikator)
class IndikatorAdmin(admin.ModelAdmin):
    list_display = ("nama", "komponen", "opd", "satuan", "sel_sumber", "urutan", "is_aktif")
    list_filter = ("opd", "komponen__jenis", "is_aktif")
    search_fields = ("nama", "frasa")


@admin.register(NilaiIndikator)
class NilaiIndikatorAdmin(admin.ModelAdmin):
    list_display = ("indikator", "periode", "nilai", "sumber_input")
    list_filter = ("periode", "indikator__opd", "sumber_input")