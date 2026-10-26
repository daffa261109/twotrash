"""Sampled solid collision checks for Rev G. Not a continuous swept-volume proof."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import subprocess,json,tempfile
ROOT=Path(__file__).resolve().parent
from parts import stl_path

def imp(p):return 'import('+json.dumps(str(stl_path(p)))+');'
def run(angle):
    with tempfile.TemporaryDirectory(prefix='external-gear-clearance-') as d:
        d=Path(d)
        fixed='union(){'+''.join(imp(p) for p in ['frame','caps','retainers'])+'translate([0,-36,61.6])rotate([90,0,0])'+imp('motor')+'}'
        moving='translate([0,0,100])rotate([0,'+str(angle)+',0])'+imp('flap')
        (d/'test.scad').write_text('intersection(){'+fixed+moving+'}')
        q=subprocess.run(['openscad','-o',str(d/'hit.stl'),str(d/'test.scad')],capture_output=True,text=True,timeout=180)
        empty='Current top level object is empty' in q.stderr
        if not empty:
            (ROOT/f'collision-{angle}.log').write_text(q.stderr)
            if(d/'hit.stl').exists():(ROOT/f'collision-{angle}.stl').write_bytes((d/'hit.stl').read_bytes())
        assert empty,(angle,q.stderr)
        return angle
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool:
        angles=sorted(f.result() for f in as_completed([pool.submit(run,a) for a in range(-60,61,10)]))
    report=dict(angles_deg=angles,result='empty intersection at every sampled angle',checked='Integral flap vs rotating head frame, bearing caps/retainers and tilt motor',exclusions=['Unsampled continuous sweep','Elastic deformation and manufacturing tolerance','Shaft-bearing fits and gear loaded contact','Cables and unmodeled screw heads'])
    (ROOT/'clearance-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
