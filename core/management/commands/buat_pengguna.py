from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from core.models import Pengguna

# (nama, nip, jabatan, role, akses_permanen, username_admin)
DAFTAR = [
    ("Sindu Dinar Bangun Leksono", "200204252026031001",
     "Pranata Komputer Ahli Pertama", "admin", True, "azalia-irisfield"),
    ("Yanuar Dwi Cristyawan", "198601302009021001",
     "Kepala BPS Kabupaten Malinau", "admin", False, None),
    ("Ervione Mahala Zulfitri", "",
     "Ketua Tim Nerwilis", "admin", False, None),
    ("Yusa Okta Mahendra", "",
     "Statistisi Ahli Pertama", "pengguna", False, None),
]


class Command(BaseCommand):
    help = "Membuat pengguna APIFESTAT beserta tautan aksesnya"

    def add_arguments(self, parser):
        parser.add_argument("--alamat", default="http://127.0.0.1:8000")

    def handle(self, *args, **opsi):
        for nama, nip, jabatan, role, permanen, username in DAFTAR:
            akun = User.objects.filter(username=username).first() if username else None

            p, baru = Pengguna.objects.update_or_create(
                nip=nip or nama.lower().replace(" ", "_"),
                defaults={
                    "nama": nama, "jabatan": jabatan, "role": role,
                    "is_aktif": True, "akses_permanen": permanen, "akun": akun,
                },
            )
            status = "dibuat" if baru else "diperbarui"
            self.stdout.write(self.style.SUCCESS(f"\n{nama} — {role} ({status})"))

            if permanen:
                if akun:
                    self.stdout.write("  Akses permanen melalui akun pengelola "
                                      f"'{username}', tanpa perlu tautan token.")
                else:
                    self.stdout.write(self.style.ERROR(
                        f"  Akun '{username}' belum ada. Buat dengan createsuperuser, "
                        "lalu jalankan perintah ini lagi."
                    ))
            self.stdout.write(f"  {opsi['alamat']}/?token={p.token_akses}")

        self.stdout.write(self.style.WARNING(
            "\nBagikan tautan hanya kepada yang bersangkutan."
        ))