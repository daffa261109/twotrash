"""Vector 1:1 etch masks, assembly/drill guide and CSV manufacturing data.
Run after route_board.py AND validate_board.py. Never scales the transfer mask.
"""
from pathlib import Path
import csv,json,html,math,hashlib
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
import pymupdf
ROOT=Path(__file__).resolve().parent
PDF=ROOT/'output/pdf';SVG=ROOT/'output/svg';PRE=ROOT/'previews'

class Drawing:
    def __init__(self,c=None,mirror=False):self.c=c;self.svg=[];self.mirror=mirror
    def color(self,color):
        from reportlab.lib.colors import HexColor
        return HexColor(color)
    def line(self,pts,w,color):
        if self.c:
            self.c.setStrokeColor(self.color(color));self.c.setLineWidth(w);self.c.setLineCap(1);self.c.setLineJoin(1)
            p=self.c.beginPath();p.moveTo(*pts[0])
            for x,y in pts[1:]:p.lineTo(x,y)
            self.c.drawPath(p)
        self.svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in pts)}" fill="none" stroke="{color}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')
    def circle(self,x,y,r,fill,stroke=None,w=.2):
        if self.c:
            self.c.setFillColor(self.color(fill));self.c.setStrokeColor(self.color(stroke or fill));self.c.setLineWidth(w);self.c.circle(x,y,r,fill=1,stroke=int(stroke is not None))
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke or fill}" stroke-width="{w}"/>')
    def rect(self,x,y,w,h,color,fill=None,lw=.2):
        if self.c:
            self.c.setStrokeColor(self.color(color));self.c.setLineWidth(lw)
            if fill:self.c.setFillColor(self.color(fill))
            self.c.rect(x,y,w,h,stroke=1,fill=int(fill is not None))
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill or "none"}" stroke="{color}" stroke-width="{lw}"/>')
    def text(self,x,y,text,size=1.5,color='#17384b',angle=0):
        if self.c:
            self.c.saveState();self.c.translate(x,y);self.c.rotate(angle);self.c.scale(1,-1);self.c.setFont('Helvetica',size);self.c.setFillColor(self.color(color));self.c.drawString(0,0,text);self.c.restoreState()
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Arial,sans-serif" font-size="{size}" fill="{color}" transform="rotate({angle} {x} {y})">{html.escape(text)}</text>')


def board(d,b,mode='copper'):
    copper='#000000' if mode=='copper' else '#b4c4c8'
    if mode!='copper':d.rect(0,0,b['width'],b['height'],'#536c77','#f2f7f5',.25)
    if mode!='drill':
        for t in b['traces']:d.line(t['points'],t['width'],copper)
    for p in b['pads']:
        d.circle(p['x'],p['y'],p['diameter']/2,copper if mode!='drill' else '#f4f4f4','#777777' if mode=='drill' else None)
        if p['drill']>0:d.circle(p['x'],p['y'],.18 if mode=='copper' else p['drill']/2,'#ffffff', '#111111' if mode=='drill' else None,.12)
        if mode=='drill' and p['drill']>0:
            d.line([[p['x']-.6,p['y']],[p['x']+.6,p['y']]],.1,'#555555')
            d.line([[p['x'],p['y']-.6],[p['x'],p['y']+.6]],.1,'#555555')
    for x,y in b['mounts']:
        if mode=='copper':
            # Alignment ring remains clear of all circuit copper; drilled away.
            d.circle(x,y,1.6,'#ffffff','#000000',.15)
            d.circle(x,y,.18,'#000000')
        else:
            d.circle(x,y,1.6,'#ffffff','#536c77',.2)
            d.text(x+2,y,'M3',1.3)
    if mode in ['assembly','jumpers']:
        for c in b['components']:
            if not c['body']:continue
            x0,y0,x1,y1=c['body']
            d.rect(x0,y0,x1-x0,y1-y0,'#326879',lw=.16)
            if c['ref']=='JPI':d.text(67.8,20,'JPI / Pi GPIO 40',1.8,angle=90)
            elif c['ref'].startswith('DRV_'):
                d.text(x0+3,y0+8,c['ref'],1.65)
                d.text(x0+3,y0+11,'DRV8825',1.4)
                d.text(x0,y0-1,'EN',1.25);d.text(x1-3,y0-1,'VMOT',1.25)
            elif c['ref']=='U1':d.text(36.2,22,'U1 AHCT125',1.4,angle=90)
            else:
                d.text(x0,max(1,y0-.55),c['ref'],1.4)
            # Pin1 on component side only. All etched pads are round.
            ps=[p for p in b['pads'] if p['ref']==c['ref'] and p['pin']=='1']
            if ps:
                p=ps[0];d.circle(p['x']-1.4,p['y']-1.4,.32,'#16569b')
        d.text(5,97.5,'TT-PZ1 / PI ZERO + 2x DRV8825 / TOP',2.)
    if mode=='jumpers':
        for w in b['jumpers']:
            a,c=w['start'],w['end'];d.line([a,c],.35,'#d67b1d')
            d.text((a[0]+c[0])/2+.6,(a[1]+c[1])/2-.6,w['ref'],1.35,'#9b4d00')
    if mode=='assembly':
        for w in b['jumpers']:
            for p in [w['start'],w['end']]:
                d.circle(*p,1.05,'#fff3d5','#cf7819',.15)
                d.circle(*p,.45,'#ffffff')
                d.text(p[0]+1.2,p[1]-.5,w['ref'],1.05,'#9b4d00')


