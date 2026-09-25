```python
# Creates a 100 x 60 x 6 mm rectangular plate.
# ASSUMPTIONS: Material is steel, orientation is default (XY plane).

import adsk.core
import adsk.fusion
import traceback

def run(context):
    try:
        app = adsk.core.Application.get()
        design = app.activeProduct
        rootComp = design.rootComponent

        # Dimensions in cm
        LENGTH = 10.0  # 100 mm
        WIDTH = 6.0    # 60 mm
        HEIGHT = 0.6   # 6 mm

        # Create a new sketch on the XY plane
        sketches = rootComp.sketches
        xyPlane = rootComp.xYConstructionPlane
        sketch = sketches.add(xyPlane)

        # Draw a rectangle in the sketch
        lines = sketch.sketchLines
        startPoint = adsk.core.Point3D.create(0, 0, 0)
        endPoint = adsk.core.Point3D.create(LENGTH, WIDTH, 0)
        rectangleLine1 = lines.addByTwoPoints(startPoint, endPoint)

        startPoint = adsk.core.Point3D.create(LENGTH, WIDTH, 0)
        endPoint = adsk.core.Point3D.create(0, WIDTH, 0)
        rectangleLine2 = lines.addByTwoPoints(startPoint, endPoint)

        startPoint = adsk.core.Point3D.create(0, WIDTH, 0)
        endPoint = adsk.core.Point3D.create(0, 0, 0)
        rectangleLine3 = lines.addByTwoPoints(startPoint, endPoint)

        startPoint = adsk.core.Point3D.create(0, 0, 0)
        endPoint = adsk.core.Point3D.create(LENGTH, 0, 0)
        rectangleLine4 = lines.addByTwoPoints(startPoint, endPoint)

        # Create an extrusion from the sketch
        extrudes = rootComp.features.extrudeFeatures
        extrudeInput = extrudes.createInput(sketch.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(HEIGHT)
        extrudeInput.setDistanceExtent(False, distance)
        extrudeFeature = extrudes.add(extrudeInput)

    except:
        ui = app.userInterface
        ui.messageBox(traceback.format_exc())
```