// Rev G: empty flap only. External spur gears, 3:1 on each axis. Units mm.
// This is a fit/motion prototype, not a tested payload rating.
use <flap-shape-library.scad>
use <gear_profiles.scad>
$fn=64;
part="assembly"; pan=0; tilt=-35; show_rails=true;
axis_z=100; cd=38.4;
assert(abs(pan)<=90 && abs(tilt)<=60);
module cyly(d,h){rotate([90,0,0])cylinder(d=d,h=h,center=true);}
module cylx(d,h){rotate([0,90,0])cylinder(d=d,h=h,center=true);}
module d_bore(d=8.15,flat=3.075,h=100){linear_extrude(h,center=true)difference(){circle(d=d);translate([flat,-d])square([d,2*d]);}}
module annulus(od,id,h){difference(){cylinder(d=od,h=h);translate([0,0,-.1])cylinder(d=id,h=h+.2);}}
module nut_screw(y=0,z=0){
    translate([0,y,z])cylx(3.3,30);
    translate([8,y,z])rotate([0,90,0])cylinder(d=6.6,h=3,$fn=6);
    // Drop-in M3 nut access, perpendicular to the set screw.
    translate([8,y-2.9,z])cube([3,5.8,30]);
}
module motor(){
    // Envelope from 17HS15-1504S1: face42.3MAX, length39+/-1, shaft24+/-1.
    difference(){translate([-21.15,-21.15,-40])cube([42.3,42.3,40]);
      for(x=[-15.5,15.5],y=[-15.5,15.5])translate([x,y,-4.5])cylinder(d=3,h=4.6);}
    cylinder(d=22,h=2);
    difference(){cylinder(d=5,h=24);translate([2,-3,9])cube([3,6,16]);}
}
module pinion(){difference(){union(){linear_extrude(8)pinion_profile();translate([0,0,7.8])cylinder(d=16,h=5.2);}
    d_bore(5.1,2.05,40);translate([0,0,10.5])cylx(3.2,20);
    translate([4.5,0,10.5])rotate([0,90,0])cylinder(d=6.6,h=3,$fn=6);
    translate([4.5,-2.9,10.5])cube([3,5.8,8]);
}}
module driven(){difference(){union(){rotate([0,0,3.75])linear_extrude(8)driven_profile();
    translate([0,0,-4])cylinder(d=18,h=4.2);translate([0,0,7.8])cylinder(d=24,h=6.2);}
    d_bore();nut_screw(z=11);
}}
module flange(){difference(){union(){
    translate([-33,-33,0])cube([66,98,6]);
    translate([0,0,-20])cylinder(d=34,h=20.2);
    for(s=[-1,1])translate([s*50,0,3])cube([40,30,6],center=true);
  }
  translate([0,0,-20.1])cylinder(d=11,h=26.2);
  translate([0,0,-18])cylinder(d=22.1,h=7);
  translate([0,0,-5])cylinder(d=22.1,h=7);
  translate([0,0,1.9])cylinder(d=18.4,h=4.2);
  // The bearing cartridge splits along X=0; supplied as two printable halves.
  for(y=[-12.5,12.5])translate([0,y,-9])cylx(3.4,40);
  for(s=[-1,1],y=[-8,8])translate([s*52.5,y,-.1])cylinder(d=3.7,h=6.2);
  translate([0,cd,-.1])cylinder(d=22.4,h=2.4);
  translate([0,cd,-.1])cylinder(d=8,h=6.2);
  for(x=[-15.5,15.5],y=[cd-15.5,cd+15.5])translate([x,y,-.1])cylinder(d=3.4,h=6.2);
}}
module base_left(){intersection(){flange();translate([-100,-100,-50])cube([100,220,80]);}}
module base_right(){intersection(){flange();translate([0,-100,-50])cube([100,220,80]);}}
module pan_shaft(){difference(){translate([0,0,-25])cylinder(d=8,h=63);
    translate([3,-5,9])cube([4,10,30]);}}
module tilt_shaft(){difference(){translate([0,-2,axis_z])cyly(8,104);
    for(a=[[-54,18],[-22,44]])translate([3,a[0],axis_z-5])cube([4,a[1],10]);}}
