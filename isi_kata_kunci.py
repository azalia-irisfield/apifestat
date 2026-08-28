from core.models import Kategori, KataKunci

# Format: (jenis, kode): [(kata_kunci, bobot), ...]
DATA = {
    ("sektoral", "A"): [
        ("panen", 3), ("padi", 3), ("sawah", 3), ("gabah", 3), ("jagung", 2),
        ("petani", 3), ("kelapa sawit", 3), ("tandan buah segar", 3), ("perkebunan", 2),
        ("pupuk", 2), ("bibit", 2), ("luas tanam", 3), ("produksi beras", 3),
        ("nelayan", 3), ("perikanan", 3), ("budi daya ikan", 3), ("tambak", 3),
        ("hasil laut", 2), ("ketahanan pangan", 2), ("penyuluh pertanian", 3),
        ("ternak", 3), ("sapi", 2), ("ayam", 2), ("karet", 2), ("lada", 2),
        ("gaharu", 3), ("hasil hutan", 3), ("kayu log", 3), ("kehutanan", 3),
    ],
    ("sektoral", "B"): [
        ("batu bara", 3), ("batubara", 3), ("tambang", 3), ("pertambangan", 3),
        ("izin usaha pertambangan", 3), ("iup", 2), ("galian c", 3),
        ("pasir", 2), ("batu split", 3), ("hauling", 3), ("eksplorasi", 2),
        ("royalti tambang", 3), ("produksi tambang", 3), ("emas", 2),
    ],
    ("sektoral", "C"): [
        ("pabrik", 3), ("industri pengolahan", 3), ("sawmill", 3),
        ("pabrik kelapa sawit", 3), ("crude palm oil", 3), ("cpo", 2),
        ("penggilingan padi", 3), ("industri kecil", 2), ("ikm", 2),
        ("kerajinan", 2), ("mebel", 2), ("olahan makanan", 2), ("produksi olahan", 2),
        ("batik", 2), ("tenun", 2),
    ],
    ("sektoral", "D"): [
        ("pln", 3), ("listrik", 3), ("kelistrikan", 3), ("pembangkit", 3),
        ("pltd", 3), ("plta", 3), ("plts", 3), ("pltmh", 3),
        ("elektrifikasi", 3), ("gardu", 3), ("pemadaman listrik", 3),
        ("tarif listrik", 3), ("jaringan listrik", 3), ("daya listrik", 2),
    ],
    ("sektoral", "E"): [
        ("pdam", 3), ("air bersih", 3), ("air minum", 3), ("sampah", 3),
        ("tpa sampah", 3), ("tps3r", 3), ("bank sampah", 3), ("limbah", 3),
        ("sanitasi", 3), ("ipal", 3), ("pengolahan sampah", 3),
    ],
    ("sektoral", "F"): [
        ("pembangunan jalan", 3), ("rehabilitasi jalan", 3), ("pengaspalan", 3),
        ("jembatan", 3), ("kontraktor", 3), ("proyek fisik", 3), ("konstruksi", 3),
        ("drainase", 3), ("pembangunan gedung", 3), ("infrastruktur jalan", 3),
        ("lelang proyek", 3), ("tender", 2), ("semen", 2), ("pekerjaan fisik", 2),
        ("pupr", 2), ("peningkatan jalan", 3),
    ],
    ("sektoral", "G"): [
        ("pasar", 3), ("harga sembako", 3), ("sembako", 3), ("pedagang", 3),
        ("harga beras", 3), ("harga cabai", 3), ("harga komoditas", 3),
        ("bahan pokok", 3), ("kebutuhan pokok", 3), ("spbu", 3), ("bbm", 2),
        ("elpiji", 3), ("distribusi barang", 2), ("ritel", 2), ("toko", 1),
        ("pasar induk", 3), ("harga pangan", 3),
    ],
    ("sektoral", "H"): [
        ("speedboat", 3), ("pelabuhan", 3), ("bandara", 3), ("penerbangan", 3),
        ("angkutan", 3), ("transportasi", 3), ("penyeberangan", 3), ("feri", 3),
        ("kmp", 2), ("tiket kapal", 3), ("logistik", 3), ("pergudangan", 3),
        ("subsidi ongkos angkut", 3), ("soa", 2), ("penumpang", 2),
        ("ekspedisi", 3), ("transportasi sungai", 3), ("jalan trans", 2),
    ],
    ("sektoral", "I"): [
        ("hotel", 3), ("penginapan", 3), ("homestay", 3), ("okupansi", 3),
        ("restoran", 3), ("rumah makan", 3), ("kafe", 2), ("kuliner", 2),
        ("katering", 3), ("wisatawan menginap", 3),
    ],
    ("sektoral", "J"): [
        ("internet", 3), ("jaringan telekomunikasi", 3), ("telkomsel", 3),
        ("sinyal", 3), ("bts", 2), ("fiber optik", 3), ("telepon seluler", 3),
        ("siaran", 2), ("jaringan seluler", 3),
    ],
    ("sektoral", "K"): [
        ("bank", 3), ("kredit", 3), ("kur", 2), ("pembiayaan", 3),
        ("asuransi", 3), ("bpjs ketenagakerjaan", 3), ("ojk", 3),
        ("qris", 3), ("tabungan", 3), ("transaksi keuangan", 3),
        ("koperasi simpan pinjam", 3), ("bank indonesia", 3), ("nasabah", 3),
    ],
    ("sektoral", "L"): [
        ("perumahan", 3), ("rumah subsidi", 3), ("properti", 3),
        ("sewa rumah", 3), ("kontrakan", 3), ("tanah kavling", 3),
        ("developer perumahan", 3), ("sewa hunian", 3),
    ],
    ("sektoral", "M"): [
        ("konsultan", 3), ("notaris", 3), ("akuntan", 3), ("jasa hukum", 3),
        ("penelitian", 2), ("kajian ilmiah", 3), ("arsitek", 3), ("survei", 2),
    ],
    ("sektoral", "N"): [
        ("rental kendaraan", 3), ("penyewaan kendaraan", 3), ("sewa kendaraan", 3),
        ("biro perjalanan", 3), ("agen perjalanan", 3), ("travel", 2),
        ("tenaga kerja", 3), ("ketenagakerjaan", 3), ("lowongan kerja", 3),
        ("alih daya", 3), ("outsourcing", 3), ("pelatihan kerja", 2),
    ],
    ("sektoral", "O"): [
        # Sengaja sempit dan berbobot rendah agar tidak menenggelamkan kategori lain
        ("asn", 1), ("pns", 1), ("cpns", 1), ("pppk", 1),
        ("reformasi birokrasi", 1), ("tunjangan kinerja", 1),
        ("administrasi kependudukan", 1), ("e-ktp", 1),
        ("polri", 1), ("kepolisian", 1), ("tni", 1), ("kodim", 1),
        ("pensiun pegawai", 1), ("aparatur sipil negara", 1),
    ],
    ("sektoral", "P"): [
        ("sekolah", 3), ("siswa", 3), ("guru", 3), ("paud", 3), ("madrasah", 3),
        ("beasiswa", 3), ("tahun ajaran", 3), ("kurikulum", 3), ("mahasiswa", 3),
        ("kuliah", 2), ("ujian sekolah", 3), ("spmb", 3), ("pendidikan", 2),
        ("pesantren", 3),
    ],
    ("sektoral", "Q"): [
        ("puskesmas", 3), ("rumah sakit", 3), ("rsud", 3), ("dokter", 3),
        ("perawat", 3), ("pasien", 3), ("imunisasi", 3), ("posyandu", 3),
        ("stunting", 3), ("gizi", 3), ("vaksinasi", 3), ("kesehatan", 2),
        ("bantuan sosial", 2), ("panti sosial", 3),
    ],
    ("sektoral", "R,S,T,U"): [
        ("olahraga", 3), ("porprov", 3), ("turnamen", 3), ("kompetisi", 2),
        ("festival", 3), ("irau", 3), ("karnaval", 3), ("seni budaya", 3),
        ("sanggar", 3), ("objek wisata", 3), ("pariwisata", 3), ("destinasi wisata", 3),
        ("hiburan", 2), ("gereja", 2), ("masjid", 2), ("organisasi keagamaan", 3),
        ("bengkel", 2), ("salon", 2),
    ],

    # ================= PENGELUARAN =================
    ("pengeluaran", "1"): [
        ("konsumsi rumah tangga", 3), ("daya beli", 3), ("belanja masyarakat", 3),
        ("pengeluaran rumah tangga", 3), ("inflasi", 3), ("harga kebutuhan pokok", 3),
        ("pendapatan masyarakat", 2), ("belanja warga", 2),
    ],
    ("pengeluaran", "2"): [
        ("lsm", 3), ("yayasan", 3), ("ormas", 3), ("organisasi kemasyarakatan", 3),
        ("partai politik", 3), ("lembaga nirlaba", 3), ("sumbangan", 2),
        ("pmi", 2), ("donasi", 2),
    ],
    ("pengeluaran", "3"): [
        ("belanja pemerintah", 3), ("belanja daerah", 3), ("apbd", 3),
        ("realisasi anggaran", 3), ("penyerapan anggaran", 3), ("belanja pegawai", 3),
        ("belanja barang dan jasa", 3), ("dau", 2), ("dak", 2),
        ("transfer daerah", 3), ("efisiensi anggaran", 3), ("apbn", 2),
    ],
    ("pengeluaran", "4"): [
        ("investasi", 3), ("penanaman modal", 3), ("pmtb", 3),
        ("pembangunan infrastruktur", 3), ("alat berat", 3),
        ("pembelian mesin", 3), ("gedung baru", 3), ("belanja modal", 3),
    ],
    ("pengeluaran", "5"): [
        ("stok", 3), ("persediaan", 3), ("cadangan beras", 3), ("stok bbm", 3),
        ("gudang bulog", 3), ("cadangan pangan", 3), ("penimbunan", 2),
    ],
    ("pengeluaran", "6"): [
        ("ekspor", 3), ("plbn", 3), ("perdagangan lintas batas", 3),
        ("bea cukai", 3), ("pengiriman ke luar negeri", 3),
        ("perbatasan malaysia", 2), ("komoditas ekspor", 3),
    ],
    ("pengeluaran", "7"): [
        ("impor", 3), ("barang impor", 3), ("pemasukan barang luar negeri", 3),
        ("pasokan dari malaysia", 3), ("barang dari malaysia", 3),
    ],
}

dibuat = dilewati = 0
for (jenis, kode), daftar in DATA.items():
    try:
        kategori = Kategori.objects.get(jenis=jenis, kode=kode)
    except Kategori.DoesNotExist:
        print(f"LEWAT: kategori {jenis}/{kode} tidak ditemukan")
        continue
    for kata, bobot in daftar:
        obj, baru = KataKunci.objects.get_or_create(
            kategori=kategori, kata_kunci=kata, defaults={"bobot": bobot}
        )
        if baru:
            dibuat += 1
        else:
            dilewati += 1

print(f"Selesai. {dibuat} kata kunci ditambahkan, {dilewati} sudah ada.")
print(f"Total kata kunci: {KataKunci.objects.count()}")