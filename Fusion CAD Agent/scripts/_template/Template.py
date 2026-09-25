# Fusion CAD Agent — script skeleton.
# STATUS: NOT YET VERIFIED IN FUSION. Run it once by hand and update this line.
#
# Builds a rectangular plate with a single through-hole, as a smoke test that
# the whole loop works: sketch -> profile -> extrude -> cut.
#
# ASSUMPTIONS: builds into the ACTIVE document. See reference/fusion-api-notes.md
# for why that is a hazard for unattended runs.

import adsk.core
import adsk.fusion
import traceback

# --- Parameters (Fusion's API is ALWAYS in centimeters) -----------------
MM = 0.1              # multiply mm by this to get API units

PLATE_LEN = 100 * MM  # 100 mm
PLATE_WID = 60 * MM   # 60 mm
PLATE_THK = 6 * MM    # 6 mm
HOLE_DIA = 10 * MM    # 10 mm
# ------------------------------------------------------------------------


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active Fusion design. Open a design and re-run.')
            return

        root = design.rootComponent

        # 1. Sketch the plate outline on the XY plane.
        sketches = root.sketches
        sketch = sketches.add(root.xYConstructionPlane)
        lines = sketch.sketchCurves.sketchLines
        lines.addTwoPointRectangle(
            adsk.core.Point3D.create(0, 0, 0),
            adsk.core.Point3D.create(PLATE_LEN, PLATE_WID, 0),
        )

        # 2. Extrude the profile to thickness.
        profile = sketch.profiles.item(0)
        extrudes = root.features.extrudeFeatures
        ext_input = extrudes.createInput(
            profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        ext_input.setDistanceExtent(
            False, adsk.core.ValueInput.createByReal(PLATE_THK)
        )
        extrudes.add(ext_input)

        # 3. Sketch the hole at the plate centre and cut it through.
        hole_sketch = sketches.add(root.xYConstructionPlane)
        hole_sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(PLATE_LEN / 2, PLATE_WID / 2, 0),
            HOLE_DIA / 2,
        )
        cut_input = extrudes.createInput(
            hole_sketch.profiles.item(0),
            adsk.fusion.FeatureOperations.CutFeatureOperation,
        )
        cut_input.setDistanceExtent(
            False, adsk.core.ValueInput.createByReal(PLATE_THK)
        )
        extrudes.add(cut_input)

        # NOTE: messageBox BLOCKS until clicked. Remove before any unattended run.
        ui.messageBox('Template ran: plate {}x{}x{} mm with a {} mm hole.'.format(
            PLATE_LEN / MM, PLATE_WID / MM, PLATE_THK / MM, HOLE_DIA / MM))

    except:  # noqa: E722 - Fusion convention
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
