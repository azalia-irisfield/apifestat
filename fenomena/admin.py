from django.contrib import admin

from .models import Fenomena, FenomenaBerita, FenomenaIndikator, FenomenaRincian


class RincianInline(admin.TabularInline):
    model = FenomenaRincian
    extra = 0


@admin.register(Fenomena)
class FenomenaAdmin(admin.ModelAdmin):
    list_display = ("kategori", "periode", "status", "updated_at")
    list_filter = ("periode", "status", "kategori__jenis")
    inlines = [RincianInline]


admin.site.register(FenomenaBerita)
admin.site.register(FenomenaIndikator)