from django.contrib import admin

from .models import Berita, BeritaKategori, LogScraping, Portal


@admin.register(Portal)
class PortalAdmin(admin.ModelAdmin):
    list_display = ("nama_portal", "tipe_sumber", "url_sumber", "is_aktif")
    list_filter = ("tipe_sumber", "is_aktif")


class BeritaKategoriInline(admin.TabularInline):
    model = BeritaKategori
    extra = 1


@admin.register(Berita)
class BeritaAdmin(admin.ModelAdmin):
    list_display = ("tanggal_berita", "judul", "lingkup", "portal", "periode", "dampak", "status")
    list_filter = ("lingkup", "status", "periode", "portal", "dampak")
    search_fields = ("judul", "ringkasan")
    date_hierarchy = "tanggal_berita"
    inlines = [BeritaKategoriInline]
    readonly_fields = ("hash_konten", "created_at", "updated_at")


@admin.register(LogScraping)
class LogScrapingAdmin(admin.ModelAdmin):
    list_display = ("waktu_mulai", "portal", "status", "jumlah_ditemukan",
                    "jumlah_disimpan", "jumlah_duplikat", "jumlah_diabaikan")
    list_filter = ("status", "portal")
    readonly_fields = [f.name for f in LogScraping._meta.fields]