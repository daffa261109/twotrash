"""Generate the system diagrams referenced by wiring.md; these are not etch masks."""
from pathlib import Path
from html import escape
R=Path(__file__).resolve().parent.parent

def diagram(name,title,subtitle,boxes,lines):
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">','<rect width="1200" height="760" fill="#f4f7fa"/>','<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#668194"/></marker></defs>']
    s.append(f'<text x="35" y="48" font-family="Arial" font-size="29" font-weight="bold" fill="#17384b">{escape(title)}</text>')
    s.append(f'<text x="35" y="80" font-family="Arial" font-size="16" fill="#536b7c">{escape(subtitle)}</text>')
    for points,label,x,y in lines:
        s.append(f'<polyline points="{points}" fill="none" stroke="#668194" stroke-width="2.5" marker-end="url(#arrow)"/>')
        s.append(f'<text x="{x}" y="{y}" font-family="Arial" font-size="14" fill="#354f60">{escape(label)}</text>')
    for x,y,w,h,head,body,color in boxes:
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="white" stroke="{color}" stroke-width="2"/>')
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="36" rx="10" fill="{color}"/>')
        s.append(f'<text x="{x+14}" y="{y+25}" font-family="Arial" font-size="17" font-weight="bold" fill="white">{escape(head)}</text>')
        for i,line in enumerate(body):s.append(f'<text x="{x+14}" y="{y+61+i*23}" font-family="Arial" font-size="15" fill="#17384b">{escape(line)}</text>')
    s.append('<text x="35" y="733" font-family="Arial" font-size="15" fill="#9d5227">TT-PZ2 | Pi Zero langsung ke DRV8825 | Prototipe flap kosong | PCB tidak membawa PLN</text></svg>')
    (R/name).write_text(''.join(s))

blue='#275e80';green='#247966';gold='#976817'
diagram('diagram-daya.svg','Daya DC terpisah, ground bersama','Kamera USB dan motor tidak mengambil daya dari GPIO Pi.',[
(35,125,290,140,'Catu Pi 5 V USB',['Ke port PWR IN Pi Zero.','Tidak disatukan dengan 5 V AUX.','Pakai catu/kabel yang sesuai Pi.'],blue),
(435,125,290,140,'Raspberry Pi Zero',['GPIO 40 pin ke PCB: 3V3,','GND dan sinyal saja.','Pin 5V #2/#4 tidak dirutekan.'],blue),
(835,125,325,140,'Webcam komputer USB',['Ke port USB/OTG Pi.','Kabel USB utuh, bukan jalur etsa.','Lensa sekitar 30 cm dari flap.'],blue),
(35,320,290,140,'Adaptor 12 V DC / 3 A',['Sekring eksternal 2 A.','J12V: pin1 +12V, pin2 GND.','Jangan langsung ke lilitan motor.'],gold),
(435,320,290,140,'Dua modul DRV8825',['VMOT 12V, input logika 3V3.','100uF / 35V per driver.','Heatsink + aliran udara.'],gold),
(835,320,325,140,'Dua NEMA17 42HD4027-01',['JM: B2, B1, A1, A2.','Pasangan lilitan diuji ohmmeter.','Batas arus awal 1.0A; maks 1.5A.'],gold),
(35,515,290,140,'Catu periferal 5 V / 2 A',['Sekring eksternal 1.5 A.','J5V: pin1 +5V, pin2 GND.','Ground terhubung GND PCB.'],green),
(435,515,290,140,'Bagian periferal PCB',['HC TRIG langsung GPIO17.','Buzzer lewat transistor.','Tanpa ring dan IC buffer.'],green),
(835,515,325,140,'Sensor dan indikator',['HC-SR04 dan buzzer: 5V AUX.','OLED: 3V3 dari Pi.','LED indikator: resistor 330R.'],green)],
[('325,195 435,195','USB power',345,180),('835,195 725,195','USB data',745,180),('325,390 435,390','12V + GND',335,375),('725,390 835,390','4 kabel/motor',730,375),('325,585 435,585','5V + GND',340,570),('725,585 835,585','konektor PCB',735,570)])
diagram('diagram-sinyal.svg','Sinyal Pi Zero ke PCB TT-PZ2','Nomor BCM untuk program; nomor pin fisik untuk kabel JPI. Tidak ada Arduino Nano.',[
(35,125,330,530,'Raspberry Pi / BCM',['PAN STEP 18 / DIR 12','TILT STEP 13 / DIR 19','ENABLE 26, LOW = aktif','FAULT pan 20 / tilt 25','HOME pan 6 / tilt 16','','I2C SDA 2 / SCL 3','HC TRIG 17 / ECHO 27','GPIO21 / pin40 tidak dipakai','LED hijau 22 / merah 23','Buzzer 5','','3V3 pin1, GND pin6','Kabel IDC40 1-ke-1, 10-15 cm.'],blue),
(490,125,310,175,'Kendali dua motor',['JARM terbuka = tidak diaktifkan.','R_EN 2k2 menarik EN ke 3V3.','M0/M1=0, M2=1: 1/16 step.','RESET/SLEEP ke 3V3 Pi.','STEP/DIR langsung: level 3V3.'],gold),
(885,125,280,175,'DRV_PAN / DRV_TILT',['EN pojok kiri atas modul.','VMOT pojok kanan atas.','Header 2x8, pitch 2.54.','Jarak dua baris 15.24 mm.'],gold),
(490,350,310,135,'Home dan FAULT',['Home: COM/NC ke GND.','R 10k pull-up + C 100nF.','Terpicu/kabel putus = HIGH.'],blue),
(885,350,280,135,'Microswitch + driver',['Dua switch home terpisah.','FAULT per driver: LOW.','Jangan menyatukan FAULT.'],blue),
(490,535,310,120,'Sensor dan lampu',['ECHO: pembagi 2k2 / 2k7.','TRIG: GPIO17 langsung 3V3.','LED/buzzer lewat pembatas.'],green),
(885,535,280,120,'Periferal lama',['OLED pada 3V3.','HC-SR04: 5V AUX.','Buzzer aktif 2pin <=50mA.'],green)],
[('365,185 490,185','STEP / DIR / EN',370,170),('800,210 885,210','logika 3V3',803,194),('490,420 365,420','input home/fault',370,406),('885,420 800,420','kontak / FAULT',800,405),('365,590 490,590','GPIO periferal',375,575),('800,590 885,590','konektor',808,576)])
