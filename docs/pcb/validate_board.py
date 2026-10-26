"""Independent copper DRC and connectivity check of board.json (not an ERC simulator)."""
from pathlib import Path
import json,itertools,math,hashlib
from collections import defaultdict
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
ROOT=Path(__file__).resolve().parent

def main():
    b=json.loads((ROOT/'board.json').read_text());g=defaultdict(list);pads=b['pads'];errors=[]
    for p in pads:g[p['net']].append(Point(p['x'],p['y']).buffer(p['diameter']/2,quad_segs=32))
    for t in b['traces']:g[t['net']].append(LineString(t['points']).buffer(t['width']/2,quad_segs=24))
    nets={n:unary_union(v) for n,v in g.items()}
    minimum=1000;closest=None
    for (n,a),(m,c) in itertools.combinations(nets.items(),2):
        d=a.distance(c)
        if d<minimum:minimum=d;closest=[n,m]
        if d<b['min_clearance']-1e-4:errors.append(['copper clearance',n,m,round(d,4)])
    allowed=box(b['edge_clearance'],b['edge_clearance'],b['width']-b['edge_clearance'],b['height']-b['edge_clearance'])
    holes=unary_union([Point(*xy).buffer(3.2) for xy in b['mounts']])
    for n,s in nets.items():
        if not allowed.covers(s):errors.append(['board edge',n])
        if s.intersects(holes):errors.append(['mounting clearance',n])
    for p in pads:
        if (p['diameter']-p['drill'])/2<.5-1e-6:errors.append(['annular ring',p['ref'],p['pin']])
    for wire in b['jumpers']:
        for point in [wire['start'],wire['end']]:
            for c in b['components']:
                if c['body'] and c['kind']!='module' and box(*c['body']).buffer(.65).contains(Point(*point)):
                    errors.append(['jumper end blocked by component body',wire['ref'],c['ref'],point])
    disconnected=[]
    for net,shape in nets.items():
        groups=list(shape.geoms) if shape.geom_type=='MultiPolygon' else [shape]
        par=list(range(len(groups)))
        def root(i):
            while par[i]!=i:par[i]=par[par[i]];i=par[i]
            return i
        def component(xy):
            ids=[i for i,s in enumerate(groups) if s.buffer(1e-5).covers(Point(*xy))]
            assert len(ids)==1,(net,xy,ids)
            return ids[0]
        for w in b['jumpers']:
            if w['net']==net:
                a,c=component(w['start']),component(w['end']);par[root(a)]=root(c)
        ids={root(component([p['x'],p['y']])) for p in pads if p['net']==net}
        if len(ids)>1:disconnected.append(net)
    if disconnected:errors.append(['unconnected nets',disconnected])
    pn={(p['ref'],p['pin']):p['net'] for p in pads}
    assert pn['JPI','2'].startswith('NC_') and pn['JPI','4'].startswith('NC_')
    assert pn['JPI','1']=='3V3' and pn['JPI','6']=='GND'
    for axis in ['PAN','TILT']:
        assert [pn['DRV_'+axis,'L'+str(i+1)] for i in range(8)]==['DRV_EN','GND','GND','3V3','3V3','3V3',axis+'_STEP',axis+'_DIR']
        assert [pn['DRV_'+axis,'R'+str(i+1)] for i in range(8)]==['12V','GND',axis+'_B2',axis+'_B1',axis+'_A1',axis+'_A2',axis+'_FAULT','GND']
    assert pn['JARM','1']=='ENABLE_GPIO' and pn['JARM','2']=='DRV_EN'
    assert pn['R_EN','1']=='DRV_EN' and pn['R_EN','2']=='3V3'
    assert pn['R2','1']=='ECHO_5V' and pn['R2','2']==pn['R3','1']=='ECHO_3V3' and pn['R3','2']=='GND'
    expected_pi={3:'SDA',5:'SCL',11:'TRIG_3V3',12:'PAN_STEP',13:'ECHO_3V3',15:'GREEN_GPIO',16:'RED_GPIO',22:'TILT_FAULT',29:'BUZZ_GPIO',31:'HOME_PAN',32:'PAN_DIR',33:'TILT_STEP',35:'TILT_DIR',36:'HOME_TILT',37:'ENABLE_GPIO',38:'PAN_FAULT',40:'RING_3V3'}
    for pin,net in expected_pi.items():assert pn['JPI',str(pin)]==net,(pin,net)
    expected_u1=['GND','RING_3V3','RING_BUF','GND','TRIG_3V3','TRIG_5V','GND','NC_U1_8','GND','5V_AUX','NC_U1_11','GND','5V_AUX','5V_AUX']
    assert [pn['U1',str(i)] for i in range(1,15)]==expected_u1
    assert [pn['Q1',str(i)] for i in range(1,4)]==['GND','BUZZ_B','BUZZ_C']
    assert pn['D1','1']=='5V_AUX' and pn['D1','2']=='BUZZ_C'
    for axis in ['PAN','TILT']:
        assert pn['R_H'+axis,'1']=='3V3' and pn['R_H'+axis,'2']=='HOME_'+axis
        assert pn['C_H'+axis,'1']=='HOME_'+axis and pn['C_H'+axis,'2']=='GND'
        assert pn['JH_'+axis,'1']=='HOME_'+axis and pn['JH_'+axis,'2']=='GND'
    result=dict(board_sha256=hashlib.sha256((ROOT/'board.json').read_bytes()).hexdigest(),revision=b['revision'],passed=not errors,pad_count=len(pads),drilled_pad_count=sum(p['drill']>0 for p in pads),solid_test_pad_count=sum(p['drill']==0 for p in pads),trace_count=len(b['traces']),wire_jumpers=len(b['jumpers']),
                net_count=len(nets),unconnected_nets=disconnected,min_measured_clearance_mm=round(minimum,5),closest_nets=closest,
                minimum_annular_ring_mm=min((p['diameter']-p['drill'])/2 for p in pads),errors=errors,
                limitations=['Geometry/netlist checks only, not an electrical simulation or certified layout review.',
                             'No prototype, thermal or EMC tests performed. Trace current capability assumes35um copper.',
                             'Module and connector pinouts/physical fit must match the specified footprints.',
                             'Insulated wire jumpers are required; copper alone is intentionally incomplete.'])
    (ROOT/'drc-report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2));assert not errors,'DRC failed'
if __name__=='__main__':main()
