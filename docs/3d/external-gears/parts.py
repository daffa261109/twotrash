"""Single inventory for printable parts, reference meshes and print quantities."""
from pathlib import Path
ROOT = Path(__file__).resolve().parent
# (copies of the complete STL, separate pieces in each STL, description)
PRINT_JOBS = {
    'flap': (1, 1, 'Flap 200 x 250 mm dengan penguat dan hub menyatu'),
    'frame': (1, 1, 'Rangka kepala pan-tilt'),
    'base_left': (1, 1, 'Belahan base kiri'),
    'base_right': (1, 1, 'Belahan base kanan'),
    'pinion_pan': (1, 1, 'Gear kecil PAN: penjepit di bawah gigi, untuk poros bulat 5 mm'),
    'pinion_tilt': (1, 1, 'Gear kecil TILT: penjepit di atas gigi, untuk poros bulat 5 mm'),
    'driven': (2, 1, 'Gear besar 48 gigi'),
    'caps': (1, 2, 'Satu STL sudah berisi dua tutup bearing'),
    'retainers': (1, 4, 'Satu STL sudah berisi empat cincin penahan bearing'),
}
REFERENCE_PARTS = ('tray_only', 'flange', 'motor', 'pan_shaft', 'tilt_shaft',
                   'pan_bearings', 'tilt_bearings', 'pan_collars', 'tilt_collar',
                   'rails', 'backplates', 'rivets', 'pinion_pan_fastener', 'pinion_tilt_fastener')
PARTS = list(PRINT_JOBS) + list(REFERENCE_PARTS)

def stl_path(part):
    if part not in PARTS:
        raise ValueError(f'Unknown CAD part: {part}')
    folder = 'cetak' if part in PRINT_JOBS else 'referensi'
    return ROOT / 'stl' / folder / f'{part}.stl'

def write_print_notes():
    for folder in ('cetak', 'referensi'):
        (ROOT / 'stl' / folder).mkdir(parents=True, exist_ok=True)
    lines = [
        'JUMLAH CETAK — SATU RAKITAN REV G1 (FLAP KOSONG)',
        '',
        'Hanya STL dalam folder cetak ini yang dicetak sebagai komponen plastik.',
        'Jumlah salinan di bawah berlaku untuk SELURUH ISI file STL.',
        '',
        'File             Salinan STL   Isi per STL   Hasil komponen',
        '----------------------------------------------------------',
    ]
    for part, (copies, pieces, description) in PRINT_JOBS.items():
        lines.append(f'{part + ".stl":<17}{copies:<14}{pieces:<14}{copies * pieces}')
    lines += [
        '',
        'TOTAL: 14 komponen plastik untuk satu rakitan.',
        'caps.stl: impor satu kali, sudah berisi DUA tutup; jangan digandakan lagi.',
        'retainers.stl: impor satu kali, sudah berisi EMPAT cincin; jangan digandakan lagi.',
        'pinion_pan.stl dan pinion_tilt.stl: masing-masing SATU; driven.stl: DUA.',
        '',
        'KETERANGAN',
    ]
    lines += [f'- {part}.stl: {job[2]}.' for part, job in PRINT_JOBS.items()]
    lines += [
        '',
        'Material awal: PETG untuk prototipe flap kosong.',
        'Pinion lama pinion.stl sudah diganti; jangan gunakan untuk motor ini.',
        'Pinion: 6 perimeter, infill 100%, layer 0.15-0.20 mm sebagai awal uji.',
        'PAN cetak sisi gigi datar di bed (balik 180 derajat); TILT sisi gigi di bed.',
        'Support diperlukan di bawah telinga/hub yang menjorok; bersihkan slot dan bore.',
        'Setiap penjepit: baut socket-head M3x16 + mur M3, TANPA washer.',
        'Total 2 baut M3x16 dan 2 mur M3; baut tambahan ini belum dibeli.',
        'Bersihkan lubang cetakan; jangan mengikir poros motor. Uji fit tanpa memaksa.',
        'Lihat catatan motor/pinion di CATATAN.txt sebelum merakit.',
        'Flap berukuran 200 x 250 mm; sediakan area cetak untuk brim.',
        'Periksa orientasi dan support di slicer, terutama flap dan hub poros.',
        'Ukuran CAD dalam mm. Jumlah cetak bukan pengaturan orientasi/support.',
        '',
        'Folder sebelah, referensi/, BUKAN daftar komponen untuk dicetak.',
        'Motor, bearing, poros baja, collar, backing plate logam, baut/mur dan',
        'rivet memakai hardware nyata sesuai CATATAN.txt di folder utama.',
        'Desain ini belum melalui uji fisik; tidak memiliki rating sampah 1 kg.',
    ]
    (ROOT / 'stl/cetak/JUMLAH-CETAK.txt').write_text('\n'.join(lines) + '\n')
    (ROOT / 'stl/referensi/JANGAN-DICETAK.txt').write_text(
        'REFERENSI SAJA — BUKAN FILE CETAK PLASTIK\n\n'
        'motor, bearing, shaft, collar, backing plate dan rivet: model hardware nyata.\n'
        'rails: ilustrasi penampang bak.\n'
        'flange: model gabungan base; cetak base_left dan base_right di folder cetak.\n'
        'tray_only: bagian piring untuk menghitung massa, bukan flap lengkap.\n\n'
        'Untuk pencetakan gunakan folder cetak/ dan ikuti JUMLAH-CETAK.txt.\n')

if __name__ == '__main__':
    write_print_notes()
