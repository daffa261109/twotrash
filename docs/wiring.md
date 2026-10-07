# Wiring MG996R ke Raspberry Pi Zero

Servo yang dipakai **TowerPro MG996R** (atau klon sejenis): servo posisi, tiga kabel, torsi besar. Sudut diatur lebar pulsa dari GPIO. Tidak memakai driver L298N.

Daya servo **wajib dari +5 V eksternal**. MG996R menarik sekitar 0,5–0,9 A saat bergerak dan bisa sampai **2,5 A** jika poros tertahan. Pin 5 V Pi Zero tidak kuat memasok arus itu dan Pi bisa restart.

Raspberry Pi Zero, Zero W, dan Zero 2 W memakai header 40 pin yang sama. Sebagian papan datang tanpa pin header; solder header dulu sebelum memasang kabel.

## Sambungan

| Servo | Kabel | Tujuan |
| --- | --- | --- |
| Servo | Signal (biasanya oranye) | GPIO 18 / pin 12 |
| Servo | Merah | +5 V eksternal |
| Servo | Cokelat/hitam | GND bersama |

Sinyal GPIO 3,3 V diterima MG996R. Tidak perlu level shifter. Jangan sambungkan kabel merah ke pin 5 V atau pin 3,3 V Pi.

Catu eksternal: **5 V, minimal 3 A**. Ground catu, ground servo, dan ground Pi harus jadi satu.

```
 Raspberry Pi Zero                  MG996R                Catu +5 V eksternal
 +------------------------+         +------------------+  +------------------+
 | pin 12  GPIO 18        |-------->| Signal           |  |                  |
 | pin 6   GND            |----+--->| Cokelat/Hitam    |  |                  |
 +------------------------+    |    | Merah            |<-+ +5 V             |
                               +--------------------------| GND              |
                                                          +------------------+
```

Jangan menyambungkan +5 V catu eksternal ke pin 2 Pi.

Pin sinyal ada di `servo/pins.py` (`SIGNAL_PIN = 18`).

## Urutan yang aman

1. Matikan Pi dan catu servo.
2. Pasang sinyal ke pin 12, cokelat/hitam ke pin 6 dan ke negatif catu, merah hanya ke +5 V catu.
3. Nyalakan Pi, tunggu sampai siap login.
4. Baru nyalakan catu 5 V servo.
5. Jalankan `center` dulu, baru sudut lain.
6. Hentikan program sebelum mencabut kabel. Ctrl+C melepas pulsa.

Posisi ditahan hanya selama program masih berjalan. Setelah program selesai, pulsa berhenti dan servo tidak lagi menahan sudut.

## Menjalankan

Di Raspberry Pi OS:

```bash
sudo apt update
sudo apt install python3-gpiozero python3-pigpio
sudo systemctl enable --now pigpiod
cd /path/ke/pizero
python3 -m servo center
python3 -m servo angle --degrees 0 --seconds 1
python3 -m servo angle --degrees 180 --seconds 1
python3 -m servo sweep
python3 -m servo off
```

`pigpio` membuat pulsa lebih stabil sehingga MG996R tidak bergetar. Tanpa itu program tetap jalan memakai software PWM.

Di komputer lain, perintah yang sama hanya mencetak sudut dan tidak menggerakkan pin.

## Pulsa MG996R

Frekuensi 50 Hz. Kode mengirim pulsa **0,5 ms** untuk 0 derajat, **1,5 ms** untuk 90 derajat, dan **2,5 ms** untuk 180 derajat. Kalau di ujung servo berdengung atau gigi mentok, jangan ditahan lama di sudut itu.

## Kalau servo tidak bergerak

- Kabel merah belum ke +5 V eksternal, atau catu belum dinyalakan.
- Signal belum ke GPIO 18 / pin 12.
- GND bersama belum tersambung: negatif catu, cokelat/hitam servo, dan pin 6 Pi.
- Program dijalankan di mesin yang bukan Pi, jadi yang keluar hanya baris `[dry-run]`.
