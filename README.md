# Pi Zero

Program Python untuk Raspberry Pi Zero. Wiring lengkap ada di [docs/wiring.md](docs/wiring.md).

## Revisi hardware: PCB gabungan, flap pan-tilt, dan webcam USB

**Mekanik — Rev G1:** [Rev G1: NEMA17 + gear luar 3:1, frame 66 mm, flap 20 × 25 cm (flap kosong)](docs/3d/external-gears/CATATAN.txt).
Untuk melihat seluruh alat, buka `docs/3d/external-gears/rakitan.scad`;
untuk mencetak flap, gunakan `docs/3d/external-gears/stl/cetak/flap.stl`, dan untuk base berkupingan
gunakan dua belahan `base_left.stl` dan `base_right.stl` di `docs/3d/external-gears/stl/cetak/`.
Jumlah cetak tercantum di `stl/cetak/JUMLAH-CETAK.txt`; STL referensi terpisah di `stl/referensi/`.

Seluruh file mekanik dan petunjuk build berada di `docs/3d/external-gears/`;
folder tersebut dapat disalin sendiri. Dasar desain: satu Pi,
webcam USB sekitar 100 × 30 mm, jarak lensa ke flap 30 cm. Target awal sampah 1 kg
ditangguhkan; revisi mekanik terbaru menghitung flap kosong saja.
PCB TT-PZ2 memakai Pi Zero langsung ke dua DRV8825, tanpa Nano.
WS2812 dan IC buffer dihapus; TRIG HC-SR04 langsung 3,3 V dan ECHO tetap memakai pembagi resistor.
Pola transfer PCB NEMA17 ada di [docs/pcb/README.md](docs/pcb/README.md).
Alat yang terpasang masih wiring servo, sebelum motor NEMA17, di [docs/wiring.md](docs/wiring.md).
Tidak ada rel 5 V AUX. OLED dan infrared E18-D80NK mengambil 5 V dari pin 2 dan pin 4 Pi.
Servo mengambil 6,0 V dari catu 5 A di rak bawah, bukan dari pin 5 V Pi. MG996R yang rusak diganti TD8120MG 180°.

Preview dan sorter sekarang memilih **USB** secara default. Isi `.env` dengan
`CAMERA_BACKEND=usb`, `CAMERA_DEVICE=/dev/video0`, dan `CAMERA_FPS=15` (atau path
stabil `/dev/v4l/by-id/...`). Kamera pita lama dapat dipilih dengan
`CAMERA_BACKEND=csi`. Lebar pandangan tetap bergantung lensa webcam.
Pengendali gerak aplikasi masih servo; kendali STEP/DIR langsung dari Pi, homing
dan penanganan FAULT belum diimplementasikan. Jumper JARM PCB baru harus tetap terbuka.

## Kabel Pi Zero (sebelum motor NEMA17)

| Komponen | Dari | Ke |
| --- | --- | --- |
| OLED | VCC | 5 V Pi, pin 2 |
| OLED | SDA / SCL | GPIO 2 / pin 3, GPIO 3 / pin 5 |
| E18-D80NK | Cokelat (VCC) | 5 V Pi, pin 4 |
| E18-D80NK | Hitam (OUT) | 4,7 kΩ ke cokelat / 5 V, lalu 1 kΩ → GPIO 27 / pin 13, 10 kΩ ke GND |
| E18-D80NK | Biru | GND |
| Servo | Sinyal | GPIO 18 / pin 12 dan GPIO 13 / pin 33, kabel 80 cm turun ke rak bawah |
| Servo TD8120MG / MG996R | Merah | +6,0 V catu 5 A di rak bawah, bukan pin 5 V Pi |
| LED hijau / merah | Anoda | GPIO 22 / pin 15, GPIO 23 / pin 16 |
| Buzzer | Sinyal | GPIO 5 / pin 29 |

Gambar susunan, soket AC, dan daftar panjang kabel ada di [docs/wiring.md](docs/wiring.md).

## Dua Pi

Setiap Pi menjalankan program yang sama. Bedanya hanya flap, lewat file `station.txt`.

Di Pi atas:

```text
flap1
```

Di Pi bawah:

```text
flap2
```

