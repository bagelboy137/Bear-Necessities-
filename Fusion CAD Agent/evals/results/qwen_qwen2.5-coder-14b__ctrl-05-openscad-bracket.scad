```scad
// Dimensions
leg_length1 = 80;
leg_length2 = 60;
thickness = 5;
width = 40;
hole_diameter = 6;
gusset_height = 20;

// L-bracket
module l_bracket() {
    // First leg
    translate([0, 0, 0]) cube([width, thickness, leg_length1]);
    
    // Second leg
    translate([0, width - thickness, 0]) cube([thickness, width, leg_length2]);
    
    // Gusset
    translate([(width - thickness) / 2, thickness, leg_length1]) {
        rotate([0, 90, 0]) cube([gusset_height, thickness, width - thickness]);
    }
    
    // Holes in the first leg
    translate([width / 2, thickness / 2, hole_diameter / 2]) cylinder(h = leg_length1, r = hole_diameter / 2);
    translate([width / 2, width - thickness - hole_diameter / 2, hole_diameter / 2]) cylinder(h = leg_length1, r = hole_diameter / 2);
    
    // Holes in the second leg
    translate([thickness / 2, width - thickness / 2, hole_diameter / 2 + leg_length1]) cylinder(h = leg_length2, r = hole_diameter / 2);
    translate([thickness / 2, width - thickness - hole_diameter / 2, hole_diameter / 2 + leg_length1]) cylinder(h = leg_length2, r = hole_diameter / 2);
}

// Render the L-bracket
l_bracket();
```