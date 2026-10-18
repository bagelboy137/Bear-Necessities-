# /// script
# requires-python = ">=3.11"
# dependencies = ["build123d>=0.13,<0.14"]
# ///
"""Build the frame's two rails: 80/20 1010-S profile cut to 18 in and 22 in.

    uv run --script "Fusion CAD Agent/ots/1010-S/build_rail.py"

Writes BN-rail-1010S-18in.step and BN-rail-1010S-22in.step beside this file,
in real millimetres, and refuses to write anything that misses 80/20's
published section figures. The cut list's two lengths are the only ones built:
it is a hard invariant of the product (01-frame-cut-list-and-bom.md).

What is published and what is assumed - see README.md here for the sources:
  published  SIZE, BORE_D, SLOT_OPEN, SLOT_DEPTH callouts; AREA; IX
  assumed    LIP_T and CAV_W (typical 10-series values) and 45-degree cavity
             walls parallel to the diagonal webs
  solved     the depth where the 45-degree wall starts, so the area equals
             80/20's figure exactly. IX is then an independent check.
"""

import math
import pathlib
import sys

from build123d import Circle, IN, Polygon, Rectangle, Rot, export_step, extrude, import_step

HERE = pathlib.Path(__file__).resolve().parent

# --- 80/20 1010-S, inches ---------------------------------------------------
SIZE = 1.000        # published: 1.00 x 1.00 in
BORE_D = 0.205      # published: dia .205 THRU
SLOT_OPEN = 0.256   # published: .256 TYP
SLOT_DEPTH = 0.323  # published callout .323 TYP, read as face to cavity floor
LIP_T = 0.087       # ASSUMED: typical 10-series lip thickness
CAV_W = 0.584       # ASSUMED: typical 10-series cavity width under the lips
AREA_PUB = 0.437    # published cross-section, in^2 - fitted exactly
IX_PUB = 0.0463     # published Ix = Iy, in^4 - checked, not fitted
IX_TOL = 0.03       # how far the unfitted Ix may drift from 80/20's figure

CUT_LENGTHS = (18.0, 22.0)  # in - the frame's only two cut lengths


def solve_cavity():
    """Depth where the 45-degree wall starts, so the section area is AREA_PUB.

    With 45-degree walls, one slot's area is K - u^2, where u is the depth of
    the sloped part and K the area the slot would have with straight walls.
    """
    half = SIZE / 2
    per_slot = (SIZE ** 2 - math.pi * (BORE_D / 2) ** 2 - AREA_PUB) / 4
    k = SLOT_OPEN * LIP_T + CAV_W * (SLOT_DEPTH - LIP_T)
    u = math.sqrt(k - per_slot)
    d1 = SLOT_DEPTH - u
    web = math.sqrt(2) * (half - CAV_W / 2 - d1)
    if not 0 < u < SLOT_DEPTH - LIP_T or web <= 0:
        sys.exit("cavity solve failed: u=%.4f web=%.4f in" % (u, web))
    return d1, CAV_W / 2 - u, web


def profile():
    """The 1010-S cross-section as a face centred on the origin, in mm."""
    half = SIZE / 2
    d1, floor_hw, _ = solve_cavity()
    o, cw, e = SLOT_OPEN / 2, CAV_W / 2, 0.02
    slot = [(-o, half + e), (o, half + e), (o, half - LIP_T), (cw, half - LIP_T),
            (cw, half - d1), (floor_hw, half - SLOT_DEPTH),
            (-floor_hw, half - SLOT_DEPTH), (-cw, half - d1),
            (-cw, half - LIP_T), (-o, half - LIP_T)]
    face = Rectangle(SIZE * IN, SIZE * IN) - Circle(BORE_D / 2 * IN)
    for angle in (0, 90, 180, 270):
        face -= Rot(0, 0, angle) * Polygon(*[(x * IN, y * IN) for x, y in slot],
                                           align=None)
    return face


def second_moment_x(face):
    """Ix of a planar face about its centroid, mm^4."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face.faces()[0].wrapped, props)
    return props.MatrixOfInertia().Value(1, 1)


def main():
    face = profile()
    area = face.area / IN ** 2
    ix = second_moment_x(face) / IN ** 4
    _, _, web = solve_cavity()
    print("section: area %.4f in^2 (80/20: %.3f), Ix %.4f in^4 (80/20: %.4f, %+.1f%%), "
          "diagonal web %.3f in" % (area, AREA_PUB, ix, IX_PUB, 100 * (ix / IX_PUB - 1), web))
    if abs(area - AREA_PUB) > 1e-4:
        sys.exit("area misses 80/20's figure - nothing written")
    if abs(ix / IX_PUB - 1) > IX_TOL:
        sys.exit("Ix is more than %d%% from 80/20's figure - nothing written"
                 % (100 * IX_TOL))

    for length in CUT_LENGTHS:
        rail = extrude(face, amount=length * IN)
        path = HERE / ("BN-rail-1010S-%din.step" % length)
        export_step(rail, str(path))
        # Measure the file that was written, not the object in memory.
        back = import_step(str(path))
        bb = back.bounding_box()
        got = sorted((bb.size.X / IN, bb.size.Y / IN, bb.size.Z / IN))
        want = [SIZE, SIZE, length]
        if any(abs(g - w) > 1e-4 for g, w in zip(got, want)) or len(back.solids()) != 1:
            sys.exit("%s reads back as %s in, %d solids" % (path.name, got, len(back.solids())))
        print("wrote %s: %.4f x %.4f x %.4f in, %.4f in^3"
              % (path.name, got[0], got[1], got[2], back.volume / IN ** 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
