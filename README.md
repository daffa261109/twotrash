# Pi Zero

Program Python untuk Raspberry Pi Zero. Wiring lengkap ada di [docs/wiring.md](docs/wiring.md).

## Kabel

| Komponen | Dari | Ke |
| --- | --- | --- |
| OLED | SDA / SCL | GPIO 2 / pin 3, GPIO 3 / pin 5 |
| HC-SR04 | TRIG / ECHO | GPIO 17 / pin 11, GPIO 27 / pin 13 lewat pembagi |
| Servo | Signal | GPIO 18 / pin 12 |
| Servo | Merah | +5 V eksternal |
| LED hijau / merah | Anoda | GPIO 22 / pin 15, GPIO 23 / pin 16 |
| Buzzer | Signal | GPIO 5 / pin 29 |

Kabel komponen masuk ke header Pi, bukan ke port USB komputer. Kabel merah servo tidak disambungkan ke pin 5 V Pi.

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

Satu foto dianalisis di Pi dengan **MobileNetV3-Small**. Unduh berkasnya sekali:

```bash
python3 scripts/download_models.py
```

Hasil bacaan model ditulis ke log sebagai `[MODEL]`. Servo belum ikut bergerak. Plastik, kertas, dan kaca dihitung nonorganik bila nama kelasnya ada di label model.

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

Buka `http://<nama-pi>.local:8080` dari komputer yang satu Wi-Fi dengan Pi. Gambar kamera ada di kiri. Tekan **Ambil dan analisis** untuk menyimpan satu foto dan membacanya dengan MobileNet di Pi. Hasilnya muncul di kanan. Ctrl+C menghentikan tes. Nyalakan pemilah lagi dengan:

```bash
sudo systemctl start trash2trace
```
