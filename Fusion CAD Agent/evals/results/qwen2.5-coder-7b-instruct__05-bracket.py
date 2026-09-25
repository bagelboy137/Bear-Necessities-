```python
# 90 degree L-bracket with legs of 80 mm and 60 mm, 5 mm thick, 40 mm wide
# ASSUMPTIONS: Material is steel, thickness is 5 mm, tolerance is ±0.1 mm

import adsk.core
import adsk.fusion
import traceback

def run(context):
    ui = context.application.userInterface
    
    try:
        # Get the active design
        design = adsk.fusion.DesignManager.activeDesign
        
        # Create a new component in the root component
        rootComp = design.rootComponent
        sketches = rootComp.sketches
        
        # Create a new sketch on the XY plane
        xyPlane = rootComp.model.workplanes.itemByName("XY Plane")
        sketch = sketches.add(xyPlane)
        
        # Define dimensions
        leg1_length = 80.0  # cm
        leg2_length = 60.0  # cm
        thickness = 5.0     # cm
        width = 40.0        # cm
        hole_diameter = 6.0 # cm
        
        # Draw the first leg (vertical)
        vertical_line = sketch.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(0, leg1_length, 0))
        
        # Draw the second leg (horizontal)
        horizontal_line = sketch.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(0, leg1_length, 0), adsk.core.Point3D.create(leg2_length, leg1_length, 0))
        
        # Draw the triangular gusset
        gusset_line1 = sketch.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(leg2_length, 0, 0))
        gusset_line2 = sketch.sketchCurves.sketchLines.addByTwoPoints(adsk.core.Point3D.create(leg2_length, 0, 0), adsk.core.Point3D.create(leg2_length, leg1_length, 0))
        
        # Create a profile from the sketch
        profiles = rootComp.features.sketchBasedFeatures.addExtrude(sketch, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        profile = profiles[0].profile
        
        # Create the first leg feature
        extrude1 = rootComp.features.extrudeFeatures.add(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude1.distance = adsk.core.ValueInput.createByReal(leg1_length - thickness)
        
        # Create the second leg feature
        extrude2 = rootComp.features.extrudeFeatures.add(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude2.distance = adsk.core.ValueInput.createByReal(leg2_length - thickness)
        
        # Create the triangular gusset feature
        extrude3 = rootComp.features.extrudeFeatures.add(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrude3.distance = adsk.core.ValueInput.createByReal(thickness)
        
        # Create holes in the legs
        hole_diameter = 6.0  # cm
        hole_radius = hole_diameter / 2.0  # cm
        
        # Create holes in the first leg
        hole1 = rootComp.features.holeFeatures.add(profile, adsk.core.ValueInput.createByReal(hole_radius), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        hole1.depth = adsk.core.ValueInput.createByReal(leg1_length - thickness)
        
        hole2 = rootComp.features.holeFeatures.add(profile, adsk.core.ValueInput.createByReal(hole_radius), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        hole2.depth = adsk.core.ValueInput.createByReal(leg1_length - thickness)
        
        # Create holes in the second leg
        hole3 = rootComp.features.holeFeatures.add(profile, adsk.core.ValueInput.createByReal(hole_radius), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        hole3.depth = adsk.core.ValueInput.createByReal(leg2_length - thickness)
        
        hole4 = rootComp.features.holeFeatures.add(profile, adsk.core.ValueInput.createByReal(hole_radius), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        hole4.depth = adsk.core.ValueInput.createByReal(leg2_length - thickness)
        
        ui.messageBox("L-bracket created successfully.")
    except:
        ui.messageBox(traceback.format_exc())
```