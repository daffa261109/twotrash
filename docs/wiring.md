# Wiring Pi Zero

Mesin punya dua tingkat. Kotak atas memegang elektronik yang dekat kamera. Rak bawah memegang listrik PLN, catu 5 V, dan dua servo.

Masih ada **dua Raspberry Pi Zero**, satu untuk tiap flap. Keduanya dikabel sama. Tiap Pi punya kotak atas sendiri. Kedua servo duduk berdampingan di tengah rak bawah, diikat dengan braket MG996. Kalau Pi ada di atas, kabel ke servo dipotong **80 cm** (jalur terpakai sekitar 70 cm).

![Susunan kotak atas dan rak bawah](rangkaian.jpg)

## Rak bawah

Dari kiri ke kanan: soket AC, catu switching 5 V, lalu dua servo di tengah.

| Komponen | Dari | Ke |
| --- | --- | --- |
| Soket AC | L | sekring, lalu saklar, lalu L catu |
| Soket AC | N | N catu |
| Soket AC | PE | baut rangka logam, atau diisolasi jika kotak semua plastik |
| Catu 5 V | +V | kabel merah kedua servo, dan kabel 5 V naik ke tiap cincin LED |
| Catu 5 V | −V | kabel cokelat kedua servo, GND tiap Pi, dan GND tiap cincin |
| Servo flap 1 | sinyal | GPIO 18 / pin 12 pada Pi atas, kabel 80 cm |
| Servo flap 2 | sinyal | GPIO 18 / pin 12 pada Pi bawah, kabel 80 cm |

Kabel merah servo tidak masuk ke pin 5 V Pi. Pi tetap makan dari kabel USB-nya sendiri.

Catu di foto adalah 5 V 2 A. Itu cukup untuk cincin LED, tetapi dua servo MG996R saat macet menarik jauh di atas 2 A. Untuk rak bawah ini pakai catu **5 V 5 A** dengan bentuk yang sama. Jangan membebani unit 2 A dengan kedua servo.

## Kotak atas

Kotak plastik 160 × 130 × 45 mm. Isinya satu Pi Zero, kamera, cincin LED, HC-SR04, OLED, buzzer, LED hijau, LED merah, dan PCB lubang 2 × 8 cm.

Pi Zero lebih besar dari PCB itu, jadi Pi tidak ditumpang di atas PCB. PCB memegang resistor, buzzer, LED indikator, dan header. Kamera, cincin, sensor jarak, dan OLED dipasang di dinding kotak, lalu kawatnya masuk ke header PCB.

Cincin yang dibeli adalah **WS2812 12 LED**. Pasang mengelilingi lensa kamera. Lampu satu LED di GPIO 24 tidak dipakai pada rakitan ini. Data cincin masuk ke GPIO 21 / pin 40.

| Komponen | Dari | Ke |
| --- | --- | --- |
| OLED | VCC | 5 V Pi (pin 2) |
| OLED | GND | GND |
| OLED | SDA | GPIO 2 / pin 3 |
| OLED | SCL | GPIO 3 / pin 5 |
| HC-SR04 | VCC | 5 V Pi (pin 4) |
| HC-SR04 | GND | GND |
| HC-SR04 | TRIG | GPIO 17 / pin 11 |
| HC-SR04 | ECHO | 1 kΩ → GPIO 27 / pin 13, lalu 2 kΩ ke GND |
| LED hijau | anoda | 330 Ω → GPIO 22 / pin 15 |
| LED merah | anoda | 330 Ω → GPIO 23 / pin 16 |
| Buzzer | sinyal | GPIO 5 / pin 29 |
| Cincin 12 LED | 5 V | +V catu bawah, kabel 80 cm |
| Cincin 12 LED | GND | −V catu bawah |
| Cincin 12 LED | DIN | 330 Ω → GPIO 21 / pin 40 |
| Servo Pi ini | sinyal | GPIO 18 / pin 12, kabel 80 cm turun |

Pin sinyal ada di `servo/pins.py`.

## Isi PCB 2 × 8 cm

Papan ini berbaring di dasar kotak, di samping Pi, sisi panjang 8 cm menghadap header Pi. Jangan menaruh Pi, kamera, cincin, badan HC-SR04, atau modul OLED di atas papan. Bagian itu menempel di dinding kotak. Yang masuk ke lubang PCB hanya resistor, buzzer kecil, dan pin header.

Tiga jalur disolder memanjang, tidak saling tersambung:

| Jalur | Isi | Tidak disambung ke |
| --- | --- | --- |
| GND | semua ground di kotak, termasuk GND Pi dan GND kabel 80 cm dari catu bawah | — |
| 5 V Pi | VCC OLED dan VCC HC-SR04, dari pin 2 atau pin 4 | jalur 5 V catu |
| 5 V catu | hanya kaki 5 V cincin, dari kabel 80 cm | pin 5 V Pi |

