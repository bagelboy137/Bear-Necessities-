#!/usr/bin/env python3
"""
cq_validate.py — check a CadQuery-produced STEP is the RIGHT solid.

Solid geometry allows far stronger checks than a 2D drawing: exact bounding
box, exact volume, solid count, watertightness. Numeric feedback like
"volume is 480.0, expected 232.0" is the most actionable signal a model can get.

    python cq_validate.py <file.step>
"""
import sys
import cadquery as cq

W, D, H, P = 24.0, 20.0, 18.0, 1.0
# 4 posts + 4 width members + 4 depth members, all P x P cross-section
EXPECTED_VOL = 4 * (H * P * P) + 4 * ((W - 2 * P) * P * P) + 4 * ((D - 2 * P) * P * P)


def main():
    path = sys.argv[1]
    errs = []

    try:
        shape = cq.importers.importStep(path)
    except Exception as e:
        print(f"VALIDATION FAILED:\n1. STEP will not open: {e}", file=sys.stderr)
        return 1

    solid = shape.val()
    bb = solid.BoundingBox()
    got = (bb.xlen, bb.ylen, bb.zlen)

    for axis, g, want in zip("XYZ", got, (W, D, H)):
        if abs(g - want) > 0.02:
            errs.append(
                f"Overall {axis} size is {g:.3f}\", expected {want:.3f}\". The frame's "
                f"OUTSIDE dimensions must be exactly {W} x {D} x {H} inches. Remember the "
                f"{P}\" profile: a member placed at x={W}-{P} ends exactly at {W}.")

    vol = solid.Volume()
    if abs(vol - EXPECTED_VOL) > 0.75:
        if vol > EXPECTED_VOL:
            why = ("Too much material - members are overlapping (double-counted at the "
                   "corners) or too long. Horizontal members must fit BETWEEN the posts: "
                   f"width members are {W - 2*P}\" long starting at x={P}, depth members "
                   f"are {D - 2*P}\" long starting at y={P}.")
        else:
            why = ("Too little material - you are missing members. There must be 12: "
                   "4 vertical posts, 4 width members (top and bottom, both sides), "
                   "4 depth members (top and bottom, both sides).")
        errs.append(f"Volume is {vol:.2f} in^3, expected {EXPECTED_VOL:.2f} in^3. {why}")

    try:
        n_solids = len(solid.Solids())
        if n_solids != 1:
            errs.append(
                f"Result is {n_solids} separate solids, expected 1. The 12 members must be "
                f"unioned into a single connected frame - they should touch at the corners.")
    except Exception:
        pass

    try:
        if not solid.isValid():
            errs.append("The solid fails geometric validity checks (self-intersecting or "
                        "malformed). Build each member as a simple box and union them.")
    except Exception:
        pass

    if errs:
        print("VALIDATION FAILED:", file=sys.stderr)
        for i, e in enumerate(errs, 1):
            print(f"{i}. {e}", file=sys.stderr)
        return 1

    print(f"VALID: bbox {got[0]:.3f} x {got[1]:.3f} x {got[2]:.3f} in, "
          f"volume {vol:.2f} in^3, {len(solid.Solids())} solid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
