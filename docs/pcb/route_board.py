"""Route a single bottom copper layer; unresolved crossings use labelled insulated wires.
Physical geometry is checked independently by validate_board.py before release.
"""
from pathlib import Path
import heapq,itertools,json,math,copy
from collections import defaultdict
import numpy as np
import shapely
from shapely.geometry import Point,LineString,box
from shapely.ops import unary_union
import design as D
ROOT=Path(__file__).resolve().parent
G=.635;CLEAR=.40;EDGE=2.
W,H=D.W,D.H
nx,ny=int(W/G)+1,int(H/G)+1
yy,xx=np.mgrid[:ny,:nx];X=xx*G;Y=yy*G
pads=copy.deepcopy(D.pads);traces=copy.deepcopy(D.traces);jumpers=[];used_ports=set()

def padshape(p):return Point(p['x'],p['y']).buffer(p['diameter']/2,quad_segs=24)
def trshape(t):return LineString(t['points']).buffer(t['width']/2,quad_segs=12)
def near(p):return (round(p[0]/G),round(p[1]/G))
def xy(p):return [round(p[0]*G,4),round(p[1]*G,4)]
def width(net):
    return 1.2 if net in ('12V','5V_AUX','GND') or net.endswith(('_A1','_A2','_B1','_B2')) else (.8 if net=='3V3' else .6)

def geometry(net,foreign=False):
    return unary_union([padshape(p) for p in pads if (p['net']!=net if foreign else p['net']==net)]+[trshape(t) for t in traces if (t['net']!=net if foreign else t['net']==net)])
mount=unary_union([Point(x,y).buffer(3.2) for x,y in D.mounts])

def grid_block(net,w):
    obstacle=geometry(net,True).buffer(w/2+CLEAR+.025).union(mount.buffer(w/2))
    return shapely.intersects_xy(obstacle,X,Y)|(X<EDGE+w/2)|(X>W-EDGE-w/2)|(Y<EDGE+w/2)|(Y>H-EDGE-w/2)

def astar(start,target,blocked):
    s=near(start)
    if blocked[s[1],s[0]]:return None
    inds=np.argwhere(target)
    if not len(inds):return None
    ds=(inds[:,1]-s[0])**2+(inds[:,0]-s[1])**2
    q=inds[int(ds.argmin())];goal=(int(q[1]),int(q[0]))
    if target[s[1],s[0]]:return [xy(s)]
    todo=[(0.,0.,s)];cost={s:0.};parent={}
    moves=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)]
    while todo:
        _,c,a=heapq.heappop(todo)
        if c>cost.get(a,1e12)+1e-9:continue
        x,y=a
        if target[y,x]:
            path=[a]
            while a in parent:a=parent[a];path.append(a)
            return [xy(p) for p in path[::-1]]
        for dx,dy in moves:
            b=(x+dx,y+dy);bx,by=b
            if not (0<=bx<nx and 0<=by<ny) or blocked[by,bx]:continue
            if dx and dy and (blocked[y,bx] or blocked[by,x]):continue
            nc=c+(1.414213562 if dx and dy else 1.)
            if nc>=cost.get(b,1e12):continue
            cost[b]=nc;parent[b]=a
            h=math.hypot(bx-goal[0],by-goal[1])
            heapq.heappush(todo,(nc+h,nc,b))
    return None

def simplify(path):
    if len(path)<3:return path
    out=[path[0]]
    for a,b,c in zip(path,path[1:],path[2:]):
        if abs((b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]))>1e-6:out.append(b)
    out.append(path[-1]);return out

def targetmask(shape):return shapely.intersects_xy(shape,X,Y)

def jumper_pad_ok(p,net,foreign=None):
    shape=Point(*p).buffer(1)
    if not box(EDGE,EDGE,W-EDGE,H-EDGE).contains(shape):return False
    if shape.intersects(mount):return False
    # Wire ends must remain physically accessible. DRV modules sit on tall
    # removable sockets; other bodies (especially IDC/DIP sockets) block them.
    if any(box(*c['body']).buffer(.65).contains(Point(*p)) for c in D.components if c['body'] and c['kind']!='module'):return False
    if shape.distance(foreign if foreign is not None else geometry(net,True))<CLEAR+.05:return False
    if any(math.hypot(p[0]-q['x'],p[1]-q['y'])<2.54-.001 for q in pads):return False
    return True

