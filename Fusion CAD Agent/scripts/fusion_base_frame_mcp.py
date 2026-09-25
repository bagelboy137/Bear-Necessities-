import adsk.core, adsk.fusion

IN = 2.54  # Fusion API is ALWAYS centimetres; spec is in inches.
W, D, H, P = 24.0 * IN, 20.0 * IN, 18.0 * IN, 1.0 * IN


def box(root, lx, ly, lz, x, y, z):
    """One extrusion member: rectangle sketched at (x,y) then extruded lz."""
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(x, y, 0),
        adsk.core.Point3D.create(x + lx, y + ly, 0))
    prof = sk.profiles.item(0)
    ext = root.features.extrudeFeatures
    inp = ext.createInput(prof, adsk.fusion.FeatureOperations.JoinFeatureOperation
                          if root.bRepBodies.count else
                          adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    start = adsk.fusion.FromEntityStartDefinition.create(
        root.xYConstructionPlane, adsk.core.ValueInput.createByReal(z))
    inp.startExtent = start
    inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(lz))
    return ext.add(inp)


def run(_context: str):
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    root = design.rootComponent

    members = []
    for x in (0, W - P):                       # 4 vertical posts
        for y in (0, D - P):
            members.append((P, P, H, x, y, 0))
    for y in (0, D - P):                       # 4 width rails (X), between posts
        for z in (0, H - P):
            members.append((W - 2 * P, P, P, P, y, z))
    for x in (0, W - P):                       # 4 depth rails (Y), between posts
        for z in (0, H - P):
            members.append((P, D - 2 * P, P, x, P, z))

    for m in members:
        box(root, *m)

    bodies = root.bRepBodies
    vol = sum(bodies.item(i).volume for i in range(bodies.count))
    bb = bodies.item(0).boundingBox
    for i in range(1, bodies.count):
        b = bodies.item(i).boundingBox
        bb.combine(b)
    print("members placed:", len(members))
    print("bodies:", bodies.count)
    print("bbox in:  %.3f x %.3f x %.3f" % ((bb.maxPoint.x - bb.minPoint.x) / IN,
                                            (bb.maxPoint.y - bb.minPoint.y) / IN,
                                            (bb.maxPoint.z - bb.minPoint.z) / IN))
    print("volume in^3: %.3f" % (vol / (IN ** 3)))