def svg_board(b,mode,mirror=False):
    d=Drawing();board(d,b,mode)
    g=''.join(d.svg)
    if mirror:g=f'<g transform="translate({b["width"]} 0) scale(-1 1)">{g}</g>'
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{b["width"]}mm" height="{b["height"]}mm" viewBox="0 0 {b["width"]} {b["height"]}"><rect width="100%" height="100%" fill="white"/>{g}</svg>'


def page_header(c,title,subtitle):
    c.setFillColorRGB(.08,.19,.25);c.setFont('Helvetica-Bold',15);c.drawString(18*mm,277*mm,title)
    c.setFont('Helvetica',9);c.drawString(18*mm,270*mm,subtitle)

def page_board(c,b,mode,mirror=False):
    ox=(210-b['width'])/2;oy=145
    c.saveState();c.translate(ox*mm,(oy+b['height'])*mm);c.scale(mm,-mm)
    if mirror:c.translate(b['width'],0);c.scale(-1,1)
    d=Drawing(c);board(d,b,mode);c.restoreState()
    # Outside the board: calibration and cut marks never form circuit copper.
    c.setStrokeColorRGB(0,0,0);c.setLineWidth(.4)
    c.line(35*mm,132*mm,85*mm,132*mm)
    for x in [35,85]:c.line(x*mm,130*mm,x*mm,134*mm)
    c.setFillColorRGB(0,0,0);c.setFont('Helvetica',9);c.drawString(40*mm,125*mm,'CALIBRATION: exactly 50 mm')
    c.setFont('Helvetica',8);c.drawString(35*mm,118*mm,'Board outline 140 x 100 mm. A4 / Actual size / 100%.')
    for x in [ox,ox+b['width']]:
        for y in [oy,oy+b['height']]:
            sx=-1 if x==ox else 1;sy=-1 if y==oy else 1
            c.line((x+sx)*mm,y*mm,(x+sx*3)*mm,y*mm)
            c.line(x*mm,(y+sy)*mm,x*mm,(y+sy*3)*mm)

def footer_lines(c,lines,y=105):
    c.setFont('Helvetica',9)
    for s in lines:c.drawString(18*mm,y*mm,s);y-=5


