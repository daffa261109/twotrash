# PCB TT-PZ1 — Pi Zero langsung ke DRV8825

Papan carrier satu sisi **140 × 100 mm**, dua motor NEMA17 42HD4027-01, tanpa Nano. Rangkaian lengkap dan langkah uji: [../wiring.md](../wiring.md).

## File yang digunakan

| Keperluan | File |
| --- | --- |
| **Cetak untuk transfer toner** | [output/pdf/01-transfer-toner-1to1.pdf](output/pdf/01-transfer-toner-1to1.pdf) |
| Membandingkan hasil pada sisi tembaga | [output/pdf/02-tembaga-bawah-inspeksi.pdf](output/pdf/02-tembaga-bawah-inspeksi.pdf) |
| Penempatan, bor, jumper dan tabel titik sambungan | [output/pdf/03-komponen-dan-bor.pdf](output/pdf/03-komponen-dan-bor.pdf) |
| Preview tampak atas | [previews/pcb-atas.png](previews/pcb-atas.png) |
| Versi vektor | [output/svg/](output/svg/) |
| Belanja komponen | [bom.csv](bom.csv) |
| Kawat jumper W01–W28 | [jumpers.csv](jumpers.csv) |
| Semua pad, net dan diameter bor | [pads.csv](pads.csv) |
| GPIO untuk firmware baru | [pinmap.json](pinmap.json) |
| Pemeriksaan jalur/net | [drc-report.json](drc-report.json) |

Cetak file **01** pada **100% / Actual size**, tanpa Fit dan **tanpa mirror tambahan**. Sisi toner ditempel ke tembaga; setelah transfer tampilan sisi tembaga harus sama dengan file **02**. Ukur garis 50 mm terlebih dahulu.

Jalur tembaga saja belum merupakan rangkaian lengkap: **28 jumper berisolasi wajib dipasang**. Kedua ujung setiap jumper memakai lubang tersendiri; tidak berbagi lubang dengan kaki komponen. Titik yang hitam penuh pada pola adalah test point cadangan tanpa bor. Lubang mayoritas 1,0 mm; terminal sekrup 1,2 mm; dudukan 3,2 mm. Soket driver perlu tinggi minimal 8,5 mm agar ada ruang kawat di bawah modul; ujung jumper tidak diletakkan di bawah rumah IDC atau IC DIP.

Footprint driver khusus pinout Pololu DRV8825 2133: 2×8 pin, pitch 2,54 mm, jarak baris 15,24 mm. **EN kiri atas / VMOT kanan atas**. Cocokkan modul dan konektor fisik pada gambar 1:1 sebelum etsa. Ukuran body elko adalah batas penempatan, bukan jaminan semua merek cocok.

PCB hanya DC: input 12 V motor dan 5 V AUX periferal. Pi memakai catu USB sendiri. USB webcam lewat adaptor OTG langsung ke Pi; PCB tidak merutekan USB. JARM disimpan terbuka sampai firmware STEP/DIR, home, batas gerak dan FAULT tersedia. Kode aplikasi sekarang masih servo.

## Sumber dan pembuatan ulang

- `design.py`: koneksi listrik, footprint, posisi dan jalur daya awal.
- `route_board.py`: jalur tembaga satu sisi dan pad jumper; menyimpan `board.json`.
- `board.json`: geometri final yang dipakai semua keluaran.
- `validate_board.py`: pemeriksaan terpisah atas jarak tembaga, tepi PCB, annular ring, akses pad jumper, net dan mapping driver.
- `export_board.py`: PDF/SVG/PNG serta CSV dari geometri yang sama; menolak ekspor jika laporan DRC gagal.
- `draw_system.py`: diagram sistem daya dan sinyal untuk `wiring.md`.

Dengan Python dan paket dari `requirements.txt`, jalankan dari folder ini:

```sh
python route_board.py
python validate_board.py
python export_board.py
python draw_system.py
```

Tidak membutuhkan KiCad atau autorouter eksternal. Tidak ada lapisan tembaga atas atau via berlapis; jumper adalah kawat nyata. Hasil merupakan prototipe untuk etsa manual, bukan Gerber fabrikasi multi-layer.

## Batas verifikasi

Pemeriksaan digital memastikan semua net tersambung **setelah jumper dipasang**, tidak ada tembaga antarnet yang melanggar clearance 0,4 mm, pad/bor memenuhi annular ring 0,5 mm, dan rel Pi 5 V tidak dirutekan ke 5 V AUX. Pemeriksaan ini bukan simulasi rangkaian, pengujian termal, EMC, atau pembuktian kekuatan mekanik. PCB fisik belum dibuat; hasil etsa, modul clone dan kemampuan printer harus diperiksa nyata.
