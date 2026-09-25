#!/usr/bin/env python3
"""
validate_drawing.py — check that a DXF is actually CORRECT, not merely valid.

Runs inside the CAD venv. Prints human-readable failures on stderr and exits
non-zero, so cad_loop.py can feed them straight back to the model. Every
message names the specific defect and the expected value.

    python validate_drawing.py <file.dxf>
"""
import sys, math, ezdxf

W, D, H = 24.0, 20.0, 18.0     # outside dims, inches
PROFILE = 1.0                   # 1010 series, 1" square
TOL = 0.35                      # generous — we are checking intent, not precision

# Cut lengths for a butt-jointed cube whose OUTSIDE dims are W x D x H:
# posts run full height; the horizontal members fit between them.
EXPECT_CUTS = {
    "post":  (4, H),                    # 4 verticals, full 18"
    "width": (4, W - 2 * PROFILE),      # 4 @ 22"
    "depth": (4, D - 2 * PROFILE),      # 4 @ 18"
}


def bbox(e):
    try:
        if e.dxftype() == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points()]
        elif e.dxftype() == "LINE":
            pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
        elif e.dxftype() == "CIRCLE":
            c, r = e.dxf.center, e.dxf.radius
            pts = [(c.x - r, c.y - r), (c.x + r, c.y + r)]
        else:
            return None
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))
    except Exception:
        return None


def overlaps(a, b):
    return not (a[2] <= b[0] + 0.01 or b[2] <= a[0] + 0.01 or
                a[3] <= b[1] + 0.01 or b[3] <= a[1] + 0.01)


def main():
    path = sys.argv[1]
    errs = []
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    ents = list(msp)

    geom = [e for e in ents if e.dxftype() in ("LWPOLYLINE", "LINE", "CIRCLE")]
    texts = [e for e in ents if e.dxftype() in ("TEXT", "MTEXT")]

    def txt(e):
        try:
            return (e.dxf.text if e.dxftype() == "TEXT" else e.text) or ""
        except Exception:
            return ""

    alltext = " | ".join(txt(t) for t in texts).lower()

    if len(geom) < 3:
        errs.append(f"Only {len(geom)} geometry entities. Three orthographic views need "
                    f"far more - draw the frame MEMBERS, not just an outline rectangle.")

    # --- the three views must exist at distinct, non-overlapping locations ----
    boxes = [b for b in (bbox(e) for e in geom) if b]
    clusters = []
    for b in boxes:
        placed = False
        for c in clusters:
            if overlaps(b, c) or (abs(b[0] - c[0]) < 3 and abs(b[1] - c[1]) < 3):
                c[0] = min(c[0], b[0]); c[1] = min(c[1], b[1])
                c[2] = max(c[2], b[2]); c[3] = max(c[3], b[3])
                placed = True
                break
        if not placed:
            clusters.append(list(b))

    if len(clusters) < 3:
        errs.append(
            f"Found only {len(clusters)} separate view region(s); need 3 that DO NOT "
            f"OVERLAP. Every view is being drawn at the same origin. Offset each view: "
            f"e.g. front at (0,0), top at (0, {H+6}), right at ({W+8}, 0). Add the offset "
            f"to EVERY point of that view.")
    else:
        sizes = sorted(((round(c[2]-c[0],1), round(c[3]-c[1],1)) for c in clusters),
                       key=lambda s: -s[0]*s[1])
        want = {(W, H), (W, D), (D, H)}
        got_ok = 0
        for wv, hv in sizes[:3]:
            if any(abs(wv-a) < TOL and abs(hv-b) < TOL for a, b in want):
                got_ok += 1
        if got_ok < 3:
            errs.append(
                f"View sizes are wrong. Got {sizes[:3]}. Expected exactly these three "
                f"(width x height, inches): front {W}x{H}, top {W}x{D}, right {D}x{H}. "
                f"NOTE the right view uses DEPTH ({D}) for its width, not WIDTH ({W}).")

    # --- labels ---------------------------------------------------------------
    for label in ("front", "top", "right"):
        if label not in alltext:
            errs.append(f"Missing a text label containing '{label}'.")

    # --- cut list -------------------------------------------------------------
    import re
    nums = [float(n) for n in re.findall(r"(\d+(?:\.\d+)?)", alltext)]
    for name, (qty, length) in EXPECT_CUTS.items():
        if not any(abs(n - length) < 0.26 for n in nums):
            errs.append(
                f"Cut list is missing the {name} member length {length}\". "
                f"For a {W}x{D}x{H}\" OUTSIDE cube from {PROFILE}\" square extrusion: "
                f"4 posts @ {EXPECT_CUTS['post'][1]}\", "
                f"4 width members @ {EXPECT_CUTS['width'][1]}\", "
                f"4 depth members @ {EXPECT_CUTS['depth'][1]}\". "
                f"Horizontal members fit BETWEEN the posts, so subtract 2 x {PROFILE}\".")
            break

    if not any(abs(n - 4) < 0.01 for n in nums):
        errs.append("Cut list quantities look wrong - there should be 4 of each of the "
                    "three member types (12 members total), stated as '4x'.")

    # --- text must not collide (the title kept landing on the cut list) ------
    def text_box(e):
        try:
            h = float(e.dxf.height) if e.dxftype() == "TEXT" else float(e.dxf.char_height)
            ins = e.dxf.insert if e.dxftype() == "TEXT" else e.dxf.insert
            t = txt(e)
            return (ins.x, ins.y, ins.x + 0.62 * h * max(len(t), 1), ins.y + h)
        except Exception:
            return None

    tboxes = [(txt(e), b) for e in texts if (b := text_box(e))]
    collisions = []
    for i in range(len(tboxes)):
        for j in range(i + 1, len(tboxes)):
            (t1, b1), (t2, b2) = tboxes[i], tboxes[j]
            if overlaps(b1, b2):
                collisions.append((t1[:34], t2[:34]))
    if collisions:
        a, b = collisions[0]
        errs.append(
            f"Text overlaps text: {a!r} collides with {b!r} ({len(collisions)} collisions). "
            f"Move the TITLE well clear of everything else - put it ABOVE the topmost "
            f"view, and place the cut list in its own empty column to the RIGHT of all "
            f"views. Account for text WIDTH (~0.6 x height x number of characters), not "
            f"just height.")

    # --- the views must show the actual frame, not empty outlines ------------
    if len(geom) < 24:
        errs.append(
            f"Only {len(geom)} geometry entities - the views are empty outline boxes. "
            f"DRAW THE 12 EXTRUSION MEMBERS. In the front view show the 2 vertical posts "
            f"and 2 horizontal members as {PROFILE}\" wide rectangles inset at the frame "
            f"edges; do the same for top and right. Expect roughly 8-12 rectangles PER "
            f"view, not one.")

    if errs:
        print("VALIDATION FAILED:", file=sys.stderr)
        for i, e in enumerate(errs, 1):
            print(f"{i}. {e}", file=sys.stderr)
        return 1

    print(f"VALID: {len(geom)} geometry entities, {len(clusters)} separate views, "
          f"{len(texts)} text items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
