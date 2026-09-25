```python
# Creates a 100 x 60 x 6 mm rectangular plate
# ASSUMPTIONS: Material is unspecified, thickness is 6 mm

import adsk.core
import adsk.fusion
import traceback

def run(context):
    try:
        app = context.application
        ui = app.userInterface
        
        # Get the active document and root component
        doc = app.activeDocument
        design = adsk.fusion.Design.cast(doc.design)
        rootComp = design.rootComponent
        
        # Define dimensions
        length = 100.0  # cm
        width = 60.0   # cm
        thickness = 6.0  # cm
        
        # Create a new sketch on the XY plane
        sketches = rootComp.sketches
        xyPlane = rootComp.modelRoot.findItem("XY Plane")
        sketch = sketches.add(xyPlane)
        
        # Draw the rectangle
        lines = sketch.sketchCurves.sketchLines
        line1 = lines.addByTwoPoints(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(length, 0, 0))
        line2 = lines.addByTwoPoints(adsk.core.Point3D.create(length, 0, 0), adsk.core.Point3D.create(length, width, 0))
        line3 = lines.addByTwoPoints(adsk.core.Point3D.create(length, width, 0), adsk.core.Point3D.create(0, width, 0))
        line4 = lines.addByTwoPoints(adsk.core.Point3D.create(0, width, 0), adsk.core.Point3D.create(0, 0, 0))
        
        # Create a profile from the sketch
        profiles = rootComp.features.sketchBasedFeatures
        extrudeInput = profiles.addExtrude(sketch, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        extrudeInput.setDistanceExtent(adsk.core.ValueInput.createByReal(thickness))
        
        # Finalize the feature
        extrudeFeature = extrudeInput.feature
        
        ui.messageBox('Rectangular plate created successfully.')
    except:
        ui.messageBox(traceback.format_exc())
```