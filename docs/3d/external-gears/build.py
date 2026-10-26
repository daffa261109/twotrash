"""Rev G1: regenerate actual meshes, empty-flap torque calculation and previews."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,json,math,base64,tempfile
import numpy as np
import trimesh
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
from render_pan_tilt import render,font,BG
from parts import PARTS,stl_path,write_print_notes
def body_count(m):
    par=list(range(len(m.vertices)))
    def root(i):
        while par[i]!=i:par[i]=par[par[i]];i=par[i]
        return i
    for a,b,c in m.faces:
        r=root(int(a));par[root(int(b))]=r;par[root(int(c))]=r
    return len({root(i) for i in range(len(par))})

def export(p):
    out=stl_path(p)
    deps=[ROOT/'rakitan.scad',ROOT/'gear_profiles.scad',ROOT/'flap-shape-library.scad']
    if out.exists() and out.stat().st_mtime>max(x.stat().st_mtime for x in deps):return p
    q=subprocess.run(['openscad','-o',str(out),'-D',f'part="{p}"',str(ROOT/'rakitan.scad')],capture_output=True,text=True)
    if q.returncode != 0:out.with_suffix('.log').write_text(q.stderr)
    assert q.returncode==0,(p,q.stderr)
    return p

def T(x=0,y=0,z=0):
    m=np.eye(4);m[:3,3]=[x,y,z];return m

def R(axis,deg):
    a=np.zeros(3);a[axis]=1
    return trimesh.transformations.rotation_matrix(math.radians(deg),a)
COLORS={'frame':[67,91,112],'gear':[225,163,56],'steel':[170,186,199],'bearing':[80,99,122],'motor':[51,58,68],'flap':[54,168,143],'rails':[132,172,200]}
def objects():
    out=[]
    def add(part,kind,color,base=None,motion=''):
        out.append(dict(part=part,kind=kind,color=COLORS[color],base=(np.eye(4) if base is None else base).T.flatten().tolist(),motion=motion))
    for p,c in [('rails','rails'),('flange','frame'),('backplates','steel'),('rivets','steel'),('pan_bearings','bearing')]:add(p,'fixed',c)
    add('motor','fixed','motor',T(y=38.4))
    add('pinion_pan','fixed','gear',T(y=38.4,z=12),'panpinion')
    add('pinion_pan_fastener','fixed','steel',T(y=38.4,z=12),'panpinion')
    for p,c in [('frame','frame'),('caps','frame'),('retainers','steel'),('pan_shaft','steel'),('pan_collars','steel'),('tilt_bearings','bearing')]:add(p,'pan',c)
    add('driven','pan','gear',T(z=12));add('motor','pan','motor',T(y=-36,z=61.6)@R(0,90))
    add('pinion_tilt','pan','gear',T(y=-40,z=61.6)@R(0,90),'tiltpinion')
    add('pinion_tilt_fastener','pan','steel',T(y=-40,z=61.6)@R(0,90),'tiltpinion')
    add('flap','tilt','flap');add('driven','tilt','gear',T(y=-40)@R(0,90))
    for p in ['tilt_shaft','tilt_collar']:add(p,'tilt','steel',T(z=-100))
    return out

def matrix(o,p=0,t=0):
    m=np.eye(4) if o['kind']=='fixed' else R(2,p)
    if o['kind']=='tilt':m=m@T(z=100)@R(1,t)
    m=m@np.array(o['base']).reshape(4,4).T
    if o['motion']=='panpinion':m=m@R(2,-3*p)
    if o['motion']=='tiltpinion':m=m@R(2,3*t)
    return m

def main():
    write_print_notes()
    with ThreadPoolExecutor(max_workers=4) as pool:
        for f in as_completed([pool.submit(export,p) for p in PARTS]):print('CAD',f.result(),flush=True)
    meshes={p:trimesh.load(stl_path(p),force='mesh') for p in PARTS}
    checks={}
    grouped=['caps','retainers','pan_bearings','tilt_bearings','pan_collars','rails','backplates','rivets','pinion_pan_fastener','pinion_tilt_fastener']
    for p,m in meshes.items():
        assert m.is_watertight and m.is_winding_consistent and m.volume>0,(p,'invalid mesh')
        checks[p]=dict(watertight=True,bodies=body_count(m),size_mm=m.extents.tolist(),volume_mm3=float(m.volume))
        if p not in grouped:assert checks[p]['bodies']==1,(p,checks[p]['bodies'])
    assert np.allclose(meshes['flap'].extents[:2],[200,250],atol=.02)
    objs=objects();(ROOT/'scene.json').write_text(json.dumps(objs,indent=2)+'\n')
    scene=trimesh.Scene()
    for i,o in enumerate(objs):
        if o['part']=='rails':continue
        m=meshes[o['part']].copy();m.visual.vertex_colors=np.tile(o['color']+[255],(len(m.vertices),1))
        scene.add_geometry(m,node_name=f'{i}_{o["part"]}',transform=matrix(o))
    scene.export(ROOT/'rakitan.glb',include_normals=False)
    moving_min=1e9;radius=0
    for a in np.linspace(-60,60,121):
        for o in objs:
            if o['kind']=='fixed' or o['part'] in ['pan_shaft','pan_collars']:continue
            v=trimesh.transform_points(meshes[o['part']].vertices,matrix(o,0,a))
            moving_min=min(moving_min,float(v[:,2].min()));radius=max(radius,float(np.linalg.norm(v[:,:2],axis=1).max()))
    assert moving_min>6,moving_min
    # Only the empty printed flap, including its integral support. No trash.
    density=1.27e-6
    flap=meshes['flap'];mass=flap.volume*density;com=flap.center_mass
    tray_mass=meshes['tray_only'].volume*density
    angles=np.linspace(-60,60,241)
    torques=[mass*9.81*abs(com[0]*math.cos(math.radians(a))+com[2]*math.sin(math.radians(a)))/1000 for a in angles]
    static=max(torques)
    inertia_y=(flap.moment_inertia[1,1]+flap.volume*(com[0]**2+com[2]**2))*density*1e-6
    alpha=math.radians(20);dynamic=inertia_y*alpha
    factor=3;eff=.75;target=factor*(static+dynamic)
    checks['assembly']=dict(revision='G1',payload_kg=0,slot_mm=70,fixed_body_width_mm=66,side_clearance_mm=2,base_length_mm=98,ear_span_mm=140,ear_width_mm=30,rivet_nominal_diameter_mm=3.5,rivet_hole_mm=3.7,
      tilt_axis_height_above_rim_mm=100,pan_deg=[-90,90],tilt_deg=[-60,60],sampled_min_head_z_above_rim_mm=moving_min,conservative_swing_diameter_mm=2*radius,
      material_density_assumed_g_cm3=1.27,solid_tray_only_mass_kg=tray_mass,solid_flap_including_integral_support_mass_kg=mass,flap_CoG_from_tilt_axis_mm=com.tolist(),
      maximum_empty_flap_static_tilt_torque_Nm=static,flap_tilt_inertia_kg_m2=inertia_y,assumed_output_acceleration_deg_s2=20,flap_acceleration_torque_Nm=dynamic,
      margin_factor=factor,output_torque_target_Nm=target,gear_ratio=3,assumed_efficiency=eff,required_motor_torque_Nm=target/(3*eff),initial_output_speed_deg_s=10,motor_speed_rpm=5,
      motor_reference='42HD4027-01; max42.3mm face,39.5mm body,23+/-1mm round shaft; target diameter5mm. Listing torque conflicts: 0.28Nm text / 0.40Nm drawing; running torque unverified',
      limitations=['Mass assumes a fully solid PETG mesh; actual print infill/density changes mass and CoG.','No 1kg trash load included. No payload rating.','Torque is for the empty integral flap; factor3 is an allowance, not a measured friction or impact model.','Pan vertical-axis gravity torque is zero for a vertical axis; complete head inertia, cable drag and bearing friction require a running test.','Efficiency75% assumed. Holding torque is not running torque. Verify actual motor/driver current and smooth starting.','Spur gears backdrive; do not rely on this assembly to hold position without power.','Printed gears, frame, rivets, shaft flats, nut pockets and bearing fits need prototype validation.'])
    (ROOT/'verification.json').write_text(json.dumps(checks,indent=2)+'\n')
    with tempfile.TemporaryDirectory(prefix='twotrash-render-') as render_dir:
        def render_objects(p=0,t=-35,hide=False):
            out=[]
            for i,o in enumerate(objs):
                if hide and o['part']=='flap':continue
                mesh=meshes[o['part']].copy().apply_transform(matrix(o,p,t))
                path=Path(render_dir)/f'{i}.stl';mesh.export(path);out.append((path,o['color']))
            return out
        hero=render(render_objects(),(1100,880),(1.7,-2.8,1.6))
        detail=render(render_objects(t=0,hide=True),(720,710),(1.5,-2.5,1.5))
        canvas=Image.new('RGB',(1840,1120),tuple(BG));d=ImageDraw.Draw(canvas)
        d.text((40,30),'FLAP 20 × 25 cm · NEMA17 · GEAR LUAR 3:1',font=font(36,True),fill='#193748')
        d.text((40,86),'Rev G1 • flap kosong • badan bawah 66 mm untuk celah 70 mm',font=font(24),fill='#4e6473')
        canvas.paste(hero,(0,160));canvas.paste(detail,(1100,175))
        d.text((1140,150),'MEKANISME TANPA FLAP',font=font(23,True),fill='#193748')
        for y,s in [(900,'2 motor biasa · 2 pasang gear 16/48'),(940,f'Massa flap + penguat: ≈ {mass*1000:.0f} gram'),(980,f'Torsi gravitasi flap: ≈ {static:.3f} N·m'),(1020,'Penguat dan dudukan poros menyatu')]:d.text((1130,y),s,font=font(21),fill='#4e6473')
        d.text((40,1070),'MODEL PROTOTIPE — beban sampah 0 kg. Ukuran dan gerak diperiksa; kekuatan belum diuji fisik.',font=font(22,True),fill='#995328')
        canvas.save(ROOT/'rakitan-3d.png');detail.save(ROOT/'mekanisme-tanpa-flap.png')
    data={}
    for p in sorted(set(o['part'] for o in objs)):
        m=meshes[p];a=np.concatenate([m.triangles.reshape(-1,3),np.repeat(m.face_normals,3,axis=0)],axis=1).astype('<f4')
        data[p]=base64.b64encode(a.tobytes()).decode()
    html=(ROOT/'viewer-template.html').read_text().replace('__MESHES__',json.dumps(data)).replace('__OBJECTS__',json.dumps(objs)).replace('__MASS__',f'{mass*1000:.0f}').replace('__TORQUE__',f'{static:.3f}')
    (ROOT/'rakitan-3d.html').write_text(html)
    preview_dir=ROOT/'previews'
    preview_dir.mkdir(exist_ok=True)
    for name,eye in [('flap-atas.png',(0,0,1)),('flap-bawah.png',(0,0,-1)),('flap-miring.png',(1.6,-2.5,1.5)),('flap-bawah-miring.png',(1.6,-2.5,-1.5))]:render([(stl_path('flap'),COLORS['flap'])],(1000,800),eye).save(preview_dir/name)
    render([(stl_path('flange'),COLORS['frame'])],(1000,600),(0,0,1)).save(preview_dir/'frame-dudukan-bak-atas.png')
    pinion_preview=Image.new('RGB',(1400,700),tuple(BG))
    label=ImageDraw.Draw(pinion_preview)
    for x,axis,eye in [(0,'pan',(1.4,-2,-1.6)),(700,'tilt',(1.4,-2,1.6))]:
        detail=render([(stl_path('pinion_'+axis),COLORS['gear']),
                       (stl_path('pinion_'+axis+'_fastener'),COLORS['steel'])],(660,490),eye)
        pinion_preview.paste(detail,(x+20,90))
        label.text((x+30,25),f'PINION {axis.upper()} — CETAK 1',font=font(26,True),fill='#193748')
        label.text((x+30,590),'Poros bulat 5 mm · baut M3x16 + mur M3',font=font(22),fill='#4e6473')
    label.text((30,650),'Penjepit bercelah — tanpa mengikir poros. Prototipe: uji fit dan selip sebelum digunakan.',font=font(21),fill='#995328')
    pinion_preview.save(preview_dir/'pinion-poros-bulat.png')
    print(json.dumps(checks['assembly'],indent=2),flush=True)
if __name__=='__main__':main()
