"""Editable electrical/placement source. Units mm; component-side view, Y down.
TT-PZ1: Raspberry Pi 40-pin cable, two Pololu-pinout DRV8825 carriers.
No mains, USB data, regulator, or stepper power IC on this home-etched board.
"""
W,H=140.,100.
PITCH=2.54
pads=[]; components=[]; traces=[]

def pad(ref,pin,x,y,net,d=2.,drill=1.0,label=None):
    p=dict(ref=ref,pin=str(pin),x=x,y=y,net=net or f'NC_{ref}_{pin}',diameter=d,drill=drill,label=label or str(pin))
    pads.append(p); return p

def part(ref,value,points,body=None,kind='passive',note=''):
    for pin,x,y,net,*more in points:pad(ref,pin,x,y,net,*more)
    components.append(dict(ref=ref,value=value,body=body,kind=kind,note=note))

def conn(ref,value,x,y,nets,pitch=2.54,vertical=False,terminal=False,labels=None):
    ps=[]
    for i,n in enumerate(nets):
        ps.append((i+1,x+(0 if vertical else i*pitch),y+(i*pitch if vertical else 0),n,3. if terminal else 2.,1.2 if terminal else 1.0,(labels or nets)[i]))
    margin=3.4 if terminal else 1.6
    b=[x-margin,y-margin,x+(0 if vertical else (len(nets)-1)*pitch)+margin,y+((len(nets)-1)*pitch if vertical else 0)+margin]
    part(ref,value,ps,b,'connector')

def axial(ref,value,x,y,n1,n2,vertical=False,pitch=7.62,kind='resistor'):
    dx,dy=(0,pitch) if vertical else (pitch,0)
    part(ref,value,[(1,x,y,n1),(2,x+dx,y+dy,n2)],[min(x,x+dx)-1,min(y,y+dy)-1,max(x,x+dx)+1,max(y,y+dy)+1],kind)

def cap(ref,value,x,y,plus,minus='GND',pitch=2.54,diam=4):
    part(ref,value,[(1,x,y,plus),(2,x+pitch,y,minus)],[x+pitch/2-diam/2,y-diam/2,x+pitch/2+diam/2,y+diam/2],'capacitor', 'Pin 1 positive for electrolytic')

# The Pi is powered only through its own USB power input. Pins 2/4 are NOT routed.
pi={1:'3V3',3:'SDA',5:'SCL',6:'GND',11:'TRIG_3V3',12:'PAN_STEP',13:'ECHO_3V3',
    15:'GREEN_GPIO',16:'RED_GPIO',18:None,22:'TILT_FAULT',29:'BUZZ_GPIO',31:'HOME_PAN',
    32:'PAN_DIR',33:'TILT_STEP',35:'TILT_DIR',36:'HOME_TILT',37:'ENABLE_GPIO',38:'PAN_FAULT',40:'RING_3V3'}
