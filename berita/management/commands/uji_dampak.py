from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from berita.models import Berita, SheetODON
from berita.services.dampak import tebak_dampak
from inventarisasi.services.sheets import unduh_sheet

LABEL_KE_KODE = {label.lower(): kode for kode, label in Berita.Dampak.choices}


class Command(BaseCommand):
    help = ("Menguji ketepatan penentuan dampak otomatis terhadap isian petugas "
            "pada sheet ODON (atau pada database dengan --db).")

    def add_arguments(self, parser):
        parser.add_argument("--gid", help="GID tab lain, misalnya tab 2025 (bawaan: tab aktif)")
        parser.add_argument("--db", action="store_true",
                            help="Uji terhadap berita terverifikasi yang dampaknya diisi petugas")
        parser.add_argument("--gemini", action="store_true",
                            help="Uji dampak hasil Gemini (bawaan: kamus kata)")
        parser.add_argument("--maks", type=int, default=0,
                            help="Batasi jumlah contoh (hemat kuota Gemini), 0 = semua")
        parser.add_argument("--salah", type=int, default=15,
                            help="Jumlah contoh tebakan salah yang ditampilkan")

    def contoh_dari_sheet(self, gid):
        sheet = SheetODON.objects.filter(is_aktif=True).first()
        if not sheet:
            raise CommandError("Sheet ODON aktif belum diatur.")
        data = unduh_sheet(sheet.id_spreadsheet, gid or sheet.gid_sheet)
        for baris in data[sheet.baris_pertama - 1:]:
            def sel(k):
                try:
                    return (baris[k - 1] or "").strip()
                except IndexError:
                    return ""
            kode = LABEL_KE_KODE.get(sel(sheet.kol_dampak).lower())
            if kode and sel(sheet.kol_judul):
                yield sel(sheet.kol_judul), sel(sheet.kol_ringkasan), kode

    def contoh_dari_db(self):
        qs = Berita.objects.filter(status=Berita.Status.TERVERIFIKASI).exclude(dampak="")
        for b in qs:
            yield b.judul, b.ringkasan, b.dampak

    def handle(self, *args, **opsi):
        contoh = list(self.contoh_dari_db() if opsi["db"] else self.contoh_dari_sheet(opsi["gid"]))
        if not contoh:
            raise CommandError("Tidak ada contoh berlabel dampak untuk diuji.")

        if opsi["maks"]:
            contoh = contoh[-opsi["maks"]:]

        jawaban_gemini = {}
        if opsi["gemini"]:
            from berita.services.klasifikasi import (gemini_tersedia, peta_kategori,
                                                     tanya_gemini)
            if not gemini_tersedia():
                raise CommandError("GEMINI_API_KEY belum diisi di .env.")
            self.stdout.write(f"Mengirim {len(contoh)} contoh ke Gemini...")
            jawaban_gemini = tanya_gemini(
                [{"id": str(i), "judul": j, "teks": r} for i, (j, r, _) in enumerate(contoh)],
                peta_kategori())

        benar, matriks, salah = 0, Counter(), []
        for i, (judul, ringkasan, asli) in enumerate(contoh):
            if opsi["gemini"]:
                g = jawaban_gemini.get(str(i))
                if not g:
                    continue
                tebakan, alasan = g.get("dampak"), g.get("alasan", "")
                if tebakan not in LABEL_KE_KODE.values():
                    continue
            else:
                tebakan, yakin, alasan = tebak_dampak(judul, ringkasan)
            matriks[(asli, tebakan)] += 1
            if tebakan == asli:
                benar += 1
            else:
                salah.append((judul, asli, tebakan, alasan))

        n = sum(matriks.values())
        if not n:
            raise CommandError("Tidak ada jawaban yang bisa dinilai.")
        mesin = "Gemini" if opsi["gemini"] else "Kamus kata"
        self.stdout.write(self.style.SUCCESS(f"{mesin} — ketepatan: {benar}/{n} = {benar / n:.1%}\n"))

        kode = [k for k, _ in Berita.Dampak.choices]
        singkat = {"meningkatkan_ntb": "+NTB", "menurunkan_ntb": "-NTB",
                   "meningkatkan_harga": "+Harga", "menurunkan_harga": "-Harga"}
        self.stdout.write("Asli \\ Tebakan " + "".join(f"{singkat[k]:>9}" for k in kode))
        for a in kode:
            self.stdout.write(f"{singkat[a]:<15}" + "".join(f"{matriks[(a, t)]:>9}" for t in kode))

        if salah and opsi["salah"]:
            self.stdout.write(f"\nContoh tebakan salah (maks {opsi['salah']}):")
            for judul, asli, tebakan, alasan in salah[:opsi["salah"]]:
                self.stdout.write(f"- {judul[:80]}\n    asli {singkat[asli]}, "
                                  f"tebakan {singkat[tebakan]} | {alasan}")
