"""CPU depth-buffer CAD renderer; uses actual STL geometry without OpenGL.
Run this file to rebuild the local assembly and previews using build.py.
"""
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image, ImageFont
ROOT=Path(__file__).resolve().parent
BG=np.array([246,248,250],dtype=np.uint8)

def render(objects, size, eye):
    width,height=size
    d=np.array(eye,dtype=float);d/=np.linalg.norm(d)
    right=np.cross([0,0,1],d)
    if np.linalg.norm(right)<1e-8: right=np.array([1.,0.,0.])
    right/=np.linalg.norm(right)
    up=np.cross(d,right)
    basis=np.stack([right,up,d],axis=1)
    prepared=[]
    for path,color in objects:
        mesh=trimesh.load(path,force='mesh')
        prepared.append((mesh,color,mesh.vertices@basis))
    points=np.concatenate([p for _,_,p in prepared]);lo=points.min(axis=0);hi=points.max(axis=0)
    scale=min((width-70)/(hi[0]-lo[0]),(height-70)/(hi[1]-lo[1]))
    center=(lo+hi)/2
    image=np.broadcast_to(BG,(height,width,3)).copy()
    depth=np.full((height,width),-np.inf)
    light=np.array([-.35,-.55,.85]);light/=np.linalg.norm(light)
    for mesh,color,points in prepared:
        pp=points.copy();pp[:,0]=(pp[:,0]-center[0])*scale+width/2;pp[:,1]=height/2-(pp[:,1]-center[1])*scale
        tri=pp[mesh.faces]
        norms=mesh.face_normals
        visible=(norms@d)>0
        lighting=.36+.64*np.maximum(0,norms@light)
        colors=np.clip(np.array(color)[None,:]*lighting[:,None],0,255).astype(np.uint8)
        for t,col in zip(tri[visible],colors[visible]):
            x0=max(0,int(np.floor(t[:,0].min())));x1=min(width-1,int(np.ceil(t[:,0].max())))
            y0=max(0,int(np.floor(t[:,1].min())));y1=min(height-1,int(np.ceil(t[:,1].max())))
            if x1<x0 or y1<y0:continue
            a,b,c=t;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-9:continue
            yy,xx=np.mgrid[y0:y1+1,x0:x1+1];xx=xx+.5;yy=yy+.5
            w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
            w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
            w2=1-w0-w1
            zz=w0*a[2]+w1*b[2]+w2*c[2]
            block=depth[y0:y1+1,x0:x1+1]
            hit=(w0>=-1e-7)&(w1>=-1e-7)&(w2>=-1e-7)&(zz>block)
            block[hit]=zz[hit];image[y0:y1+1,x0:x1+1][hit]=col
    return Image.fromarray(image)

def font(size,bold=False):
    name='DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    import matplotlib
    return ImageFont.truetype(str(Path(matplotlib.__file__).parent/'mpl-data/fonts/ttf'/name),size)

if __name__=='__main__':
    import runpy
    runpy.run_path(str(ROOT/'build.py'),run_name='__main__')
