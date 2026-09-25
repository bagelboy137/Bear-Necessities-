def run(_context: str):
    IN = 2.54  # Conversion factor from inches to centimeters

    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent

    W, D, H, P = 24.0 * IN, 20.0 * IN, 18.0 * IN, 1.0 * IN

    MEMBERS = []
    for x in (0, W - P):  # 4 vertical posts, full height
        for y in (0, D - P):
            MEMBERS.append((P, P, H, x, y, 0))
    for y in (0, D - P):  # 4 width rails along X, between posts
        for z in (0, H - P):
            MEMBERS.append((W - 2 * P, P, P, P, y, z))
    for x in (0, W - P):  # 4 depth rails along Y, between posts
        for z in (0, H - P):
            MEMBERS.append((P, D - 2 * P, P, x, P, z))

    for (lx, ly, lz, x, y, z) in MEMBERS:
        box(root, lx, ly, lz, x, y, z)

    # Print the final outside dimensions in inches
    print(f"Final dimensions: W = {W / IN:.3f} inches, D = {D / IN:.3f} inches, H = {H / IN:.3f} inches")