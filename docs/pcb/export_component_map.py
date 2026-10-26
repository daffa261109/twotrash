"""Readable component map and connector guide; does not modify etch geometry."""
import json, hashlib
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A3, landscape
import pymupdf
from export_board import Drawing, ROOT, PDF, SVG, PRE

COLORS={'connector':'#c6e0ef','module':'#dfd0ef','ic':'#cbd5e1',
        'resistor':'#f6dfad','capacitor':'#c9e6d5','transistor':'#d5dbe4','diode':'#e3d7ca'}

def center(d,x,y,s,size=1.5,color='#17384b'):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    d.text(x-stringWidth(s,'Helvetica',size)/2,y,s,size,color)

def draw_map(d,b):
    d.rect(0,0,140,100,'#526c7c','#f7faf9',.25)
    # Jumper holes remain visible but do not compete with component labels.
    for p in b['pads']:
        if p['ref'].startswith('W'):
            d.circle(p['x'],p['y'],.55,'#f0e9db','#c8baa0',.12)
    for x,y in b['mounts']:d.circle(x,y,1.6,'#ffffff','#526c7c',.2)
    for c in b['components']:
        x0,y0,x1,y1=c['body'];cx=(x0+x1)/2;cy=(y0+y1)/2
        ref=c['ref'];kind=c['kind'];ps=[p for p in b['pads'] if p['ref']==ref]
        d.rect(x0,y0,x1-x0,y1-y0,'#526c7c',COLORS[kind],.18)
        for p in ps:
            d.circle(p['x'],p['y'],.72,'#ffffff','#6e8391',.14)
            if p['pin'] in ['1','L1']:d.circle(p['x'],p['y'],.4,'#1265bc')
        if ref=='JPI':
            d.text(x1+3,12,'JPI - GPIO Pi Zero / IDC 40 pin',1.9,angle=90)
            d.text(x0+1,7.9,'1',1.6,'#1265bc')
        elif kind=='module':
            center(d,cx,cy-1,ref,1.9);center(d,cx,cy+2,'DRV8825',1.8)
            d.text(x0,y0-1,'EN',1.5);d.text(x1-4,y0-1,'VMOT',1.5)
        elif ref=='U1':
            d.text(cx+.6,y0+3,'U1  AHCT125',1.8,angle=90)
            d.line([[cx-1,y0+.2],[cx,y0+1.2],[cx+1,y0+.2]],.3,'#17384b')
        elif kind=='resistor':
            vertical=y1-y0>x1-x0
            if vertical:
                d.text(x0-1, y1, ref+' '+c['value'],1.5,angle=-90)
            else:
                center(d,cx,y0-.9,ref+' '+c['value'],1.5)
        elif kind=='capacitor':
            # Long references use the spacious side of the footprint.
            if ref.startswith('C_H'):
                d.text(x1+1,cy+.5,ref,1.35)
                center(d,cx,y1+2,'100nF',1.4)
            elif ref in ['C_PAN','C_TILT']:
                d.text(x0-2,y0-1,ref,1.4)
                center(d,cx,cy+1,'100uF',1.4)
                center(d,cx,y1+2.2,'35V',1.5)
            elif ref=='C2':
                center(d,cx,cy-.4,'C2',1.5);center(d,cx,cy+2,'1000uF',1.45)
                center(d,cx,y1+2,'16V',1.5)
            else:
                d.text(x1+1,y1+3,'C1 100nF',1.4)
            if 'uF' in c['value']:
                p=next(p for p in ps if p['pin']=='1')
                d.text(p['x']-1.8,p['y']-1.3,'+',1.8,'#b04425')
        elif ref=='Q1':
            center(d,cx,y0-1,'Q1 2N3904',1.5)
            for p,lab in zip(ps,['E','B','C']):center(d,p['x'],y1+2,lab,1.4)
        elif ref=='D1':
            center(d,cx,y0-1,'D1 1N4148',1.5)
            p=next(p for p in ps if p['pin']=='1')
            d.line([[p['x']+1,y0],[p['x']+1,y1]],.45,'#17384b')
            d.text(x0+.3,y1+2,'K',1.4)
        else:
            if ref in ['JOLED','JHC']:
                d.text(x1+1,y0+1,ref,1.6)
                for p in ps:center(d,x0-1.7,p['y']+.5,p['pin'],1.35)
            elif ref.startswith('JM_'):
                d.text(x0-1.2,y0-1,ref,1.6)
                for p in ps:d.text(x1+1,p['y']+.5,p['label'],1.5)
            else:
                pos={
                    'J5V':(x0,1.1),'JRING':(x0,1.1),'J12V':(x0,1.1),
                    'JBUZ':(x0,y0-1),'JARM':(x0,y0-1),
                    'JH_PAN':(x0-1,y1+2.1),'JH_TILT':(x0-1,y1+2.1),
                }.get(ref,(x0,y0-1))
                d.text(*pos,ref,1.5)
                if ref in ['J5V','J12V']:
                    center(d,cx,y1+2,'+  GND',1.4)
    d.text(5,98,'TT-PZ1 / TAMPAK ATAS / 140 x 100 mm',1.8)

