#!/usr/bin/env python3
"""Validate the C-01 anchor plate STEP against its spec, numerically."""
import math, sys
import cadquery as cq

L, W, T = 4.000, 1.500, 0.250
R = 0.250                       # corner radius
D_MOUNT, N_MOUNT = 0.281, 2
D_PIN = 0.266

# Analytical target volume: plate - corner radii - holes
area = L * W - 4 * (R * R - math.pi * R * R / 4)
holes = N_MOUNT * math.pi * (D_MOUNT / 2) ** 2 + math.pi * (D_PIN / 2) ** 2
EXPECTED_VOL = area * T - holes * T


def main():
    errs = []
    try:
        shape = cq.importers.importStep(sys.argv[1])
    except Exception as e:
        print(f"VALIDATION FAILED:\n1. STEP will not open: {e}", file=sys.stderr)
        return 1
    s = shape.val()
    bb = s.BoundingBox()

    for axis, got, want in zip("XYZ", (bb.xlen, bb.ylen, bb.zlen), (L, W, T)):
        if abs(got - want) > 0.01:
            errs.append(f"{axis} size is {got:.4f}\", expected {want:.4f}\". The plate is "
                        f"{L}\" long x {W}\" wide x {T}\" thick, laid flat (thickness in Z).")

    vol = s.Volume()
    if abs(vol - EXPECTED_VOL) > 0.02:
        errs.append(
            f"Volume is {vol:.4f} in^3, expected {EXPECTED_VOL:.4f} in^3. "
            f"That means holes or corner radii are missing or wrong. Required: "
            f"{N_MOUNT} mounting holes dia {D_MOUNT}\" spaced 2.000\" apart symmetric about "
            f"the centre, 1 pin hole dia {D_PIN}\" at 1.500\" from centre along the length, "
            f"and {R}\" radius on all 4 corners. All holes go fully through.")

    # Count cylindrical faces = holes
    try:
        cyl = [f for f in s.Faces() if f.geomType() == "CYLINDER"]
        # 4 corner fillets are also cylinders; expect 3 holes + 4 corners = 7
        if len(cyl) < 7:
            errs.append(f"Found {len(cyl)} cylindrical faces; expected 7 "
                        f"(3 through-holes + 4 filleted corners). Some feature is missing.")
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
