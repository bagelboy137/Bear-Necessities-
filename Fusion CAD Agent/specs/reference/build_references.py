#!/usr/bin/env python3
"""Rebuild every reference solid from its hand-written CadQuery source.

A reference solid is the ground truth a spec's `checks` are measured against.
Without this script they would be unreproducible binaries: correct today,
unverifiable tomorrow, and impossible to adjust when a part changes.

    "Fusion CAD Agent/.venv-cq/bin/python" specs/reference/build_references.py

Writes, for every part:
  <id>-authored.step   the shape as authored, numbered in the spec's units
  <id>.step  <id>.stl  the millimetre delivery, which is what gets measured

The two-file split is not tidiness. A STEP written by CadQuery always declares
`SI_UNIT(.MILLI.,.METRE.)`, so the authored file's 4.0 means 4mm to every
reader. Only the converted file is physically correct. See ../../bncad/README.md.
"""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

import cadquery as cq                       # noqa: E402
from cadquery import exporters              # noqa: E402

from bncad import spec as S                 # noqa: E402
from bncad.spec import PartSpec             # noqa: E402


def plate(length, width, thickness, radius, holes):
    """A flat plate with rounded vertical corners and through holes."""
    solid = (cq.Workplane("XY")
             .box(length, width, thickness, centered=(True, True, False))
             .edges("|Z").fillet(radius))
    for x, y, diameter in holes:
        solid = solid.faces(">Z").workplane().pushPoints([(x, y)]).hole(diameter)
    return solid


def p01_plate():
    return plate(4.0, 1.5, 0.25, 0.25,
                 [(-1.0, 0.0, 0.281), (1.0, 0.0, 0.281)])


def c01_anchor_plate():
    return plate(4.0, 1.5, 0.25, 0.25,
                 [(-1.0, 0.0, 0.281), (1.0, 0.0, 0.281), (1.5, 0.0, 0.266)])


def c02u_floor_bracket():
    return plate(6.0, 2.0, 0.25, 0.375,
                 [(-2.0, 0.0, 0.281), (0.0, 0.0, 0.281), (2.0, 0.0, 0.281),
                  (1.0, 0.625, 0.266)])


def p05_spacer():
    # A disc, not a filleted square. circle() takes a RADIUS, hole() a DIAMETER.
    return (cq.Workplane("XY").circle(1.5 / 2).extrude(0.125)
            .faces(">Z").workplane().hole(0.5))


def p06_l_bracket():
    """Two legs sharing the origin corner, holes on two different axes.

    Holes are cut as positioned cylinders rather than selected faces: on an L
    the target face is ambiguous, and `.faces("|Y")` raises "Selected faces must
    be co-planar" - the failure that took three prompt revisions to teach around.
    """
    horizontal = cq.Workplane("XY").box(3.0, 1.5, 0.25, centered=False)
    vertical = cq.Workplane("XY").box(0.25, 1.5, 2.0, centered=False)
    solid = horizontal.union(vertical)
    solid = solid.cut(cq.Workplane("XY").circle(0.281 / 2).extrude(0.25)
                      .translate((2.0, 0.75, 0)))
    solid = solid.cut(cq.Workplane("YZ").circle(0.281 / 2).extrude(0.25)
                      .translate((0, 0.75, 1.5)))
    return solid


def bn_frame_base():
    """Twelve members, outside dimensions exactly 24 x 20 x 18.

    Two cut lengths only - 18in x 8 and 22in x 4 - which is the project's
    standing rule and the cheapest orderable cut list. Preserve it.
    """
    width, depth, height, profile = 24.0, 20.0, 18.0, 1.0
    members = []
    for x in (0, width - profile):                       # 4 corner posts
        for y in (0, depth - profile):
            members.append((profile, profile, height, x, y, 0))
    for y in (0, depth - profile):                       # 4 width rails
        for z in (0, height - profile):
            members.append((width - 2 * profile, profile, profile, profile, y, z))
    for x in (0, width - profile):                       # 4 depth rails
        for z in (0, height - profile):
            members.append((profile, depth - 2 * profile, profile, x, profile, z))

    solid = None
    for lx, ly, lz, x, y, z in members:
        member = cq.Workplane("XY").box(lx, ly, lz, centered=False).translate((x, y, z))
        solid = member if solid is None else solid.union(member)
    return solid


PARTS = {
    "P05-spacer": p05_spacer,
    "P01-plate": p01_plate,
    "C-01-anchor-plate": c01_anchor_plate,
    "P06-l-bracket": p06_l_bracket,
    "C-02-U-floor-bracket": c02u_floor_bracket,
    "BN-FRAME-base": bn_frame_base,
}


def main():
    specs = {p.stem: PartSpec.load(p)
             for p in sorted((ROOT / "specs" / "parts").glob("*.json"))}
    missing = set(specs) - set(PARTS)
    if missing:
        print("no builder for spec(s): %s" % ", ".join(sorted(missing)))

    failures = 0
    for part_id, builder in PARTS.items():
        part = specs.get(part_id)
        if part is None:
            print("%-24s SKIP (no spec)" % part_id)
            continue

        authored = HERE / ("%s-authored.step" % part_id)
        delivery = HERE / ("%s.step" % part_id)
        mesh = HERE / ("%s.stl" % part_id)

        exporters.export(builder(), str(authored))
        S.to_delivery(authored, delivery, mesh, part.scale)
        measured = S.measure(delivery, mesh, scale=part.scale)
        errors = part.check(measured)

        status = "OK  " if not errors else "FAIL"
        print("%-24s %s %s" % (part_id, status, part.report(measured)))
        for i, error in enumerate(errors, 1):
            print("      %d. %s" % (i, error))
        failures += bool(errors)

    print("\n%d of %d reference solids match their spec."
          % (len(PARTS) - failures, len(PARTS)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