Ground memang berkumpul di jalur GND pada PCB ini. Satu kawat dari situ ke pin GND Pi. Satu kawat 80 cm dari situ ke −V catu di bawah. Itulah sambungan ground bersama.

Urutan dari kiri ke kanan pada papan:

1. Header dupont ke Pi.
2. Pembagi ECHO: 1 kΩ lalu 2 kΩ. Ujung bawah 2 kΩ ke jalur GND.
3. Dua resistor 330 Ω untuk LED hijau dan LED merah. Katoda LED ke jalur GND.
4. Satu resistor 330 Ω untuk data cincin. Keluar ke DIN.
5. Buzzer, kaki negatif ke jalur GND.
6. Di ujung kanan, tiga sekrup atau header untuk kabel 80 cm: sinyal servo, GND, dan 5 V catu.

LED hijau, LED merah, dan buzzer boleh menempel di dinding kotak. Kakinya yang masuk ke PCB, bukan badannya, jika tempat di papan sudah penuh.

## Pembagi ECHO

ECHO HC-SR04 mengeluarkan 5 V. GPIO hanya tahan 3,3 V.

```
ECHO ---- 1 kΩ ---- GPIO 27 / pin 13
                      |
                     2 kΩ
                      |
                     GND
```

Resistor ini duduk di PCB lubang. Jangan menyambung ECHO langsung ke pin 13.

## Kebutuhan kabel

Panjang di bawah sudah termasuk sedikit lebih untuk dilipat di ujung. Kabel 80 cm adalah jalur Pi di atas ke rak bawah.

### Di rak bawah, pendek

| Kabel | Jumlah | Panjang | Kawat | Sambungan |
| --- | --- | --- | --- | --- |
| Fasa | 1 | 15 cm | 0,75 mm² | L soket, lewat sekring dan saklar, ke L catu |
| Netral | 1 | 15 cm | 0,75 mm² | N soket ke N catu |
| Bumi | 1 | 15 cm | 0,75 mm² | PE soket ke rangka logam, atau diisolasi |
| 5 V servo | 2 | 20 cm | 0,75 mm² | +V catu ke merah tiap servo |
| GND servo | 2 | 20 cm | 0,75 mm² | −V catu ke cokelat tiap servo |

### Naik ke kotak atas

Tiap Pi punya satu set. Untuk dua Pi, gandakan baris ini.

| Kabel | Jumlah per Pi | Panjang | Kawat | Sambungan |
| --- | --- | --- | --- | --- |
| Sinyal servo | 1 | 80 cm | 0,25 mm² | GPIO 18 ke kabel oranye/kuning servo |
| GND pasangan servo | 1 | 80 cm | 0,5 mm² | GND Pi ke −V catu, dipilin dengan sinyal |
| 5 V cincin | 1 | 80 cm | 0,5 mm² | +V catu ke 5 V cincin |
| GND cincin | 1 | 80 cm | 0,5 mm² | −V catu ke GND cincin |

Jangan memakai kabel dupont tipis untuk 5 V cincin sepanjang 80 cm. Dua belas LED putih menarik kira-kira 0,7 A.

### Di dalam kotak, 15 cm

| Kabel | Jumlah per kotak | Kawat | Catatan |
| --- | --- | --- | --- |
| Dupont ke header Pi | 12 | 0,25 mm² | OLED, sensor, LED, buzzer, data cincin, sinyal servo |
| Kabel pita kamera | 1 | pita CSI | dari kamera ke soket kamera Pi, pendek |
| Data cincin | 1 | 0,25 mm² | DIN cincin, lewat 330 Ω, ke GPIO 21 |

## Urutan pasang

1. Cabut PLN dan USB Pi.
2. Ikat dua servo di tengah rak bawah dengan braket. Merah dan cokelat hanya ke catu 5 V.
3. Pasang soket AC. Fasa wajib lewat sekring dulu, baru saklar, baru ke catu. Tutup semua sambungan PLN sebelum kotak ditutup.
4. Naikkan sinyal servo, GND, serta 5 V dan GND cincin sepanjang 80 cm.
5. Di kotak atas, solder pembagi ECHO, resistor LED, dan header pada PCB 2 × 8 cm. Baru kemudian colok ke Pi.
6. Nyalakan USB Pi dulu. Catu 5 V bawah dinyalakan setelah Pi hidup.
7. Hentikan program sebelum melepas kabel.

Program yang sekarang masih menyalakan GPIO 24 untuk lampu lama. Cincin WS2812 di GPIO 21 belum ikut perintah itu.