def writecsv(path,fields,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def main():
    b=json.loads((ROOT/'board.json').read_text());report=json.loads((ROOT/'drc-report.json').read_text())
    assert report['passed'],'Do not export manufacturing masks with failing DRC'
    assert report['board_sha256']==hashlib.sha256((ROOT/'board.json').read_bytes()).hexdigest(),'Run validate_board.py on the current geometry before export'
    for p in [PDF,SVG,PRE]:p.mkdir(parents=True,exist_ok=True)
    files=[('01-transfer-toner-1to1.pdf','TRANSFER TONER - CETAK FILE INI',False),('02-tembaga-bawah-inspeksi.pdf','SISI TEMBAGA - HANYA UNTUK INSPEKSI',True)]
    for name,title,mirror in files:
        c=canvas.Canvas(str(PDF/name),pagesize=A4);page_header(c,title,'TT-PZ1 / 140 x 100 mm / single-sided copper / no mains')
        page_board(c,b,'copper',mirror)
        footer_lines(c,['Printer laser. Actual size 100%. Matikan Fit / Shrink. JANGAN mirror lagi.',
                        'Hitam = tembaga dipertahankan. Titik putih kecil = pusat bor.',
                        'Sisi toner ditempel menghadap tembaga; orientasi master sudah disiapkan.' if not mirror else 'Bandingkan gambar ini dengan sisi tembaga SETELAH transfer.',
                        'Use 03-komponen-dan-bor.pdf for component side, drill sizes and wire jumpers.',
                        f'Required insulated wire jumpers: {len(b["jumpers"])}. Do not omit them.',
                        'Prototipe: cocokkan modul nyata dan periksa kontinuitas sebelum memberi daya.'])
        c.showPage();c.save()
    c=canvas.Canvas(str(PDF/'03-komponen-dan-bor.pdf'),pagesize=A4)
    for mode,title,lines in [
        ('assembly','COMPONENT SIDE - 1:1 PLACEMENT',['All components on bare FR4 side. Copper is on the opposite side.', 'Blue dot = pin1. All copper pads round. JPI cable must be pin1-to-pin1.', 'DRV: EN upper-left, VMOT upper-right. U1 notch faces the board top.', 'Capacitor pin1 positive. D1 pin1 cathode. Q1 pads E-B-C left-to-right.', 'Keep JARM open until STEP/DIR software and homing are ready.']),
        ('drill','DRILL GUIDE - COMPONENT SIDE',['Header / component / jumper holes: 1.0 mm.', 'Screw terminals: 1.2 mm. Mounts: 3.2 mm. Solid test pads: DO NOT DRILL.', 'Coordinates in pads.csv are millimetres from TOP-LEFT, component-side view.', 'Check footprint with the real part; form radial capacitor leads to 5.08 mm.', 'No plated holes required. Solder all pads on copper side.']),
        ('jumpers','INSULATED WIRE JUMPERS - TOP SIDE',['Orange lines are insulated WIRE, not copper traces.', 'Each Wxx connects its two dedicated pads. Follow jumpers.csv endpoints.', 'Route around sockets/components as needed; cut length includes 20 mm slack.', 'AWG22 for GND / 5V / 12V; AWG26 for logic. Insulate every crossing.', 'Install wires before sockets; retain access to module trimpots and heatsinks.'])]:
        page_header(c,title,'TT-PZ1 / 140 x 100 mm / exact scale at 100% print');page_board(c,b,mode);footer_lines(c,lines);c.showPage()
    # Connection schedule as additional pages in the assembly document.
    for start in range(0,len(b['jumpers']),26):
        page_header(c,'WIRE SCHEDULE - COMPONENT SIDE','Pad coordinates from top-left. Dedicated pads already included in copper master.')
        c.setFont('Helvetica',8);y=255
        c.drawString(18*mm,y*mm,'REF       NET                 PAD 1 (x,y mm)        PAD 2 (x,y mm)       CUT mm');y-=8
        for w in b['jumpers'][start:start+26]:
            a,z=w['start'],w['end']
            text=f'{w["ref"]:<5} {w["net"]:<17} {a[0]:6.2f},{a[1]:6.2f}       {z[0]:6.2f},{z[1]:6.2f}       {w["min_cut_length_mm"]:6.1f}'
            c.setFont('Courier',8);c.drawString(18*mm,y*mm,text);y-=7
        c.showPage()
    c.save()
    for name,mode,mirror in [('transfer-toner-1to1','copper',False),('tembaga-bawah','copper',True),('komponen-atas','assembly',False),('jumper-atas','jumpers',False)]:
        (SVG/(name+'.svg')).write_text(svg_board(b,mode,mirror))
    (ROOT.parent/'diagram-pcb.svg').write_text(svg_board(b,'assembly'))
    for f in PDF.glob('*.pdf'):
        doc=pymupdf.open(f)
        for i,p in enumerate(doc):p.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(PRE/(f.stem+f'-p{i+1}.png'))
    # A cropped, readable board image for wiring.md.
    doc=pymupdf.open(PDF/'03-komponen-dan-bor.pdf')
    crop=pymupdf.Rect(32*mm,49*mm,178*mm,155*mm)
    doc[0].get_pixmap(matrix=pymupdf.Matrix(3,3),clip=crop).save(PRE/'pcb-atas.png')
    writecsv(ROOT/'pads.csv',['ref','pin','label','net','x','y','diameter','drill'],[{k:p[k] for k in ['ref','pin','label','net','x','y','diameter','drill']} for p in b['pads']])
    rows=[]
    for w in b['jumpers']:
        rows.append(dict(ref=w['ref'],net=w['net'],x1_mm=round(w['start'][0],3),y1_mm=round(w['start'][1],3),x2_mm=round(w['end'][0],3),y2_mm=round(w['end'][1],3),cut_mm=w['min_cut_length_mm'],wire='AWG22 insulated' if w['net'] in ['12V','5V_AUX','GND'] else 'AWG26 insulated'))
    writecsv(ROOT/'jumpers.csv',list(rows[0]) if rows else ['ref'],rows)
    rows=[]
    for x in b['components']:
        value=x['value'];note=x['note']
        pins=[p for p in b['pads'] if p['ref']==x['ref']]
        if x['kind']=='connector':
            if x['ref']=='JPI':value='Header IDC 2x20 pitch2.54mm; cable 1-to-1'
            elif x['ref']=='JARM':value='Header 1x2 pitch2.54mm + removable shunt'
            elif pins[0]['drill']==1.2:value=f'Terminal sekrup {len(pins)} pin pitch5.08mm'
            else:value=f'Header 1x{len(pins)} pitch2.54mm'
            note=x['value']+'. '+note
        elif x['kind']=='resistor':note='Metal film 1/4W 1%; pitch7.62mm'
        elif x['kind']=='capacitor':
            note+='; '+('ceramic pitch2.54mm' if '100n' in value else 'radial leads formed to pitch5.08mm; see placement envelope')
        rows.append(dict(ref=x['ref'],qty=1,value=value,kind=x['kind'],note=note))
    rows += [dict(ref='SOCKET_DRV',qty=4,value='Female 1x8 2.54mm, rated >=2A/contact',kind='socket',note='For two removable DRV8825 modules; socket height >=8.5mm for wire clearance'),dict(ref='SOCKET_U1',qty=1,value='DIP14 7.62mm socket',kind='socket',note='For SN74AHCT125N'),dict(ref='WIRES',qty=len(b['jumpers']),value='Insulated copper wire',kind='jumper',note='See jumpers.csv; required for netlist continuity'),dict(ref='HEATSINK',qty=2,value='DRV8825 heatsink + airflow',kind='cooling',note='Keep conductive sink clear of pins/trimpot')]
    rows += [dict(ref='EXT_F12',qty=1,value='Inline fuse2A + holder',kind='external',note='In positive12V supply lead'),dict(ref='EXT_F5',qty=1,value='Inline fuse1.5A + holder',kind='external',note='In positive5V AUX supply lead'),dict(ref='EXT_HOME',qty=2,value='Microswitch COM/NC',kind='external',note='Match mechanical home locations'),dict(ref='EXT_PSU12',qty=1,value='Regulated12V3A DC adapter',kind='external',note='Motor power only'),dict(ref='EXT_PSU5',qty=1,value='Regulated5V2A DC supply',kind='external',note='Peripherals only; Pi uses its own USB PSU'),dict(ref='EXT_USB',qty=1,value='USB OTG adapter/cable for Pi Zero',kind='external',note='Webcam connects directly, not through etched copper')]
    writecsv(ROOT/'bom.csv',['ref','qty','value','kind','note'],rows)
    print('Exported',len(files)+1,'PDF files;',len(b['jumpers']),'wire jumpers')
    from export_component_map import main as export_component_map
    export_component_map()
if __name__=='__main__':main()
