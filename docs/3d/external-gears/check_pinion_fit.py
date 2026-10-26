"""Rev G1 round-shaft pinion clearance, including clamp bolt/nut envelopes.
Nominal rigid meshes only. Does not validate clamp force, print tolerance or creep.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json, subprocess, tempfile
import numpy as np
import trimesh
from build import objects, matrix
from parts import stl_path
ROOT=Path(__file__).resolve().parent


def intersects_bounds(a,b):
    return bool(np.all(np.minimum(a[1],b[1])-np.maximum(a[0],b[0])>1e-5))


def run(case):
    axis,angle=case
    p,t=(angle,0) if axis=='pan' else (0,angle)
    objs=objects()
    target='pinion_'+axis
    movers=[];others=[]
    for o in objs:
        m=trimesh.load(stl_path(o['part']),force='mesh').apply_transform(matrix(o,p,t))
        if o['part'] in (target,target+'_fastener'):movers.append(m)
        else:others.append((o['part'],m))
    moving=trimesh.util.concatenate(movers)
    candidates=[(n,m) for n,m in others if intersects_bounds(moving.bounds,m.bounds)]
    with tempfile.TemporaryDirectory(prefix='pinion-fit-') as d:
        d=Path(d);moving.export(d/'moving.stl')
        imports=[]
        for i,(n,m) in enumerate(candidates):
            dest=d/f'{i}.stl';m.export(dest);imports.append('import('+json.dumps(str(dest))+');')
        (d/'test.scad').write_text('intersection(){import('+json.dumps(str(d/'moving.stl'))+');union(){'+''.join(imports)+'}}')
        q=subprocess.run(['openscad','-o',str(d/'hit.stl'),str(d/'test.scad')],capture_output=True,text=True,timeout=180)
        empty='Current top level object is empty' in q.stderr
        if not empty:
            (ROOT/'pinion-fit-failure.log').write_text(q.stderr)
            if (d/'hit.stl').exists():(ROOT/'pinion-fit-failure.stl').write_bytes((d/'hit.stl').read_bytes())
        assert empty,(axis,angle,[n for n,_ in candidates],q.stderr)
    print('CLEAR',axis,angle,flush=True)
    return dict(axis=axis,angle_deg=angle,broadphase_candidates=[n for n,_ in candidates],result='empty intersection')


def main():
    # Minimum/maximum published shaft projection: 23 +/-1mm from motor face.
    lengths=[22,23,24]
    engagement={}
    for axis,z0,z1 in [('pan',6.2,11.7),('tilt',12.3,20)]:
        overlap=[max(0,min(z1,L)-max(z0,2)) for L in lengths]
        assert all(abs(x-(z1-z0))<1e-6 for x in overlap)
        engagement[axis]=dict(clamp_from_motor_face_mm=[z0,z1],shaft_lengths_mm=lengths,engaged_clamp_length_mm=overlap)
    # Pan min clearance stays constant through rotation about motor shaft.
    pan=trimesh.load(stl_path('pinion_pan'),force='mesh')
    fast=trimesh.load(stl_path('pinion_pan_fastener'),force='mesh')
    base_gap=float(pan.bounds[0,2]+12-6)
    fast_gap=float(fast.bounds[0,2]+12-6)
    assert base_gap>=.199 and fast_gap>=.249
    # M3 mounting bolt heads are on radius sqrt(2)*15.5 (max head diameter5.5).
    radial=max(np.linalg.norm(pan.vertices[:,:2],axis=1).max(),np.linalg.norm(fast.vertices[:,:2],axis=1).max())
    motor_bolt_gap=float(2**.5*15.5-2.75-radial)
    assert motor_bolt_gap>0
    cases=[('pan',a) for a in [-90,-77,-61,-44,-26,-9,0,14,31,49,67,82,90]]
    cases += [('tilt',a) for a in [-60,-51,-41,-29,-17,-7,0,11,23,34,43,53,60]]
    with ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(run,cases))
    report=dict(revision='G1',motor='42HD4027-01',target_round_shaft_diameter_mm=5,bore_mm=5.1,
                engagement=engagement,pan_clamp_to_base_mm=base_gap,pan_fastener_to_base_mm=fast_gap,
                conservative_radial_clearance_to_motor_bolt_heads_mm=motor_bolt_gap,sampled_cases=results,
                limitations=['Rigid nominal geometry only; no elastic clamp closure simulated.',
                             '0.20mm base clearance requires a flat, cleaned print and physical check.',
                             'Nut orientation: flats parallel to base; no washer; screw head diameter <=5.5mm.',
                             'Sampled angles are not a continuous collision proof.',
                             'Grip torque, PETG creep, fatigue and running motor torque require physical tests.'])
    (ROOT/'pinion-fit-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='sampled_cases'},indent=2))

if __name__=='__main__': main()