Sudut servo ada di `trash2trace/settings.py`. Organik ke kiri (`-60`), nonorganik ke kanan (`+60`), other di tengah (`0`). Ubah angka itu kalau posisi flap di mekanik berbeda.

Sampah dibaca oleh **API bridge** `https://twotrash.wbesoft.com/classify`. Isi `.env` dari `.env.example` dengan `API_TOKEN` yang sama dengan token di server. Saat program menyala, layar monitor terbuka penuh dan menampilkan webcam. Saat HC-SR04 melihat benda, layar menghitung **TUNGGU** selama `PLACE_WAIT_S` (3 detik), baru foto dikirim ke API. Hasil ORGANIK, NONORGANIK, atau LAINNYA tampil di monitor dan OLED. Kalau jawaban API memuat `item` (misalnya `kulit_pisang`, `botol`, atau `kaleng_minuman`), layar menulis nama subkategorinya. Daftarnya ada di `trash2trace/catalog.py`. Servo belum ikut bergerak. Tanpa token atau tanpa internet, foto tetap disimpan dan layar menampilkan GAGAL.

## Menjalankan

Di tiap Pi, sekali saja:

```bash
sudo ./install.sh
sudo reboot
```

Setelah reboot, pemilah menyala sendiri. `station.txt` menentukan flap Pi itu. Cek statusnya dengan:

```bash
systemctl status trash2trace
```

Untuk menjalankan manual dari folder proyek. Layar monitor terbuka sendiri dalam mode penuh. Pi Zero tidak bisa memakai Chromium karena prosesornya tidak punya NEON, jadi jendelanya jendela Python. Sekali saja, kalau belum terpasang: `sudo apt install python3-tk python3-pil.imagetk`.

```bash
python3 -m trash2trace
```

## Tes kamera di browser

Pemilah harus dimatikan dulu, karena kamera hanya bisa dipakai satu program.

```bash
sudo systemctl stop trash2trace
python3 -m trash2trace.preview
```

Untuk menyalakan cincin LED putih selama pratinjau, jalankan dengan sudo. Cincin dan pigpio sama-sama memakai PCM, sedangkan servo butuh `pigpiod` tetap aktif. Supaya keduanya jalan bersamaan, jalankan `pigpiod` dengan timer PWM (`-t 0`) sekali saja:

```bash
sudo systemctl edit pigpiod
```

Isi dengan:

```ini
[Service]
ExecStart=
ExecStart=/usr/bin/pigpiod -l -t 0
```

Lalu `sudo systemctl restart pigpiod`. Pasang library cincin sekali:

```bash
sudo apt install python3-dev gcc
sudo python3 -m pip install --break-system-packages rpi-ws281x
sudo python3 -m trash2trace.preview
```

Uji cepat tanpa browser: `sudo python3 scripts/test_parts.py camera` menyalakan cincin putih, menyimpan satu foto di `captures/`, lalu mematikan cincin.

Buka `http://<nama-pi>.local:8080` dari komputer yang satu Wi-Fi dengan Pi. Gambar kamera ada di kiri. Panel di kanan punya tiga bagian:

- **Ambil dan analisis**: menyimpan satu foto dan membacanya dengan API. Setelah hasilnya muncul, servo bergerak: servo 1 memutar ke -45° (organik) atau +45° (nonorganik) dan tetap di sana, servo 2 turun lalu naik lagi ke tegak, dan setelah jeda beberapa detik servo 1 kembali ke titik awal. Jenis LAINNYA tidak menggerakkan servo. Sudut dan jeda ada di `trash2trace/settings.py` (`SORT_ANGLES`, `TILT_DOWN_DEG`, `SORT_WAIT_S`). Butuh `pigpiod` aktif.
- **Cincin LED**: tombol Putih, Merah, Hijau, Biru dan Mati. Butuh sudo. Kalau cincin tidak bisa dipakai, panel memberi tahu bahwa cincin tidak aktif.
- **API**: mengecek server, lalu mengirim gambar kamera saat ini ke API dan menampilkan ORGANIK, NONORGANIK atau LAINNYA. Servo ikut bergerak seperti pada tombol di atas. Butuh `API_TOKEN` di `.env`. Ctrl+C menghentikan tes. Nyalakan pemilah lagi dengan:

```bash
sudo systemctl start trash2trace
```
