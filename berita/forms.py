from django import forms

from core.models import Kategori
from .models import Berita, BeritaKategori


class VerifikasiBeritaForm(forms.ModelForm):
    kategori_pilihan = forms.ModelMultipleChoiceField(
        queryset=Kategori.objects.filter(is_aktif=True),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
        label="Kategori PDRB",
    )
    # arah_dampak = forms.ChoiceField(
    #     choices=[("", "---------")] + list(BeritaKategori.ArahDampak.choices),
    #     required=False,
    #     widget=forms.Select(attrs={"class": "form-select"}),
    #     label="Arah Dampak",
    # )

    class Meta:
        model = Berita
        fields = ["judul", "ringkasan", "tanggal_berita", "periode", "dampak", "status"]
        widgets = {
            "judul": forms.TextInput(attrs={"class": "form-control"}),
            "ringkasan": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "tanggal_berita": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "periode": forms.Select(attrs={"class": "form-select"}),
            "dampak": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            relasi = self.instance.beritakategori_set.all()
            self.fields["kategori_pilihan"].initial = [r.kategori_id for r in relasi]
            # pertama = relasi.first()
            # if pertama:
            #     self.fields["arah_dampak"].initial = pertama.arah_dampak

    def save(self, commit=True):
        berita = super().save(commit=commit)
        arah = BeritaKategori.ARAH_DARI_DAMPAK.get(berita.dampak, "")
        terpilih = self.cleaned_data.get("kategori_pilihan")
        berita.beritakategori_set.exclude(kategori__in=terpilih).delete()
        for kategori in terpilih:
            BeritaKategori.objects.update_or_create(
                berita=berita, kategori=kategori, defaults={"arah_dampak": arah}
            )
        return berita