ps=[]
for i in range(40):
    pin=i+1;ps.append((pin,66.04+(i%2)*2.54,7.62+(i//2)*2.54,pi.get(pin)))
part('JPI','Pi GPIO 2x20 / IDC 1-to-1',ps,[62.5,2.54,72.12,60.96],'connector','Pin 1 indicated on assembly map. Pi 5V pins2/4 NC. Top view. No Pi mounting footprint.')
conn('J5V','5V AUX IN',10.16,5.08,['5V_AUX','GND'],5.08,terminal=True)
conn('J12V','12V IN (fuse external)',129.54,5.08,['12V','GND'],5.08,terminal=True)
conn('JOLED','OLED 3V3',7.62,12.7,['GND','3V3','SCL','SDA'],vertical=True)
conn('JHC','HC-SR04',7.62,30.48,['5V_AUX','TRIG_5V','ECHO_5V','GND'],vertical=True)
conn('JGREEN','GREEN LED',7.62,43.18,['GREEN_A','GND'])
conn('JRED','RED LED',25.4,43.18,['RED_A','GND'])
conn('JBUZ','ACTIVE BUZZER 5V <=50mA',45.72,5.08,['5V_AUX','BUZZ_C'])
conn('JRING','WS2812 12LED',22.86,5.08,['5V_AUX','GND','RING_DATA'],5.08,terminal=True)

# DIP14 AHCT125, notch towards board top. Inputs3.3V -> outputs5V.
u=['GND','RING_3V3','RING_BUF','GND','TRIG_3V3','TRIG_5V','GND',None,'GND','5V_AUX',None,'GND','5V_AUX','5V_AUX']
ps=[]
for pin in range(1,15):
    x=33.02 if pin<=7 else 40.64;y=20.32+((pin-1) if pin<=7 else (14-pin))*2.54
    ps.append((pin,x,y,u[pin-1]))
part('U1','SN74AHCT125N DIP14',ps,[31.75,18.4,41.91,37.5],'ic','Notch top; use AHCT, not HC. Unused gates disabled.')
cap('C1','100nF',40.64,15.24,'5V_AUX')
cap('C2','1000uF 16V',22.86,13.97,'5V_AUX',pitch=5.08,diam=10)
axial('R1','330R',16.51,25.4,'RING_DATA','RING_BUF')
axial('R2','2k2',16.51,36.83,'ECHO_5V','ECHO_3V3')
axial('R3','2k7',20.32,50.8,'ECHO_3V3','GND')
axial('R4','330R',17.78,55.88,'GREEN_A','GREEN_GPIO',vertical=True)
axial('R5','330R',27.94,55.88,'RED_A','RED_GPIO',vertical=True)
axial('R6','1k',45.72,43.18,'BUZZ_GPIO','BUZZ_B',vertical=True)
axial('R7','10k',53.34,30.48,'BUZZ_B','GND',vertical=True)
axial('R8','100k',27.94,20.32,'RING_3V3','GND',vertical=True)
axial('R9','100k',33.02,43.18,'TRIG_3V3','GND',vertical=True)
part('Q1','2N3904 TO92 E-B-C (spread 2.54)',[(1,45.72,27.94,'GND'),(2,48.26,27.94,'BUZZ_B'),(3,50.8,27.94,'BUZZ_C')],[44.7,26.4,51.8,29.5],'transistor','E-B-C per onsemi; spread leads to 2.54mm.')
axial('D1','1N4148 (K at pin1)',45.72,12.7,'5V_AUX','BUZZ_C',kind='diode')

# Two DRV8825 modules: component side up; EN top-left, VMOT top-right.
for axis,y in [('PAN',15.24),('TILT',53.34)]:
    l=['DRV_EN','GND','GND','3V3','3V3','3V3',axis+'_STEP',axis+'_DIR']
    rr=['12V','GND',axis+'_B2',axis+'_B1',axis+'_A1',axis+'_A2',axis+'_FAULT','GND']
    namesl=['EN','M0','M1','M2','RST','SLP','STEP','DIR'];namesr=['VMOT','GND','B2','B1','A1','A2','FAULT','GND']
    ps=[]
    for i in range(8):
        ps.append(('L'+str(i+1),99.06,y+2.54*i,l[i],2.,1.0,namesl[i]))
        ps.append(('R'+str(i+1),114.3,y+2.54*i,rr[i],2.,1.0,namesr[i]))
    part('DRV_'+axis,'DRV8825 '+axis,ps,[97.54,y-1.5,115.82,y+19.28],'module','2x8 sockets, row gap15.24, pitch2.54. Pololu2133 pinout only.')
    conn('JM_'+axis,axis+' MOTOR',130.81,y+7.62,[axis+'_B2',axis+'_B1',axis+'_A1',axis+'_A2'],5.08,True,True,labels=['B2','B1','A1','A2'])
    cap('C_'+axis,'100uF 35V',120.65,y-5.08,'12V',pitch=5.08,diam=8)

conn('JARM','ARM (normally OPEN)',80.01,57.15,['ENABLE_GPIO','DRV_EN'])
axial('R_EN','2k2',88.9,57.15,'DRV_EN','3V3',vertical=True)
for axis,x in [('PAN',58.42),('TILT',73.66)]:
    axial('R_H'+axis,'10k',x,74.93,'3V3','HOME_'+axis,vertical=True)
    cap('C_H'+axis,'100nF',x,86.36,'HOME_'+axis)
    conn('JH_'+axis,axis+' HOME NC',x,92.71,['HOME_'+axis,'GND'])

mounts=[(4,4),(86,4),(4,96),(136,96)]

def tr(net,points,w):traces.append(dict(net=net,points=points,width=w))
# Low-impedance local motor supply/return; do not route winding current through Pi.
tr('12V',[(129.54,5.08),(91.44,5.08),(91.44,48.26),(114.3,48.26),(114.3,53.34)],1.5)
tr('12V',[(91.44,10.16),(114.3,10.16),(114.3,15.24)],1.5)
tr('12V',[(114.3,10.16),(120.65,10.16)],1.5)
tr('12V',[(114.3,48.26),(120.65,48.26)],1.5)
tr('GND',[(134.62,5.08),(137.16,5.08),(137.16,86.36)],1.5)
for y in [15.24,53.34]:
    tr('GND',[(114.3,y+2.54),(137.16,y+2.54)],1.2)
    tr('GND',[(114.3,y+17.78),(109.22,y+17.78),(109.22,y+2.54),(114.3,y+2.54)],1.2)
    tr('GND',[(125.73,y-5.08),(125.73,y+2.54)],1.2)

# Ordered winding fan-out: preserve pair order and 0.59mm diagonal clearance.
for axis,y in [('PAN',15.24),('TILT',53.34)]:
    for i,name in enumerate(['B2','B1','A1','A2']):
        sy=y+5.08+i*2.54; ey=y+7.62+i*5.08
        tr(axis+'_'+name,[(114.3,sy),(116.84,sy),(116.84+ey-sy,ey),(130.81,ey)],1.2)
# Peripheral return trunk stays on the perimeter, away from motor phase fan-outs.
tr('GND',[(15.24,5.08),(17.78,7.62),(17.78,12.7),(3.175,12.7),(3.175,89.535),(137.16,89.535),(137.16,86.36)],1.2)

# Dedicated wire/test pads reserve escape points before routing dense headers.
def wire_port(ref,x,y,net,source,w=.6):
    q=pad(ref,1,x,y,net);q['wire_port']=True
    tr(net,[source,[x,y]],w)
for i,net in pi.items():
    if net:
        sx=66.04+((i-1)%2)*2.54;sy=7.62+((i-1)//2)*2.54
        wire_port('TP_PI'+str(i),60.96 if i%2 else 73.66,sy,net,[sx,sy],1.2 if net=='GND' else .8 if net=='3V3' else .6)
for axis,y in [('PAN',15.24),('TILT',53.34)]:
    wire_port('TP_'+axis+'_FAULT',111.76,y+15.24,axis+'_FAULT',[114.3,y+15.24])
    for net,offset in [('DRV_EN',0),(axis+'_STEP',15.24),(axis+'_DIR',17.78),('3V3',7.62)]:
        wire_port('TP_'+axis+'_'+str(offset),96.52,y+offset,net,[99.06,y+offset],.8 if net=='3V3' else .6)
wire_port('TP_RING',30.48,22.86,'RING_3V3',[33.02,22.86])
wire_port('TP_TRIG',30.48,30.48,'TRIG_3V3',[33.02,30.48])
wire_port('TP_RDOUT',13.97,25.4,'RING_DATA',[16.51,25.4])
wire_port('TP_RDPORT',35.56,10.16,'RING_DATA',[33.02,5.08])
# Connector escape pads permit one-sided routing without sharing component holes.
for ref,x,y,nets in [('JOLED',7.62,12.7,['GND','3V3','SCL','SDA']),('JHC',7.62,30.48,['5V_AUX','TRIG_5V','ECHO_5V','GND'])]:
    for i,net in enumerate(nets):
        wire_port('TP_'+ref+str(i+1),11.43,y+2.54*i,net,[x,y+2.54*i],1.2 if net in ['5V_AUX','GND'] else .8 if net=='3V3' else .6)
wire_port('TP_TRIG_OUT',30.48,33.02,'TRIG_5V',[33.02,33.02])
wire_port('TP_RING_BUF',30.48,25.4,'RING_BUF',[33.02,25.4])
wire_port('TP_GREEN_A',7.62,46.99,'GREEN_A',[7.62,43.18])
wire_port('TP_RED_A',25.4,46.99,'RED_A',[25.4,43.18])
wire_port('TP_ECHO_HI',26.67,34.29,'ECHO_3V3',[24.13,36.83])
wire_port('TP_ECHO_LOW',20.32,46.99,'ECHO_3V3',[20.32,50.8])
wire_port('TP_BUZZ_PORT',50.8,7.62,'BUZZ_C',[48.26,5.08])
wire_port('TP_BUZZ_COL',53.34,25.4,'BUZZ_C',[50.8,27.94])
wire_port('TP_BUZZ_BASE',48.26,31.75,'BUZZ_B',[48.26,27.94])
wire_port('TP_BUZZ_GPIO',43.18,40.64,'BUZZ_GPIO',[45.72,43.18])
wire_port('TP_G_OUT',15.24,53.34,'GREEN_A',[17.78,55.88])
wire_port('TP_R_OUT',30.48,58.42,'RED_A',[27.94,55.88])
wire_port('TP_G_IN',15.24,66.04,'GREEN_GPIO',[17.78,63.5])
wire_port('TP_R_IN',30.48,66.04,'RED_GPIO',[27.94,63.5])
wire_port('TP_C1_GND',46.99,17.78,'GND',[43.18,15.24],1.2)
wire_port('TP_Q1_GND',45.72,22.86,'GND',[45.72,27.94],1.2)
wire_port('TP_C2_GND',31.75,15.24,'GND',[27.94,13.97],1.2)
for pin,x,y,px in [(1,33.02,20.32,30.48),(4,33.02,27.94,30.48),(7,33.02,35.56,30.48),(9,40.64,33.02,43.18),(12,40.64,25.4,43.18)]:
    wire_port('TP_U1_G'+str(pin),px,y,'GND',[x,y],1.2)
tr('GND',[(27.94,27.94),(33.02,27.94)],1.2)
wire_port('TP_R3_GND',25.4,53.34,'GND',[27.94,50.8],1.2)
tr('GND',[(27.94,50.8),(33.02,50.8)],1.2)
wire_port('TP_R7_GND',55.88,40.64,'GND',[53.34,38.1],1.2)

wire_port('TP_5V_IN',10.16,10.16,'5V_AUX',[10.16,5.08],1.2)
wire_port('TP_PI_3V3_EXTRA',57.15,7.62,'3V3',[60.96,7.62],.8)
wire_port('TP_PI_ECHO_EXTRA',57.15,22.86,'ECHO_3V3',[60.96,22.86])
