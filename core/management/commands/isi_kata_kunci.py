from django.core.management.base import BaseCommand

from core.models import Kategori, KataKunci

# (jenis, kode): [(kata_kunci, bobot), ...]
DATA = {
    # ================= A — PERTANIAN, KEHUTANAN, PERIKANAN =================
    ("sektoral", "A"): [
        ("pertanian", 2), ("ketahanan pangan", 2), ("penyuluh pertanian", 2),
        ("gapoktan", 2), ("kelompok tani", 2), ("lahan tidur", 2), ("cetak sawah", 2),
        ("food estate", 2), ("pesat", 1), ("alsintan", 2), ("pupuk subsidi", 2),
    ],
    ("sektoral", "A.1.a"): [
        ("padi", 3), ("gabah", 3), ("panen raya", 3), ("sawah", 3), ("jagung", 3),
        ("ubi kayu", 3), ("ubi jalar", 3), ("kedelai", 3), ("tanaman pangan", 3),
        ("luas panen", 3), ("produksi beras", 3), ("penggilingan padi", 2),
        ("ksa", 2), ("kerangka sampel area", 3), ("bulog", 2), ("gagal panen", 3),
        ("puso", 3), ("tanam perdana", 3),
    ],
    ("sektoral", "A.1.b"): [
        ("hortikultura", 3), ("cabai", 3), ("bawang merah", 3), ("bawang putih", 3),
        ("tomat", 3), ("semangka", 3), ("sayuran", 3), ("kangkung", 2), ("sawi", 2),
        ("terong", 2), ("timun", 2), ("vip horti", 3), ("melon", 2),
    ],
    ("sektoral", "A.1.c"): [
        ("perkebunan semusim", 3), ("tebu", 3), ("tembakau", 2), ("nilam", 2),
    ],
    ("sektoral", "A.1.d"): [
        ("pisang", 3), ("jeruk", 3), ("durian", 3), ("mangga", 2), ("rambutan", 2),
        ("nanas", 2), ("pepaya", 2), ("kates", 2), ("buah-buahan", 2),
        ("hortikultura tahunan", 3), ("kebun buah", 2),
    ],
    ("sektoral", "A.1.e"): [
        ("kelapa sawit", 3), ("tandan buah segar", 3), ("tbs", 2), ("karet", 3),
        ("lada", 3), ("kakao", 3), ("kopi", 3), ("kelapa", 2), ("cengkeh", 2),
        ("perkebunan tahunan", 3), ("replanting", 2), ("peremajaan sawit", 3),
    ],
    ("sektoral", "A.1.f"): [
        ("peternakan", 3), ("sapi", 3), ("kambing", 3), ("babi", 3), ("ayam ras", 3),
        ("ayam potong", 3), ("telur ayam", 3), ("rph", 3), ("rumah potong hewan", 3),
        ("pemotongan ternak", 3), ("ternak", 2), ("kurban", 2), ("idul adha", 2),
        ("vaksinasi ternak", 2), ("pmk", 2),
    ],
    ("sektoral", "A.1.g"): [
        ("jasa pertanian", 3), ("perburuan", 3), ("madu hutan", 3), ("sarang walet", 2),
        ("jasa penggilingan", 2),
    ],
    ("sektoral", "A.2"): [
        ("kayu bulat", 3), ("kehutanan", 3), ("penebangan kayu", 3), ("hph", 3),
        ("inhutani", 3), ("hasil hutan", 3), ("ditjen phl", 3), ("log kayu", 3),
        ("rotan", 2), ("gaharu", 3), ("perhutanan sosial", 2), ("hutan desa", 2),
    ],
    ("sektoral", "A.3"): [
        ("perikanan", 3), ("nelayan", 3), ("budi daya ikan", 3), ("tambak", 3),
        ("kolam ikan", 3), ("ikan air tawar", 3), ("ikan laut", 3), ("benih ikan", 3),
        ("tebar benih", 3), ("keramba", 3), ("udang", 2), ("rumput laut", 2),
        ("dinas perikanan", 2), ("produksi ikan", 3),
    ],

    # ================= B — PERTAMBANGAN =================
    ("sektoral", "B"): [
        ("pertambangan", 2), ("izin usaha pertambangan", 2), ("iup", 2),
        ("royalti tambang", 2), ("reklamasi tambang", 2),
    ],
    ("sektoral", "B.1"): [
        ("minyak bumi", 3), ("gas bumi", 3), ("migas", 3), ("panas bumi", 3),
        ("sumur minyak", 3),
    ],
    ("sektoral", "B.2"): [
        ("batu bara", 3), ("batubara", 3), ("lignit", 3), ("hauling", 3),
        ("kpuc", 3), ("mitrabara", 3), ("amnk", 3), ("produksi batu bara", 3),
        ("cadangan batu bara", 3), ("tongkang batu bara", 3), ("mining site", 2),
    ],
    ("sektoral", "B.3"): [
        ("bijih logam", 3), ("emas", 3), ("penambang emas", 3), ("peti", 2),
        ("tambang emas ilegal", 3), ("bijih besi", 2),
    ],
    ("sektoral", "B.4"): [
        ("galian c", 3), ("pasir", 3), ("batu split", 3), ("kerikil", 3),
        ("mblb", 3), ("mineral bukan logam", 3), ("pasir batu", 3), ("sirtu", 3),
        ("kuari", 2), ("tanah urug", 2),
    ],

    # ================= C — INDUSTRI PENGOLAHAN =================
    ("sektoral", "C"): [
        ("industri pengolahan", 2), ("imk", 2), ("industri kecil", 2),
        ("ikm", 2), ("hilirisasi", 2), ("pabrik", 2),
    ],
    ("sektoral", "C.2"): [
        ("industri makanan", 3), ("industri minuman", 3), ("olahan makanan", 3),
        ("keripik", 3), ("kue", 2), ("roti", 2), ("air minum dalam kemasan", 3),
        ("amdk", 2), ("tahu tempe", 3), ("abon", 2), ("kerupuk", 2),
        ("pabrik kelapa sawit", 3), ("crude palm oil", 3), ("cpo", 2),
    ],
    ("sektoral", "C.4"): [
        ("industri tekstil", 3), ("pakaian jadi", 3), ("konveksi", 3),
        ("batik", 3), ("tenun", 3), ("penjahit", 2), ("sablon", 2),
    ],
    ("sektoral", "C.5"): [
        ("alas kaki", 3), ("industri kulit", 3), ("sepatu", 2), ("sandal", 2),
    ],
    ("sektoral", "C.6"): [
        ("industri kayu", 3), ("barang dari kayu", 3), ("anyaman", 3),
        ("rotan", 3), ("bambu", 3), ("sawmill", 3), ("kedabang", 3),
        ("papan kayu", 3), ("kerajinan kayu", 3),
    ],
    ("sektoral", "C.7"): [
        ("percetakan", 3), ("industri kertas", 3), ("banner", 3), ("spanduk", 3),
        ("fotokopi", 2), ("reproduksi media", 2), ("undangan cetak", 2),
    ],
    ("sektoral", "C.8"): [
        ("industri kimia", 3), ("farmasi", 3), ("obat tradisional", 3),
        ("jamu", 2), ("bahan kimia", 3), ("pupuk organik", 2),
    ],
    ("sektoral", "C.9"): [
        ("industri karet", 3), ("barang dari plastik", 3), ("industri plastik", 3),
    ],
    ("sektoral", "C.10"): [
        ("galian bukan logam", 3), ("batu bata", 3), ("batako", 3), ("genteng", 2),
        ("pembakaran batu bata", 3), ("paving", 2), ("beton", 2),
    ],
    ("sektoral", "C.12"): [
        ("barang logam", 3), ("bengkel las", 3), ("industri elektronik", 3),
        ("peralatan listrik", 3), ("pandai besi", 2),
    ],
    ("sektoral", "C.14"): [
        ("alat angkutan", 3), ("perahu", 3), ("ketinting", 3), ("longboat", 3),
        ("karoseri", 2), ("galangan", 2),
    ],
    ("sektoral", "C.15"): [
        ("furnitur", 3), ("mebel", 3), ("meubel", 3), ("lemari", 2), ("kursi kayu", 2),
    ],
    ("sektoral", "C.16"): [
        ("jasa reparasi", 3), ("pemasangan mesin", 3), ("industri pengolahan lainnya", 3),
        ("buket bunga", 2), ("servis mesin", 2),
    ],

    # ================= D — LISTRIK DAN GAS =================
    ("sektoral", "D"): [("kelistrikan", 2), ("energi", 1)],
    ("sektoral", "D.1"): [
        ("pln", 3), ("listrik", 3), ("pembangkit", 3), ("pltd", 3), ("plta", 3),
        ("plts", 3), ("pltmh", 3), ("gardu", 3), ("pemadaman listrik", 3),
        ("tarif listrik", 3), ("jaringan listrik", 3), ("elektrifikasi", 3),
        ("korsleting", 2), ("daya listrik", 2), ("kayan hydropower", 3),
    ],
    ("sektoral", "D.2"): [
        ("pengadaan gas", 3), ("produksi es", 3), ("pabrik es", 3), ("elpiji", 2),
    ],

    # ================= E — AIR, SAMPAH, LIMBAH =================
    ("sektoral", "E"): [
        ("pdam", 3), ("air bersih", 3), ("air minum", 3), ("sampah", 3),
        ("tpa sampah", 3), ("tps3r", 3), ("bank sampah", 3), ("limbah", 3),
        ("sanitasi", 3), ("ipal", 3), ("pengolahan sampah", 3), ("krisis air", 3),
        ("distribusi air", 3), ("sumur bor", 2), ("dinas lingkungan hidup", 2),
        ("kebersihan kota", 2), ("daur ulang", 3),
    ],

    # ================= F — KONSTRUKSI =================
    ("sektoral", "F"): [
        ("pembangunan jalan", 3), ("rehabilitasi jalan", 3), ("pengaspalan", 3),
        ("jembatan", 3), ("kontraktor", 3), ("proyek fisik", 3), ("konstruksi", 3),
        ("drainase", 3), ("pembangunan gedung", 3), ("infrastruktur", 2),
        ("lelang proyek", 3), ("tender", 2), ("pupr", 2), ("peningkatan jalan", 3),
        ("penerangan jalan umum", 3), ("pju", 2), ("irigasi", 3), ("turap", 2),
        ("gorong-gorong", 2), ("semenisasi", 3), ("rumah layak huni", 2),
        ("belanja modal gedung", 3), ("jalan usaha tani", 3),
    ],

    # ================= G — PERDAGANGAN =================
    ("sektoral", "G"): [
        ("perdagangan", 2), ("distribusi barang", 2), ("stok barang", 2),
    ],
    ("sektoral", "G.1"): [
        ("penjualan mobil", 3), ("penjualan motor", 3), ("bbnkb", 3),
        ("dealer", 3), ("bengkel motor", 3), ("kendaraan bermotor", 3),
        ("samsat", 2), ("pajak kendaraan", 2),
    ],
    ("sektoral", "G.2"): [
        ("pasar", 3), ("harga sembako", 3), ("sembako", 3), ("pedagang", 3),
        ("harga beras", 3), ("harga cabai", 3), ("harga komoditas", 3),
        ("bahan pokok", 3), ("kebutuhan pokok", 3), ("spbu", 3), ("bbm", 2),
        ("pasar murah", 3), ("gerakan pangan murah", 3), ("gpm", 2),
        ("harga pangan", 3), ("umkm", 2), ("toko ritel", 2), ("pasar induk", 3),
        ("inflasi pangan", 3), ("operasi pasar", 3), ("takjil", 2),
    ],

    # ================= H — TRANSPORTASI =================
    ("sektoral", "H"): [("transportasi", 2), ("dinas perhubungan", 2), ("mobilitas", 1)],
    ("sektoral", "H.2"): [
        ("damri", 3), ("angkutan darat", 3), ("bus", 2), ("travel darat", 2),
        ("terminal", 2), ("subsidi ongkos angkut", 3), ("soa", 2),
        ("angkutan perdesaan", 3),
    ],
    ("sektoral", "H.3"): [
        ("angkutan laut", 3), ("pelabuhan", 3), ("kapal laut", 3), ("pelayaran", 3),
        ("tongkang", 2), ("bongkar muat", 3), ("kelapis", 3), ("pelni", 2),
    ],
    ("sektoral", "H.4"): [
        ("speedboat", 3), ("angkutan sungai", 3), ("penyeberangan", 3),
        ("longboat", 3), ("dermaga sungai", 3), ("feri", 3), ("kmp", 2),
    ],
    ("sektoral", "H.5"): [
        ("bandara", 3), ("penerbangan", 3), ("pesawat", 3), ("wings air", 3),
        ("susi air", 3), ("tiket pesawat", 3), ("penumpang pesawat", 3),
        ("rute penerbangan", 3), ("penerbangan dibatalkan", 3),
    ],
    ("sektoral", "H.6"): [
        ("pergudangan", 3), ("ekspedisi", 3), ("pos indonesia", 3), ("kurir", 3),
        ("paket pos", 3), ("kargo", 3), ("logistik", 3), ("gudang", 2),
    ],

    # ================= I — AKOMODASI DAN MAKAN MINUM =================
    ("sektoral", "I"): [("pariwisata kuliner", 1)],
    ("sektoral", "I.1"): [
        ("hotel", 3), ("penginapan", 3), ("homestay", 3), ("okupansi", 3),
        ("tingkat penghunian kamar", 3), ("tpk", 2), ("losmen", 3), ("wisma", 2),
        ("sewa hunian", 3), ("kamar hotel", 3),
    ],
    ("sektoral", "I.2"): [
        ("restoran", 3), ("rumah makan", 3), ("kafe", 3), ("warung makan", 3),
        ("katering", 3), ("jasa boga", 3), ("kedai kopi", 3), ("franchise makanan", 3),
        ("mbg", 2), ("makan bergizi gratis", 3), ("pbjt makanan", 3),
    ],

    # ================= J — INFORMASI DAN KOMUNIKASI =================
    ("sektoral", "J"): [
        ("internet", 3), ("jaringan telekomunikasi", 3), ("telkomsel", 3),
        ("telkom", 3), ("indihome", 3), ("sinyal", 3), ("bts", 2),
        ("fiber optik", 3), ("gangguan jaringan", 3), ("wifi", 3),
        ("siaran televisi", 2), ("radio", 2), ("blankspot", 3), ("starlink", 3),
    ],

    # ================= K — JASA KEUANGAN =================
    ("sektoral", "K"): [("jasa keuangan", 2), ("ojk", 2), ("literasi keuangan", 2)],
    ("sektoral", "K.1"): [
        ("bank", 3), ("kredit", 3), ("kur", 3), ("penyaluran kredit", 3),
        ("bank indonesia", 3), ("nasabah", 3), ("tabungan", 3), ("bankaltimtara", 3),
        ("bri", 2), ("bni", 2), ("mandiri", 2), ("qris", 3), ("pembiayaan", 3),
    ],
    ("sektoral", "K.2"): [
        ("asuransi", 3), ("bpjs ketenagakerjaan", 3), ("bpjs kesehatan", 3),
        ("klaim bpjs", 3), ("dana pensiun", 3), ("taspen", 3), ("jaminan sosial", 2),
    ],
    ("sektoral", "K.3"): [
        ("pegadaian", 3), ("koperasi simpan pinjam", 3), ("cu femung pebaya", 3),
        ("credit union", 3), ("gadai", 3), ("fintech", 2), ("pinjaman online", 2),
    ],
    ("sektoral", "K.4"): [
        ("jasa penunjang keuangan", 3), ("penukaran valuta", 3), ("money changer", 3),
    ],

    # ================= L — REAL ESTAT =================
    ("sektoral", "L"): [
        ("perumahan", 3), ("rumah subsidi", 3), ("properti", 3), ("sewa rumah", 3),
        ("kontrakan", 3), ("kos-kosan", 3), ("tanah kavling", 3),
        ("developer perumahan", 3), ("sertifikat tanah", 2), ("ptsl", 2),
        ("harga tanah", 3), ("real estat", 3),
    ],

    # ================= M,N — JASA PERUSAHAAN =================
    ("sektoral", "M,N"): [
        ("konsultan", 3), ("notaris", 3), ("akuntan", 3), ("jasa hukum", 3),
        ("pengacara", 3), ("arsitek", 3), ("kajian ilmiah", 3), ("penelitian", 2),
        ("jasa survei", 3), ("periklanan", 3), ("rental kendaraan", 3),
        ("sewa kendaraan", 3), ("penyewaan alat", 3), ("sewa sepeda", 3),
        ("biro perjalanan", 3), ("agen perjalanan", 3), ("travel umrah", 3),
        ("jemaah haji", 3), ("kuota haji", 3), ("tenaga kerja", 3),
        ("ketenagakerjaan", 3), ("lowongan kerja", 3), ("alih daya", 3),
        ("outsourcing", 3), ("jasa kebersihan", 3), ("jasa keamanan", 3),
        ("cleaning service", 2), ("pelatihan kerja", 2), ("bursa kerja", 3),
    ],

    # ================= O — ADMINISTRASI PEMERINTAHAN (sengaja sempit) =================
    ("sektoral", "O"): [
        ("asn", 1), ("pns", 1), ("cpns", 1), ("pppk", 1),
        ("reformasi birokrasi", 1), ("tunjangan kinerja", 1),
        ("administrasi kependudukan", 1), ("e-ktp", 1), ("polri", 1),
        ("kepolisian", 1), ("tni", 1), ("kodim", 1), ("pensiun pegawai", 1),
        ("aparatur sipil negara", 1), ("satpol pp", 1), ("pemadam kebakaran", 1),
        ("damkar", 1), ("bpbd", 1),
    ],

    # ================= P — PENDIDIKAN =================
    ("sektoral", "P"): [
        ("sekolah", 3), ("siswa", 3), ("guru", 3), ("paud", 3), ("madrasah", 3),
        ("beasiswa", 3), ("tahun ajaran", 3), ("kurikulum", 3), ("mahasiswa", 3),
        ("kuliah", 2), ("ujian sekolah", 3), ("spmb", 3), ("pesantren", 3),
        ("perpustakaan sekolah", 3), ("dinas pendidikan", 3), ("disdik", 3),
        ("bantuan operasional sekolah", 3), ("bos", 1), ("pelajar", 2),
        ("belajar daring", 3), ("sekolah 3t", 3), ("ruang kelas", 3),
    ],

    # ================= Q — KESEHATAN DAN SOSIAL =================
    ("sektoral", "Q"): [
        ("puskesmas", 3), ("rumah sakit", 3), ("rsud", 3), ("dokter", 3),
        ("perawat", 3), ("pasien", 3), ("imunisasi", 3), ("posyandu", 3),
        ("stunting", 3), ("gizi", 3), ("vaksinasi", 3), ("dinas kesehatan", 3),
        ("dinkes", 3), ("tuberkulosis", 3), ("tbc", 2), ("malaria", 3),
        ("demam berdarah", 3), ("ispa", 3), ("panti sosial", 3),
        ("bantuan sosial", 2), ("kesehatan ibu", 3), ("kb", 1), ("apotek", 3),
        ("ambulans", 3), ("penimbangan balita", 3),
    ],

    # ================= R,S,T,U — JASA LAINNYA =================
    ("sektoral", "R,S,T,U"): [
        ("olahraga", 3), ("porprov", 3), ("turnamen", 3), ("kompetisi", 2),
        ("koni", 3), ("atlet", 3), ("festival", 3), ("irau", 3), ("karnaval", 3),
        ("seni budaya", 3), ("sanggar", 3), ("objek wisata", 3), ("pariwisata", 3),
        ("destinasi wisata", 3), ("desa wisata", 3), ("hiburan", 2),
        ("gereja", 2), ("masjid", 2), ("organisasi keagamaan", 3),
        ("ormas", 2), ("bengkel", 2), ("salon", 3), ("pangkas rambut", 3),
        ("laundry", 3), ("bumdes", 3), ("karang taruna", 2), ("pramuka", 2),
        ("pawai", 3), ("lomba", 2), ("pesparani", 3), ("safari ramadan", 2),
    ],

    # ================= PENGELUARAN =================
    ("pengeluaran", "1"): [
        ("konsumsi rumah tangga", 3), ("daya beli", 3), ("belanja masyarakat", 3),
        ("pengeluaran rumah tangga", 3), ("inflasi", 3), ("pendapatan masyarakat", 2),
        ("thr", 2), ("seruti", 3),
    ],
    ("pengeluaran", "1.a"): [
        ("makanan dan minuman", 3), ("rokok", 3), ("harga rokok", 3),
        ("konsumsi pangan", 3), ("beras", 2), ("minyak goreng", 3),
    ],
    ("pengeluaran", "1.b"): [
        ("pakaian", 3), ("alas kaki", 3), ("baju lebaran", 3), ("seragam sekolah", 3),
    ],
    ("pengeluaran", "1.c"): [
        ("perlengkapan rumah tangga", 3), ("perkakas", 3), ("tarif air", 3),
        ("tagihan listrik rumah", 3), ("perabot", 3),
    ],
    ("pengeluaran", "1.d"): [
        ("biaya kesehatan", 3), ("biaya pendidikan", 3), ("spp", 3),
        ("berobat", 2),
    ],
    ("pengeluaran", "1.e"): [
        ("tarif angkutan", 3), ("biaya transportasi", 3), ("pulsa", 3),
        ("paket data", 3), ("rekreasi", 3), ("biaya komunikasi", 3),
    ],
    ("pengeluaran", "1.f"): [
        ("belanja di restoran", 3), ("menginap hotel", 3), ("wisata kuliner", 2),
    ],
    ("pengeluaran", "1.g"): [
        ("konsumsi lainnya", 3), ("jasa perawatan pribadi", 3),
    ],
    ("pengeluaran", "2"): [
        ("lnprt", 3), ("lsm", 3), ("yayasan", 3), ("organisasi kemasyarakatan", 3),
        ("partai politik", 3), ("lembaga nirlaba", 3), ("zakat", 3), ("baznas", 3),
        ("donasi", 3), ("pmi", 2), ("sumbangan", 2),
    ],
    ("pengeluaran", "3"): [
        ("belanja pemerintah", 3), ("belanja daerah", 3), ("apbd", 3),
        ("realisasi anggaran", 3), ("penyerapan anggaran", 3), ("belanja pegawai", 3),
        ("belanja barang dan jasa", 3), ("dau", 2), ("dak", 2), ("apbn", 2),
        ("transfer daerah", 3), ("efisiensi anggaran", 3), ("dana desa", 3),
        ("defisit anggaran", 3), ("bpkd", 2),
    ],
    ("pengeluaran", "4"): [
        ("investasi", 3), ("penanaman modal", 3), ("pmtb", 3), ("lkpm", 3),
        ("belanja modal", 3), ("dpmptsp", 3), ("realisasi investasi", 3),
    ],
    ("pengeluaran", "4.a"): [
        ("pembangunan gedung", 3), ("proyek konstruksi", 3), ("bangunan baru", 3),
    ],
    ("pengeluaran", "4.b"): [
        ("alat berat", 3), ("pembelian mesin", 3), ("pengadaan kendaraan dinas", 3),
        ("peralatan kantor", 2), ("non bangunan", 3),
    ],
    ("pengeluaran", "5"): [
        ("stok", 3), ("persediaan", 3), ("cadangan beras", 3), ("stok bbm", 3),
        ("gudang bulog", 3), ("cadangan pangan", 3), ("penimbunan", 2),
        ("perubahan inventori", 3),
    ],
    ("pengeluaran", "6"): [
        ("net ekspor", 3), ("neraca perdagangan", 3),
    ],
    ("pengeluaran", "6.a"): [
        ("ekspor", 3), ("plbn", 3), ("perdagangan lintas batas", 3),
        ("bea cukai", 3), ("komoditas ekspor", 3), ("pengiriman ke luar negeri", 3),
    ],
    ("pengeluaran", "6.b"): [
        ("impor", 3), ("barang impor", 3), ("pasokan dari malaysia", 3),
        ("barang dari malaysia", 3), ("pemasukan barang luar negeri", 3),
    ],
}


