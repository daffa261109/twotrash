// Flap 200×250 mm. Dua kaki menggantung ke bawah, pola lubang servo
// dari gambar braket U. Piring sama dengan Rev G.
// Satuan mm.
include <../external-gears/flap-shape-library.scad>

plate_t = 2;         // dinding piring. Tulangan tetap dari pustaka.

leg_w = 25;          // lebar kaki, gambar 25,00
leg_t = 3;           // tebal kaki
leg_r = 12.5;        // ujung kaki setengah lingkaran, lebar 25
axis_z = -50;        // poros servo 50 mm di bawah dasar piring. 62,50 - 12,50
gap = 46;            // jarak dalam antar kaki, badan servo muat
// Lubang tanduk: φ8 di tengah, empat lubang pada lingkaran diameter 18,60.
// Ditambah 0,2 mm supaya hasil cetak tetap bisa dimasuki poros dan sekrup.
shaft_d = 8.2;
screw_d = 3.2;
screw_r = 18.60 / 2;

module leg_blank() {
    translate([-leg_w / 2, -leg_t / 2, axis_z])
        cube([leg_w, leg_t, -axis_z + plate_t + 8]);
    translate([0, 0, axis_z])
        rotate([90, 0, 0])
            cylinder(r = leg_r, h = leg_t, center = true);
}

module servo_holes() {
    translate([0, 0, axis_z])
        rotate([90, 0, 0])
            cylinder(d = shaft_d, h = leg_t + 4, center = true);
    for (p = [[screw_r, 0], [-screw_r, 0], [0, screw_r], [0, -screw_r]])
        translate([p[0], 0, axis_z + p[1]])
            rotate([90, 0, 0])
                cylinder(d = screw_d, h = leg_t + 4, center = true);
}

module one_leg() {
    difference() {
        leg_blank();
        translate([0, 0, 1]) outer_sphere();
        servo_holes();
    }
}

module legs() {
    for (s = [-1, 1])
        translate([0, s * (gap / 2 + leg_t / 2), 0])
            one_leg();
}

module flap_besi() {
    dish();
    legs();
}

flap_besi();
