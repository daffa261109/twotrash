# Pi Zero — servo MG996R

Program Python untuk menggerakkan **satu servo MG996R** dari Raspberry Pi Zero.

Wiring ada di [docs/wiring.md](docs/wiring.md).

## Kabel

| Servo | Kabel | Tujuan |
| --- | --- | --- |
| Servo | Signal | GPIO 18 / pin 12 |
| Servo | Merah | +5 V eksternal (minimal 3 A) |
| Servo | Cokelat/hitam | GND bersama (pin 6 Pi dan negatif catu) |

Kabel merah tidak disambungkan ke pin 5 V Pi. MG996R bisa menarik arus sampai sekitar 2,5 A saat poros tertahan.

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
