pi_length_x = 65;
pi_length_y = 30;
pi_pcb_height = 1;
pi_component_height = 4;
pi_total_height = pi_pcb_height + pi_component_height;
pi_screw_inset = 3.5;
pi_corner_radius = 3;
pi_screw_clearance = 2.7 / 2;

module pi_base() {
    cube([pi_length_x, pi_length_y, pi_pcb_height]);
    translate([0, 0, pi_pcb_height]) cube([pi_length_x, pi_length_y, pi_component_height]);
}

module screw_hole(depth=pi_pcb_height, radius=pi_screw_clearance) {
    cylinder(h=depth, r1=radius, r2=radius, $fn=50);
}

module pi_corner() {
    cylinder(h=pi_pcb_height, r1=pi_corner_radius, r2=pi_corner_radius, $fn=50);
}
/*
difference() {
    color([0, 1, 0]) pi_base();
    translate([pi_screw_inset, pi_screw_inset, 0]) screw_hole();
    translate([pi_length_x - pi_screw_inset, pi_screw_inset, 0]) screw_hole();
    translate([pi_screw_inset, pi_length_y - pi_screw_inset, 0]) screw_hole();
    translate([pi_length_x - pi_screw_inset, pi_length_y - pi_screw_inset, 0]) screw_hole();
    difference() {
        pi_base();
        translate([pi_corner_radius, 0, 0]) cube([pi_length_x - 2 * pi_corner_radius, pi_length_y, pi_pcb_height]);
        translate([0, pi_corner_radius, 0]) cube([pi_length_x, pi_length_y - 2 * pi_corner_radius, pi_pcb_height]);
        translate([pi_corner_radius, pi_corner_radius, 0]) pi_corner();
        translate([pi_length_x - pi_corner_radius, pi_corner_radius, 0]) pi_corner();
        translate([pi_corner_radius, pi_length_y - pi_corner_radius, 0]) pi_corner();
        translate([pi_length_x - pi_corner_radius, pi_length_y - pi_corner_radius, 0]) pi_corner();
    }
}*/

wall_thickness = 2;
plate_thickness = wall_thickness * 2;
mount_protrusion = 13;
thread_hole_radius = 1.5 / 2;
plate_screw_inset_x = 5;
plate_screw_inset_y = 7;

module plate() {
    translate([0, 0, -plate_thickness]) difference() {
        cube([pi_length_x, pi_length_y, plate_thickness]);
        translate([pi_screw_inset, pi_screw_inset, 0]) screw_hole(plate_thickness, thread_hole_radius);
        translate([pi_length_x - pi_screw_inset, pi_screw_inset, 0]) screw_hole(plate_thickness, thread_hole_radius);
        translate([pi_screw_inset, pi_length_y - pi_screw_inset, 0]) screw_hole(plate_thickness, thread_hole_radius);
        translate([pi_length_x - pi_screw_inset, pi_length_y - pi_screw_inset, 0]) screw_hole(plate_thickness, thread_hole_radius);
    }

    translate([pi_length_x, 0, -wall_thickness]) difference() {
        cube([mount_protrusion, pi_length_y, wall_thickness]);
        translate([mount_protrusion - plate_screw_inset_x, pi_length_y - plate_screw_inset_y, 0]) screw_hole(wall_thickness);
        translate([mount_protrusion - plate_screw_inset_x, plate_screw_inset_y, 0]) screw_hole(wall_thickness);
    }
}

cover_screw_inset = 10;

difference() {
    plate();
    translate([cover_screw_inset + thread_hole_radius, plate_thickness, -wall_thickness]) rotate([90, 0, 0]) screw_hole(plate_thickness, thread_hole_radius);
    translate([pi_length_x - cover_screw_inset - thread_hole_radius, plate_thickness, -wall_thickness]) rotate([90, 0, 0]) screw_hole(plate_thickness, thread_hole_radius);
    translate([cover_screw_inset + thread_hole_radius, pi_length_y, -wall_thickness]) rotate([90, 0, 0]) screw_hole(plate_thickness, thread_hole_radius);
    translate([pi_length_x - cover_screw_inset - thread_hole_radius, pi_length_y, -wall_thickness]) rotate([90, 0, 0]) screw_hole(plate_thickness, thread_hole_radius);
}

rotate([180, 0, 0]) {
    translate([0, 4 * wall_thickness, -3]) {
        translate([0, 0, pi_total_height]) cube([pi_length_x, pi_length_y, wall_thickness]);

        translate([-wall_thickness, 0, -2 * wall_thickness]) cube([wall_thickness, pi_length_y, pi_total_height + 3 * wall_thickness]);

        translate([pi_length_x, 0, 0]) cube([wall_thickness, pi_length_y, pi_total_height + wall_thickness]);

        translate([0, -wall_thickness, 0]) difference() {
            translate([-wall_thickness, 0, -2 * wall_thickness]) cube([pi_length_x + 2 * wall_thickness, wall_thickness, pi_total_height + 3 * wall_thickness]);
            translate([cover_screw_inset + thread_hole_radius, wall_thickness, -wall_thickness]) rotate([90, 0, 0]) screw_hole(wall_thickness, thread_hole_radius);
            translate([pi_length_x - cover_screw_inset - thread_hole_radius, wall_thickness, -wall_thickness]) rotate([90, 0, 0]) screw_hole(wall_thickness, thread_hole_radius);
        }

        translate([0, wall_thickness, 0]) difference() {
            translate([-wall_thickness, pi_length_y - wall_thickness, -2 * wall_thickness]) cube([pi_length_x + 2 * wall_thickness, wall_thickness, pi_total_height + 3 * wall_thickness]);
            translate([cover_screw_inset + thread_hole_radius, pi_length_y, -wall_thickness]) rotate([90, 0, 0]) screw_hole(wall_thickness, thread_hole_radius);
            translate([pi_length_x - cover_screw_inset - thread_hole_radius, pi_length_y, -wall_thickness]) rotate([90, 0, 0]) screw_hole(wall_thickness, thread_hole_radius);
            translate([5, pi_length_y - wall_thickness, 0]) cube([25, wall_thickness, 5]);
        }
    }
}