class Command(BaseCommand):
    help = "Mengisi kamus kata kunci untuk klasifikasi otomatis berita"

    def add_arguments(self, parser):
        parser.add_argument("--bersihkan", action="store_true",
                            help="Hapus seluruh kata kunci lama sebelum mengisi")

    def handle(self, *args, **opsi):
        if opsi["bersihkan"]:
            jumlah = KataKunci.objects.count()
            KataKunci.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"{jumlah} kata kunci lama dihapus."))

        dibuat = ada = 0
        tidak_ketemu = []

        for (jenis, kode), daftar in DATA.items():
            kategori = Kategori.objects.filter(jenis=jenis, kode=kode).first()
            if not kategori:
                tidak_ketemu.append(f"{jenis}/{kode}")
                continue
            for kata, bobot in daftar:
                _, baru = KataKunci.objects.get_or_create(
                    kategori=kategori, kata_kunci=kata, defaults={"bobot": bobot}
                )
                dibuat += baru
                ada += (not baru)

        self.stdout.write(self.style.SUCCESS(
            f"Selesai. {dibuat} kata kunci ditambahkan, {ada} sudah ada. "
            f"Total sekarang {KataKunci.objects.count()}."
        ))
        if tidak_ketemu:
            self.stdout.write(self.style.WARNING(
                "Kategori tidak ditemukan: " + ", ".join(tidak_ketemu)
            ))