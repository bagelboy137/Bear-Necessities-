#!/usr/bin/env python3
"""Validate the C-02-U universal L-track floor bracket against its spec."""
import math, sys
import cadquery as cq

L, W, T, R = 6.000, 2.000, 0.250, 0.375
D_MOUNT, N_MOUNT = 0.281, 3
D_PIN = 0.266

area = L * W - 4 * (R * R - math.pi * R * R / 4)
holes = N_MOUNT * math.pi * (D_MOUNT / 2) ** 2 + math.pi * (D_PIN / 2) ** 2
EXPECTED_VOL = (area - holes) * T


def main():
    errs = []
    try:
        s = cq.importers.importStep(sys.argv[1]).val()
    except Exception as e:
        print(f"VALIDATION FAILED:\n1. STEP will not open: {e}", file=sys.stderr)
        return 1
    bb = s.BoundingBox()
    for axis, got, want in zip("XYZ", (bb.xlen, bb.ylen, bb.zlen), (L, W, T)):
        if abs(got - want) > 0.01:
            errs.append(f"{axis} size is {got:.4f}\", expected {want:.4f}\". Plate is "
                        f"{L}\" x {W}\" x {T}\" thick, laid flat with thickness in Z.")
    vol = s.Volume()
    if abs(vol - EXPECTED_VOL) > 0.02:
        errs.append(
            f"Volume is {vol:.4f} in^3, expected {EXPECTED_VOL:.4f} in^3. Required features: "
            f"{N_MOUNT} mounting holes dia {D_MOUNT}\" on the centreline at x = -2.000, 0.000, "
            f"+2.000; 1 pin hole dia {D_PIN}\" at x = +1.000, y = +0.625; and {R}\" radius on "
            f"all 4 corners. All holes go fully through.")
    try:
        cyl = [f for f in s.Faces() if f.geomType() == "CYLINDER"]
        if len(cyl) < 8:
            errs.append(f"Found {len(cyl)} cylindrical faces, expected 8 "
                        f"(4 holes + 4 filleted corners). A feature is missing.")
    except Exception:
        pass
    if len(s.Solids()) != 1:
        errs.append(f"Result is {len(s.Solids())} solids, expected 1.")

    if errs:
        print("VALIDATION FAILED:", file=sys.stderr)
        for i, e in enumerate(errs, 1):
            print(f"{i}. {e}", file=sys.stderr)
        return 1
    print(f"VALID: {bb.xlen:.3f} x {bb.ylen:.3f} x {bb.zlen:.3f} in, "
          f"volume {vol:.4f} in^3 (target {EXPECTED_VOL:.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
