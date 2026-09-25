```openscad
module l_bracket(leg1_length, leg2_length, thickness, width, hole_diameter) {
    difference() {
        union() {
            cube([leg1_length, thickness, width]);
            translate([leg2_length - hole_diameter / 2, thickness / 2, width / 2])
                cylinder(h = leg1_length, r = hole_diameter / 2);
            translate([leg2_length - hole_diameter / 2, thickness / 2 + width / 2, width / 2])
                cylinder(h = leg1_length, r = hole_diameter / 2);
        }
        translate([leg1_length - thickness / 2, 0, width / 2])
            cube([thickness, leg1_length, width]);
        translate([leg1_length - thickness / 2 + hole_diameter / 2, leg1_length - hole_diameter / 2, width / 2])
            cylinder(h = thickness, r = hole_diameter / 2);
        translate([leg1_length - thickness / 2 + hole_diameter / 2, leg1_length - hole_diameter / 2 + width / 2, width / 2])
            cylinder(h = thickness, r = hole_diameter / 2);
    }
}

l_bracket(leg1_length = 80, leg2_length = 60, thickness = 5, width = 40, hole_diameter = 6);
```