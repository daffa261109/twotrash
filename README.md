# Pi Zero

Program Python untuk Raspberry Pi Zero. Wiring lengkap ada di [docs/wiring.md](docs/wiring.md).

## Kabel

| Komponen | Dari | Ke |
| --- | --- | --- |
| OLED | SDA / SCL | GPIO 2 / pin 3, GPIO 3 / pin 5 |
| HC-SR04 | TRIG / ECHO | GPIO 17 / pin 11, GPIO 27 / pin 13 lewat pembagi |
| Servo | Sinyal | GPIO 18 / pin 12, kabel 80 cm turun ke rak bawah |
| Servo | Merah | +5 V catu di rak bawah, bukan pin 5 V Pi |
| LED hijau / merah | Anoda | GPIO 22 / pin 15, GPIO 23 / pin 16 |
| Cincin WS2812 12 LED | DIN | GPIO 21 / pin 40, 5 V dari catu bawah |
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

Sampah dibaca oleh **Sumopod AI** lewat internet. Model lokal MobileNet tidak dipakai lagi. Isi `.env` dari `.env.example` dengan `LLM_API_KEY` Sumopod. Saat HC-SR04 melihat benda, mesin mengambil satu foto, mengirimnya ke Sumopod, lalu menampilkan ORGANIK, NONORGANIK atau LAINNYA di OLED dan mencatatnya di log sebagai `[AI] Sumopod`. Servo belum ikut bergerak. Tanpa kunci atau tanpa internet, foto tetap disimpan dan OLED menampilkan "AI GAGAL".

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

Untuk menjalankan manual dari folder proyek:

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

- **Ambil dan analisis**: menyimpan satu foto dan membacanya dengan Sumopod AI. Setelah hasilnya muncul, servo bergerak: servo 1 memutar ke -45° (organik) atau +45° (nonorganik) dan tetap di sana, servo 2 turun lalu naik lagi ke tegak, dan setelah jeda beberapa detik servo 1 kembali ke titik awal. Jenis LAINNYA tidak menggerakkan servo. Sudut dan jeda ada di `trash2trace/settings.py` (`SORT_ANGLES`, `TILT_DOWN_DEG`, `SORT_WAIT_S`). Butuh `pigpiod` aktif.
- **Cincin LED**: tombol Putih, Merah, Hijau, Biru dan Mati. Butuh sudo. Kalau cincin tidak bisa dipakai, panel memberi tahu bahwa cincin tidak aktif.
- **API Sumopod**: mengecek koneksi dan kunci, lalu mengirim gambar kamera saat ini ke Sumopod dan menampilkan label, keyakinan dan waktu respons. Servo ikut bergerak seperti pada tombol di atas. Butuh `LLM_API_KEY` di `.env`. Ctrl+C menghentikan tes. Nyalakan pemilah lagi dengan:

```bash
sudo systemctl start trash2trace
```
