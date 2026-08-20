from django.contrib import admin

from .models import KataKunci, Kategori, Pengguna, Periode


@admin.register(Pengguna)
class PenggunaAdmin(admin.ModelAdmin):
    list_display = ("nama", "nip", "jabatan", "role", "is_aktif")
    list_filter = ("role", "is_aktif")
    search_fields = ("nama", "nip")
    readonly_fields = ("token_akses", "created_at", "updated_at")


@admin.register(Periode)
class PeriodeAdmin(admin.ModelAdmin):
    list_display = ("nama_periode", "tahun", "triwulan", "tanggal_mulai", "tanggal_selesai", "status")
    list_filter = ("tahun", "status")


class KataKunciInline(admin.TabularInline):
    model = KataKunci
    extra = 3


@admin.register(Kategori)
class KategoriAdmin(admin.ModelAdmin):
    list_display = ("kode", "nama", "jenis", "urutan", "is_aktif")
    list_filter = ("jenis", "is_aktif")
    search_fields = ("kode", "nama")
    inlines = [KataKunciInline]


@admin.register(KataKunci)
class KataKunciAdmin(admin.ModelAdmin):
    list_display = ("kata_kunci", "kategori", "bobot")
    list_filter = ("kategori__jenis",)
    search_fields = ("kata_kunci",)