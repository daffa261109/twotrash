import math, json
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon
from shapely.affinity import rotate, translate
ROOT=Path(__file__).resolve().parent
M=1.2; PA=math.radians(25); BACKLASH=.12
def inv(a): return math.tan(a)-a
def profile(z, internal=False):
    rp=M*z/2; rb=rp*math.cos(PA)
    root=rp+(1.25*M if internal else -1.25*M)
    tip=rp+(-M if internal else M)
    half=math.pi/(2*z)-BACKLASH/(2*rp)
    def theta(r):
        a=math.acos(min(1,rb/r))
        return half + (inv(a)-inv(PA) if internal else inv(PA)-inv(a))
    # Below the base circle, a radial transition approximates the cutter root.
    rr=np.linspace(root,tip,14)
    pts=[]
    for k in range(z):
        c=2*math.pi*k/z
        for r in rr: pts.append([r*math.cos(c-theta(r)),r*math.sin(c-theta(r))])
        for a in np.linspace(-theta(tip),theta(tip),5)[1:]:
            pts.append([tip*math.cos(c+a),tip*math.sin(c+a)])
        for r in rr[-2::-1]: pts.append([r*math.cos(c+theta(r)),r*math.sin(c+theta(r))])
        for a in np.linspace(c+theta(root),c+2*math.pi/z-theta(root),5)[1:-1]:
            pts.append([root*math.cos(a),root*math.sin(a)])
    return pts
profiles={name:profile(z) for name,z in [('pinion',16),('driven',48)]}
for name,pts in profiles.items():assert Polygon(pts).is_valid
(ROOT/'gear_profiles.scad').write_text('// Module1.2, PA25, backlash .12 per member; external spur gears.\n'+'\n'.join('module '+name+'_profile(){polygon(points='+json.dumps(np.round(pts,7).tolist(),separators=(',',':'))+');}' for name,pts in profiles.items())+'\n')
pinion=Polygon(profiles['pinion']); driven=Polygon(profiles['driven']); worst=0;gap=100
for a in np.linspace(0,360,721):
    big=rotate(driven,3.75+a,origin=(0,0))
    small=translate(rotate(pinion,-3*a,origin=(0,0)),0,38.4)
    worst=max(worst,big.intersection(small).area);gap=min(gap,big.distance(small))
assert worst<1e-5,worst
result=dict(module_mm=M,pressure_angle_deg=25,pinion_teeth=16,output_teeth=48,ratio=3,center_distance_mm=38.4,face_width_mm=8,backlash_per_member_mm=BACKLASH,sampled_output_angles=721,max_overlap_mm2=worst,min_sampled_gap_mm=gap,limitations=['Planar sampled unloaded geometry only; root uses radial approximation.','Print tolerance, friction, wear, shaft deflection and tooth strength not validated.'])
(ROOT/'gear-check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