def start(c):
    c.saveState();c.translate(0,297*mm);c.scale(mm,-mm)
    return Drawing(c)

def main():
    b=json.loads((ROOT/'board.json').read_text())
    copper_before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['board.json','output/pdf/01-transfer-toner-1to1.pdf','output/pdf/02-tembaga-bawah-inspeksi.pdf']}
    path=PDF/'04-peta-komponen-jelas.pdf'
    c=canvas.Canvas(str(path),pagesize=landscape(A3))
    d=start(c)
    d.text(12,17,'Peta komponen PCB TwoTrash',6)
    d.text(12,25,'Pi Zero + dua DRV8825. Tampak dari sisi komponen, bukan sisi tembaga.',3.4)
    d.text(12,32,'Gambar diperbesar 2x pada A3. Untuk panduan pemasangan, BUKAN pola transfer toner.',3.1,'#a34c24')
    d.text(12,40,'Kode pada papan cocok dengan daftar di kanan. Titik biru = kaki 1.',3.1)
    c.saveState();c.translate(12,48);c.scale(2,2)
    bd=Drawing(c);draw_map(bd,b);c.restoreState()
    d.text(302,40,'KODE / KOMPONEN',3.8)
    short={'JPI':'GPIO Pi / IDC 40 pin','J5V':'Masuk 5V AUX','J12V':'Masuk 12V motor',
      'JBUZ':'Buzzer aktif 5V, <=50mA','U1':'SN74AHCT125N DIP14','Q1':'2N3904, E-B-C',
      'D1':'1N4148, garis = K','JARM':'Jumper enable; biarkan terbuka'}
    for i,x in enumerate(b['components']):
        y=47+i*5.65
        d.rect(302,y-3.5,2,3.5,COLORS[x['kind']],COLORS[x['kind']],.1)
        d.text(306,y,x['ref'],2.75)
        value=short.get(x['ref'],x['value'])
        d.text(327,y,value,2.7)
    d.text(12,260,'Warna: biru konektor | ungu driver | kuning resistor | hijau kapasitor | abu IC/transistor.',3.2)
    d.text(12,267,'Elko: + ke kaki 1. Dioda D1: garis katoda K ke kaki 1. IC U1: takik menghadap atas.',3.2)
    d.text(12,274,'Driver: EN kiri atas, VMOT kanan atas. Cocokkan tulisan pin modul; jangan mengandalkan warna PCB.',3.2)
    d.text(12,281,'28 jumper berisolasi tetap wajib dipasang: lihat panduan 03. Komponen periferal terhubung lewat kabel.',3.2)
    d.text(12,289,'Sumber: board.json, pinmap.json dan wiring.md / TT-PZ1 / Halaman 1 dari 2',2.6,'#64748b')
    c.restoreState();c.showPage()
    # Save the same annotated overview as an SVG for project documentation.
    svg=''.join(d.svg)+f'<g transform="translate(12 48) scale(2)">{"".join(bd.svg)}</g>'
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297"><rect width="420" height="297" fill="white"/>{svg}</svg>'
    (SVG/'peta-komponen-jelas.svg').write_text(svg)
    (ROOT.parent/'diagram-pcb.svg').write_text(svg)
    d=start(c)
    d.text(12,17,'Konektor dan arah pemasangan',6)
    d.text(12,26,'Urutan di bawah mengikuti nomor pad, dilihat dari ATAS. Titik biru pada peta adalah pad 1.',3.4)
    d.rect(12,34,396,9,'#23466b','#23466b')
    for x,t in [(15,'KODE'),(48,'UNTUK'),(115,'URUTAN KAKI 1 -> TERAKHIR'),(285,'CATATAN')]:d.text(x,40,t,3.2,'#ffffff')
    labels={'JPI':'Pi Zero','J5V':'Daya AUX','J12V':'Daya motor','JOLED':'OLED','JHC':'HC-SR04','JGREEN':'LED hijau','JRED':'LED merah','JBUZ':'Buzzer','JRING':'Ring WS2812','JM_PAN':'Motor pan','JM_TILT':'Motor tilt','JARM':'Aktifkan driver','JH_PAN':'Home pan','JH_TILT':'Home tilt'}
    orders={'JPI':'IDC 40 pin, kabel lurus 1-ke-1','J5V':'+5V AUX / GND','J12V':'+12V / GND','JOLED':'GND / 3,3V / SCL / SDA','JHC':'+5V / TRIG / ECHO / GND','JGREEN':'Anoda (+) / katoda (-)','JRED':'Anoda (+) / katoda (-)','JBUZ':'+5V / negatif ke transistor','JRING':'+5V / GND / DIN','JM_PAN':'B2 / B1 / A1 / A2','JM_TILT':'B2 / B1 / A1 / A2','JARM':'GPIO ENABLE / EN kedua driver','JH_PAN':'Input HOME / GND','JH_TILT':'Input HOME / GND'}
    notes={'JPI':'Pin 2/4 Pi tidak memasok AUX.','J5V':'Sekring eksternal 1,5A.','J12V':'Sekring eksternal 2A.','JOLED':'Modul harus mendukung 3,3V.','JHC':'ECHO memakai pembagi tegangan.','JBUZ':'Aktif 5V, dua kaki, <=50mA.','JRING':'12 LED, suplai 5V.','JM_PAN':'Cari pasangan lilitan dengan ohmmeter.','JM_TILT':'Jangan cabut motor saat hidup.','JARM':'Tetap TERBUKA hingga firmware siap.','JH_PAN':'Hubungkan kontak COM dan NC.','JH_TILT':'Hubungkan kontak COM dan NC.'}
    for i,ref in enumerate(labels):
        y=51+i*10
        if i%2==0:d.rect(12,y-6,396,10,'#edf3f7','#edf3f7',0)
        for x,t in [(15,ref),(48,labels[ref]),(115,orders[ref]),(285,notes.get(ref,''))]:d.text(x,y,t,3.2)
    for y,text in [(201,'Resistor: semua 1/4W, 1%. Nilai 2k2 = 2,2 kohm; 2k7 = 2,7 kohm; 330R = 330 ohm.'),
      (210,'C1, C_HPAN, C_HTILT: 100nF keramik, tanpa polaritas. C2: 1000uF 16V, perhatikan + / -.'),
      (219,'C_PAN dan C_TILT: 100uF 35V. Kaki 1 positif. Cocokkan ukuran badan elko dengan ruang pada PCB.'),
      (228,'D1: garis pada badan dioda adalah katoda K. Q1: pad 1=E, 2=B, 3=C dari kiri ke kanan.'),
      (237,'U1: SN74AHCT125N DIP14, bukan 74HC125. Gunakan soket DIP14, takik di sisi atas peta.'),
      (246,'DRV8825: 4 soket female 1x8; pitch 2,54mm; tinggi >=8,5mm; jarak antarbaris 15,24mm.'),
      (255,'Acuan orientasi driver: EN kiri atas, VMOT kanan atas. Jauhkan heatsink dari pin dan trimpot.'),
      (264,'Webcam USB dan Pi berada di luar PCB. USB kamera melalui adaptor OTG langsung ke Pi.'),
      (273,'Gambar menunjukkan batas footprint, bukan jaminan bentuk semua merek komponen identik.')]:d.text(12,y,text,3.3)
    d.text(12,289,'Panduan 04 / TT-PZ1 / Halaman 2 dari 2. Untuk bor dan 28 jumper, gunakan panduan 03.',2.8,'#64748b')
    c.restoreState();c.showPage();c.save()
    doc=pymupdf.open(path)
    for i,p in enumerate(doc):
        p.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(PRE/f'04-peta-komponen-jelas-p{i+1}.png')
        for block in p.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for sp in line['spans']:
                    box=pymupdf.Rect(sp['bbox']);assert p.rect.contains(box),(i,sp['text'],box)
    alltext='\n'.join(p.get_text() for p in doc)
    assert all(c['ref'] in alltext for c in b['components'])
    for p,h in copper_before.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    result={'component_count':len(b['components']),'pages':len(doc),'page_size':'A3 landscape','map_scale':2,'all_references_listed':True,'text_within_pages':True,'copper_geometry_and_transfer_files_unchanged':True,'source_board_sha256':copper_before['board.json']}
    (ROOT/'component-map-check.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