module collar(){difference(){annulus(16,8.1,5);translate([0,0,2.5])cylx(2.5,20);}}
module pan_bearings(){for(z=[-18,-5])translate([0,0,z])annulus(22,8,7);}
module tilt_bearings(){for(y=[-32,32])translate([0,y+3.5,axis_z])rotate([90,0,0])annulus(22,8,7);}
module pan_collars(){for(z=[-23,2.2])translate([0,0,z])collar();}
module tilt_collar(){translate([0,41,axis_z])rotate([90,0,0])collar();}
module head_frame(){difference(){union(){
    translate([-33,-41,30])cube([66,82,6]);
    translate([0,0,27])cylinder(d=24,h=3.2);
    // Side walls clear the tilt motor and tie both bearing supports to the bed.
    for(x=[-33,28])translate([x,-41,35.8])cube([5,82,50.2]);
    translate([-33,-35.5,85.8])cube([66,7,14.2]);
    translate([-17,28.5,35.8])cube([34,7,64.2]);
    // Tilt motor bolts through a separate vertical face integral with frame.
    translate([-26,-40,35.8])cube([52,4,50.2]);
  }
  translate([0,0,30])d_bore(h=25);nut_screw(z=32.5);
  for(y=[-32,32])translate([0,y,axis_z])cyly(22.1,7.2);
  for(y=[-32,32])translate([0,y,axis_z-12.5])cyly(2,7.2);
  for(y=[-32,32],x=[-14,14])translate([x,y,88])cylinder(d=2.5,h=13);
  translate([0,-38,axis_z-cd])cyly(22.4,5);
  for(x=[-15.5,15.5],z=[axis_z-cd-15.5,axis_z-cd+15.5])translate([x,-38,z])cyly(3.4,5);
}}
module bearing_caps(){for(y=[-32,32])difference(){
    translate([-17,y-3.5,axis_z])cube([34,7,15]);
    translate([0,y,axis_z])cyly(22.1,7.2);
    translate([0,y,axis_z+12.5])cyly(2,7.2);
    for(x=[-14,14])translate([x,y,axis_z-.1])cylinder(d=3.3,h=15.2);
}}
module bearing_retainers(){for(y=[-36.5,-27.5,27.5,36.5])difference(){
    translate([0,y,axis_z])cyly(27,1.6);
    translate([0,y,axis_z])cyly(18.6,1.8);
    for(z=[-12.5,12.5])translate([0,y,axis_z+z])cyly(2.5,1.8);
}}
module flap_support(){difference(){union(){
    for(y=[-40,40])translate([-85,y-9,35])cube([170,18,4.4]);
    translate([-9,-49,35])cube([18,98,4.4]);
    for(y=[-16,16]){
      translate([0,y,0])cyly(24,10);
      hull(){translate([-6,y-5,8])cube([12,10,2]);translate([-6,y-6,35])cube([12,12,4.4]);}
    }
    difference(){for(x=[-60,60],y=[-40,40])translate([x,y,39])cylinder(d=14,h=45);
      translate([0,0,47])inner_sphere();}
  }
  rotate([90,0,0])d_bore();for(y=[-16,16])nut_screw(y=y);
}}
module tray_only(){translate([0,0,47])dish();}
module new_flap(){union(){tray_only();flap_support();}}
module rails(){for(s=[-1,1])difference(){translate([s*52.5,0,-1.5])cube([35,220,3],center=true);
    for(y=[-8,8])translate([s*52.5,y,-3.1])cylinder(d=3.7,h=3.2);}}
module backplates(){for(s=[-1,1])difference(){translate([s*52.5,0,-4])cube([35,30,2],center=true);
    for(y=[-8,8])translate([s*52.5,y,-5.1])cylinder(d=3.7,h=2.2);}}
module rivets(){for(s=[-1,1],y=[-8,8])translate([s*52.5,y,0]){
    translate([0,0,-5])cylinder(d=3.5,h=11);translate([0,0,6])cylinder(d=6.5,h=1.5);}}
module tilt_motor(){translate([0,-36,axis_z-cd])rotate([90,0,0])motor();}
module assembly(){
    if(show_rails)color([.52,.67,.78])rails();
    color([.3,.4,.5])flange();color([.7,.75,.8]){backplates();rivets();pan_bearings();}
    color([.18,.2,.24])translate([0,cd,0])motor();
    color([.93,.65,.20])translate([0,cd,12])rotate([0,0,-3*pan])pinion();
    rotate([0,0,pan]){
      color([.93,.65,.20])translate([0,0,12])driven();
      color([.3,.4,.5]){head_frame();bearing_caps();}
      color([.7,.75,.8]){pan_shaft();pan_collars();tilt_bearings();bearing_retainers();}
      color([.18,.2,.24])tilt_motor();
      color([.93,.65,.20])translate([0,-40,axis_z-cd])rotate([90,0,0])rotate([0,0,3*tilt])pinion();
      translate([0,0,axis_z])rotate([0,tilt,0]){
        color([.25,.67,.58])new_flap();
        color([.93,.65,.20])translate([0,-40,0])rotate([90,0,0])driven();
        color([.7,.75,.8])translate([0,0,-axis_z]){tilt_shaft();tilt_collar();}
      }
    }
}
if(part=="assembly")assembly();
if(part=="flap")new_flap();
if(part=="tray_only")tray_only();
if(part=="frame")head_frame();
if(part=="flange")flange();
if(part=="base_left")base_left();
if(part=="base_right")base_right();
if(part=="caps")bearing_caps();
if(part=="retainers")bearing_retainers();
if(part=="pinion")pinion();
if(part=="driven")driven();
if(part=="motor")motor();
if(part=="pan_shaft")pan_shaft();
if(part=="tilt_shaft")tilt_shaft();
if(part=="pan_bearings")pan_bearings();
if(part=="tilt_bearings")tilt_bearings();
if(part=="pan_collars")pan_collars();
if(part=="tilt_collar")tilt_collar();
if(part=="rails")rails();
if(part=="backplates")backplates();
if(part=="rivets")rivets();
