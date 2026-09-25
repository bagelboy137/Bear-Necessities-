import cadquery as cq
from cadquery import exporters

# Dimensions in inches
L, W, T = 4.000, 1.500, 0.250
R = 0.250

# Create the flat plate with rounded corners
plate = (cq.Workplane("XY")
         .box(L, W, T, centered=(True, True, False))   # centred in X and Y, sits on Z=0
         .edges("|Z")                                   # the 4 vertical corner edges
         .fillet(R))

# Holes at explicit (x, y) positions measured from the plate centre:
plate = (plate.faces(">Z").workplane()
         .pushPoints([(-1.0, 0.0), (1.0, 0.0)])          # 2 holes 2.0" apart
         .hole(0.281))                                   # through hole, diameter

plate = (plate.faces(">Z").workplane()
         .pushPoints([(1.5, 0.0)])
         .hole(0.266))

# Export the result
result = plate
STEP_PATH = '/Users/cmken/Claude/Fusion CAD Agent/exports/C-01-anchor-plate.step'
STL_PATH = '/Users/cmken/Claude/Fusion CAD Agent/exports/C-01-anchor-plate.stl'
exporters.export(result, STEP_PATH)
exporters.export(result, STL_PATH)