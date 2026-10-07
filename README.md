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

## Menjalankan di Pi

```bash
sudo apt install python3-gpiozero python3-pigpio
sudo systemctl enable --now pigpiod
python3 -m servo center
python3 -m servo angle --degrees 45
python3 -m servo sweep
python3 -m servo off
```

`center` dan `angle` menahan posisi sampai Ctrl+C. Tambah `--seconds 2` kalau hanya ingin menahan sebentar.

Di luar Raspberry Pi, perintah yang sama berjalan sebagai dry-run dan hanya mencetak sudut.
