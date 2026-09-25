def run(_context: str):
    IN = 2.54  # Conversion factor from inches to centimeters

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    # Dimensions in inches
    L, W, T = 6.000 * IN, 2.000 * IN, 0.250 * IN
    Holes = [(-2.000 * IN, 0.000 * IN, 0.281 * IN), (2.000 * IN, 0.000 * IN, 0.281 * IN), (0.000 * IN, 1.000 * IN - 0.625 * IN, 0.266 * IN)]
    Radius = 0.375 * IN

    # Create the plate
    plate(root, L, W, T, Radius, Holes)

    # Print the final outside dimensions in inches
    print(f"Final dimensions: L={L / IN} inches, W={W / IN} inches, H={T / IN} inches")

def plate(root, L, W, T, R, holes):   # holes = [(x, y, dia), ...] in cm
    VI = adsk.core.ValueInput
    P3 = adsk.core.Point3D
    ext = root.features.extrudeFeatures

    sk = root.sketches.add(root.xYConstructionPlane)
    sk.sketchCurves.sketchLines.addTwoPointRectangle(
        P3.create(-L/2, -W/2, 0), P3.create(L/2, W/2, 0))
    inp = ext.createInput(sk.profiles.item(0),
                          adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    inp.setDistanceExtent(False, VI.createByReal(T))
    body = ext.add(inp).bodies.item(0)

    # Fillet only the VERTICAL corner edges (start and end share x and y).
    edges = adsk.core.ObjectCollection.create()
    for e in body.edges:
        g = e.geometry
        try:
            sp, ep = g.startPoint, g.endPoint
        except AttributeError:
            continue
        if abs(sp.x - ep.x) < 1e-9 and abs(sp.y - ep.y) < 1e-9:
            edges.add(e)
    fin = root.features.filletFeatures.createInput()
    fin.addConstantRadiusEdgeSet(edges, VI.createByReal(R), True)
    root.features.filletFeatures.add(fin)

    # All holes in ONE sketch, then one cut through everything.
    sk2 = root.sketches.add(root.xYConstructionPlane)
    for (hx, hy, dia) in holes:
        sk2.sketchCurves.sketchCircles.addByCenterRadius(P3.create(hx, hy, 0), dia/2)
    profs = adsk.core.ObjectCollection.create()
    for i in range(sk2.profiles.count):
        profs.add(sk2.profiles.item(i))
    cin = ext.createInput(profs, adsk.fusion.FeatureOperations.CutFeatureOperation)
    cin.setAllExtent(adsk.fusion.ExtentDirections.NegativeExtentDirection)
    ext.add(cin)
    return body