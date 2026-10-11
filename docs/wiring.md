# Wiring Pi Zero

Mesin memakai **dua Raspberry Pi Zero**. Keduanya dikabel sama. Pi pertama mengurus Flap 1 (kamera dan servo atas). Pi kedua mengurus Flap 2 (kamera dan servo di atas tong kuning dan hijau).

Komponen terpasang pada header Pi, bukan pada port USB komputer.

Ground Pi, ground catu servo, dan kaki GND setiap komponen disatukan.

## Sambungan

| Komponen | Dari | Ke |
| --- | --- | --- |
| OLED | VCC | 5 V (pin 2) |
| OLED | GND | GND |
| OLED | SDA | GPIO 2 / pin 3 |
| OLED | SCL | GPIO 3 / pin 5 |
| HC-SR04 | VCC | 5 V (pin 4) |
| HC-SR04 | GND | GND |
| HC-SR04 | TRIG | GPIO 17 / pin 11 |
| HC-SR04 | ECHO | resistor 1 kΩ → GPIO 27 / pin 13 |
| Pembagi tegangan | resistor 2 kΩ | GND |
| Servo | Signal | GPIO 18 / pin 12 |
| Servo | Merah | +5 V eksternal |
| Servo | Cokelat/hitam | GND bersama |
| LED hijau | Anoda | resistor → GPIO 22 / pin 15 |
| LED hijau | Katoda | GND |
| LED merah | Anoda | resistor → GPIO 23 / pin 16 |
| LED merah | Katoda | GND |
| Buzzer | Signal | GPIO 5 / pin 29 |
| Buzzer | − | GND |
| LED illumination | Anoda | resistor → GPIO 24 / pin 18 |
| LED illumination | Katoda | GND |

Pin di kode ada di `servo/pins.py`.

## Pembagi ECHO

Kaki ECHO sensor HC-SR04 mengeluarkan 5 V. GPIO Pi hanya tahan 3,3 V. Sambungannya:

```
ECHO ---- 1 kΩ ---- GPIO 27 / pin 13
                      |
                     2 kΩ
                      |
                     GND
```

Jangan menyambungkan ECHO langsung ke pin 13.

## Daya

Pin 5 V Pi (pin 2 dan pin 4) untuk OLED dan HC-SR04.

Kabel merah servo **tidak** masuk ke pin 5 V Pi. Servo MG996R mengambil +5 V dari catu eksternal minimal 3 A. Negatif catu itu ikut ke GND bersama.

LED illumination menyala dari GPIO 24 lewat resistor 330 Ω, sama seperti LED indikator. Lampu yang menarik arus besar tidak diambil dari pin GPIO.

Resistor pada LED hijau dan LED merah diperlukan. Nilai yang aman untuk LED indikator biasa adalah 330 Ω.

## Urutan

1. Matikan Pi dan catu servo.
2. Pasang kabel sesuai tabel. Cek ECHO sudah lewat pembagi, dan kabel merah servo hanya ke catu eksternal.
3. Nyalakan Pi.
4. Nyalakan catu servo setelah Pi hidup.
5. Hentikan program sebelum mencabut kabel.
