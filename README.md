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

Kamera mengirim foto ke LLM. Salin `.env.example` menjadi `.env`, lalu isi empat nilai ini:

```text
LLM_PROVIDER=openai
LLM_ENDPOINT=https://api.openai.com/v1
LLM_API_KEY=kunci-dari-penyedia
LLM_MODEL=gpt-4.1-mini
```

`LLM_ENDPOINT` harus menerima permintaan gaya OpenAI ke `/chat/completions`. Foto hanya dikirim saat sensor melihat sampah.

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
