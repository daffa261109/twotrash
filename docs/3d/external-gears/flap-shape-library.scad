// Shared 200 x 250 mm dish geometry for locked Rev G. Units mm.
// Dish and ribs only; integral axle supports are in rakitan.scad.

/* ===== PARAMETER ===== */
plate_w      = 200;   // lebar piring (sumbu X)
plate_l      = 250;   // panjang piring (sumbu Y)
plate_t      = 3;     // tebal dinding piring, sama di seluruh lengkung
dish_depth   = 40;    // naiknya lengkung dari tengah ke sudut piring
corner_r     = 40;    // radius sudut piring

// Tulangan di bawah piring: silang, dua diagonal, dan cincin di tepi.
rib_t        = 3;     // tebal tulangan
rib_h        = 7;     // tinggi tulangan di bawah lengkung
$fn          = 96;

/* ===== LENGKUNG ===== */
// Bola dipipihkan di X supaya lengkung mengikuti proporsi piring.
sx = plate_w / plate_l;
// Jarak sudut piring dari tengah dalam ukuran bola (setelah X dilebarkan kembali).
a_corner = (plate_l / 2) * sqrt(2);
// Radius bola agar sudut piring naik tepat dish_depth dari titik terendah.
R = (a_corner * a_corner + dish_depth * dish_depth) / (2 * dish_depth);
body_h = plate_t + dish_depth;

// Bola dalam. Titik terendahnya ada di z = plate_t.
module inner_sphere() {
    translate([0, 0, plate_t + R])
        scale([sx, 1, 1]) sphere(r = R, $fn = 200);
}

// Bola luar. Radius sama, digeser turun plate_t. Titik terendahnya z = 0.
module outer_sphere() {
    translate([0, 0, R])
        scale([sx, 1, 1]) sphere(r = R, $fn = 200);
}

module rounded_rect(w, l, r, h) {
    linear_extrude(height = h)
        offset(r = r) square([w - 2 * r, l - 2 * r], center = true);
}

/* ===== BENTUK ===== */
module shell() {
    intersection() {
        rounded_rect(plate_w, plate_l, corner_r, body_h);
        outer_sphere();
    }
}

// Tulangan mengikuti lengkung: selapis setebal rib_h tepat di bawah dinding piring.
module rib_band() {
    difference() {
        translate([0, 0, -rib_h]) outer_sphere();
        // Naik 0,5 mm supaya tulangan masuk sedikit ke dinding dan menyatu dengannya.
        translate([0, 0, 0.5]) outer_sphere();
    }
}

module rib_slabs() {
    z0 = -rib_h - 1;
    h = rib_h + body_h + 2;
    diag = sqrt(plate_w * plate_w + plate_l * plate_l);
    ang = atan2(plate_w, plate_l);
    // Silang melalui tengah: satu searah X, satu searah Y.
    translate([-plate_w / 2, -rib_t / 2, z0]) cube([plate_w, rib_t, h]);
    translate([-rib_t / 2, -plate_l / 2, z0]) cube([rib_t, plate_l, h]);
    // Dua diagonal ke sudut piring.
    for (s = [-1, 1])
        rotate([0, 0, s * ang])
            translate([-rib_t / 2, -diag / 2, z0]) cube([rib_t, diag, h]);
    // Cincin tipis di sepanjang tepi piring.
    translate([0, 0, z0])
        difference() {
            rounded_rect(plate_w, plate_l, corner_r, h);
            translate([0, 0, -1])
                rounded_rect(plate_w - 2 * rib_t, plate_l - 2 * rib_t,
                             max(corner_r - rib_t, 0.5), h + 2);
        }
}

module ribs() {
    intersection() {
        rounded_rect_tall();
        rib_band();
        rib_slabs();
    }
}

// Batas samping piring untuk tulangan, dari bawah lengkung sampai atas.
module rounded_rect_tall() {
    translate([0, 0, -rib_h - 1])
        rounded_rect(plate_w, plate_l, corner_r, rib_h + body_h + 2);
}

module dish() {
    difference() {
        union() {
            shell();
            ribs();
        }
        inner_sphere();
    }
}