def via_near(start,net,blocked):
    # Isolated pad with a bottom trace stub; never shares a hole with a component.
    # Pre-reserved wire pads are legal even in a fully enclosed bottom-copper island.
    for port in pads:
        if port.get('wire_port') and port['net']==net and port['ref'] not in used_ports:
            q=[port['x'],port['y']];target=np.zeros_like(blocked);x,y=near(q);target[y,x]=True
            path=astar(start,target,blocked)
            if path is not None:return q,path
    candidates=[];sx,sy=near(start);foreign=geometry(net,True)
    for r in (4,5,6,8,10,12,16):
        for dx,dy in [(r,i) for i in range(-r,r+1,2)]+[(-r,i) for i in range(-r,r+1,2)]+[(i,r) for i in range(-r+2,r,2)]+[(i,-r) for i in range(-r+2,r,2)]:
            q=xy((sx+dx,sy+dy))
            if jumper_pad_ok(q,net,foreign):candidates.append(q)
    for q in candidates:
        target=np.zeros_like(blocked);x,y=near(q);target[y,x]=True
        path=astar(start,target,blocked)
        if path is not None:return q,path
    raise RuntimeError(('cannot escape to jumper',net,start))

def addtrace(net,path,w):
    if len(path)>=2:traces.append(dict(net=net,points=simplify(path),width=w))

def expand_connected(seed,net):
    shape=geometry(net)
    gs=list(shape.geoms) if shape.geom_type=='MultiPolygon' else [shape]
    return unary_union([g for g in gs if g.intersects(seed)])

def pathshape(path,w):
    return (LineString(path) if len(path)>1 else Point(*path[0])).buffer(w/2)

def route_net(net,ps):
    w=width(net);block=grid_block(net,w)
    connected=expand_connected(padshape(ps[0]),net)
    pending=ps[1:]
    while pending:
        pending.sort(key=lambda p:Point(p['x'],p['y']).distance(connected))
        p=pending.pop(0);start=[p['x'],p['y']]
        path=astar(start,targetmask(connected),block)
        if path is not None:
            addtrace(net,path,w)
            connected=expand_connected(unary_union([connected,padshape(p),pathshape(path,w)]),net)
            continue
        # Add an insulated top-side wire across the routing barrier.
        a,pa=via_near(start,net,block)
        targets=[q for q in ps if connected.intersects(Point(q['x'],q['y']))]
        targets.sort(key=lambda q:math.hypot(q['x']-a[0],q['y']-a[1]))
        found=None
        for q in targets:
            try:
                b,pb=via_near([q['x'],q['y']],net,block)
                if math.dist(a,b)<2.54:continue
                found=(b,pb);break
            except RuntimeError:pass
        if found is None:raise RuntimeError(('cannot land jumper',net,start))
        b,pb=found
        ref=f'W{len(jumpers)+1:02}'
        for i,pt in enumerate([a,b]):
            existing=next((q for q in pads if math.dist([q['x'],q['y']],pt)<.01),None)
            if existing:used_ports.add(existing['ref'])
            else:pads.append(dict(ref=ref,pin=str(i+1),x=pt[0],y=pt[1],net=net,diameter=2.,drill=1.0,label=str(i+1)))
        jumpers.append(dict(ref=ref,net=net,start=a,end=b,min_cut_length_mm=round(math.dist(a,b)+20,1)))
        addtrace(net,pa,w);addtrace(net,pb,w)
        connected=expand_connected(unary_union([connected,padshape(p),Point(*a).buffer(1),Point(*b).buffer(1),pathshape(pa,w),pathshape(pb,w)]),net)
        block=grid_block(net,w)
    print(net,'pads',len(ps),'jumpers',len(jumpers),flush=True)


def main():
    groups=defaultdict(list)
    for p in pads:groups[p['net']].append(p)
    # First preserve short wide motor circuits, then power and local low-voltage signals.
    priority=['12V','5V_AUX','PAN_B2','PAN_B1','PAN_A1','PAN_A2','TILT_B2','TILT_B1','TILT_A1','TILT_A2','RING_DATA','RING_BUF','ECHO_5V','BUZZ_C','BUZZ_B','TRIG_5V','GREEN_A','RED_A','GND','3V3']
    rest=sorted([n for n in groups if n not in priority and not n.startswith('NC_')],key=lambda n:len(groups[n]))
    for n in priority+rest:
        if len(groups[n])>1:
            try:route_net(n,groups[n])
            except Exception:
                Path('/tmp/twotrash-route-debug.json').write_text(json.dumps(dict(width=W,height=H,pads=pads,traces=traces,jumpers=jumpers,components=D.components,mounts=D.mounts)))
                raise
    # Unused escape pads remain as solid copper test points, not extra holes.
    for p in pads:
        if p.get('wire_port') and p['ref'] not in used_ports:p['drill']=0
    board=dict(revision='TT-PZ1',width=W,height=H,grid=G,min_clearance=CLEAR,edge_clearance=EDGE,copper_oz=1,
               pads=pads,traces=traces,jumpers=jumpers,components=D.components,mounts=D.mounts,
               notes=['Bottom copper only; wire jumpers on insulated top side.','Pi powered separately via USB. Pi pins2/4 not routed.','Nano not used. DRV8825 direct3.3V STEP/DIR.'])
    (ROOT/'board.json').write_text(json.dumps(board,indent=2)+'\n')
    print('TOTAL',len(pads),'pads',len(traces),'tracks',len(jumpers),'jumpers')
if __name__=='__main__':main()
