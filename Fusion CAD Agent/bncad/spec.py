#!/usr/bin/env python3
"""Part specs that drive generation AND validation from one JSON file.

The old bridge needed a hand-written `cq_validate_<part>.py` for every part.
That is the reason only three parts ever got validated: adding a part meant
writing a program. Here a spec declares what the solid must measure, and one
engine checks any part against it.

Every failure message must carry the measured number, the wanted number and the
delta. That is not politeness - it is the difference between a repair loop that
converges and one that resamples. A real 30-cycle sweep in this project died
because a check said only "length/type invalid" and the model, having no idea it
was 27 characters over, guessed and came back longer.

Measurement runs against the exported STEP, not the in-memory model, so what is
checked is what a supplier receives.
"""

import json
import math
import os
import pathlib
import struct

# Imported lazily so `python -m bncad models` works under an interpreter that
# has no cadquery.
_CQ = None


def _cq():
    global _CQ
    if _CQ is None:
        import cadquery
        _CQ = cadquery
    return _CQ


class SpecError(ValueError):
    pass


# A STEP file written by CadQuery ALWAYS declares SI_UNIT(.MILLI.,.METRE.) -
# there is no exporter option for it, and setting OCCT's "write.step.unit" does
# nothing. So a part authored with the numbers 4.0 x 1.5 x 0.25 inches produces
# a file that every reader correctly interprets as 4.0 x 1.5 x 0.25 MILLIMETRES.
# Fusion imported exactly that and reported 0.157in - the part 25.4x too small.
# A supplier's CAM would have done the same, silently.
#
# So bncad converts to millimetres before anything is measured or delivered:
# there is one STEP, it is physically correct, and what the checks validate is
# the file that actually leaves the building.
MM_PER_UNIT = {"in": 25.4, "mm": 1.0, "cm": 10.0, "m": 1000.0}
UNIT_NAMES = {"in": "inches", "mm": "millimetres", "cm": "centimetres",
              "m": "metres"}

# Every key `check()` understands. A spec carrying anything else is refused at
# load, because an ignored key is an ignored GATE - see PartSpec.__init__.
KNOWN_CHECKS = {
    "bbox", "bbox_tol", "size_max", "size_min",
    "volume", "volume_tol", "solids", "valid", "watertight",
    "faces", "center", "center_tol", "holes", "holes_exact",
}
KNOWN_HOLE_KEYS = {"d", "count", "tol", "at", "at_tol", "through", "depth"}


def to_delivery(src_step, dst_step, dst_stl, factor):
    """Scale an authored solid into a millimetre-correct STEP and STL."""
    cq = _cq()
    solid = cq.importers.importStep(str(src_step)).val()
    if factor != 1.0:
        solid = solid.scale(factor)
    wp = cq.Workplane(obj=solid)
    from cadquery import exporters
    exporters.export(wp, str(dst_step))
    if dst_stl:
        exporters.export(wp, str(dst_stl))


def mesh_stats(stl_path):
    """Watertightness of an exported binary STL, from the bytes on disk.

    The STEP passing `isValid()` says the *solid* is sound. It says nothing
    about the tessellation, and the STL is what a printer or a supplier
    actually receives. This project already learned once that a deliverable
    needs its own gate rather than inheriting confidence from the model it came
    from.

    Watertight means every edge is shared by exactly two triangles. Vertices are
    quantised before comparison so float noise in the exporter does not read as
    a crack.
    """
    data = pathlib.Path(stl_path).read_bytes()
    if len(data) < 84:
        return {"error": "STL is too short to contain a header"}
    count = struct.unpack("<I", data[80:84])[0]
    if len(data) < 84 + count * 50:
        return {"error": "STL claims %d triangles but the file is short" % count}

    quant = 1e-6
    edges = {}
    degenerate = 0
    for i in range(count):
        off = 84 + i * 50
        vals = struct.unpack("<12f", data[off:off + 48])
        verts = [tuple(int(round(c / quant)) for c in vals[3:6]),
                 tuple(int(round(c / quant)) for c in vals[6:9]),
                 tuple(int(round(c / quant)) for c in vals[9:12])]
        if len(set(verts)) < 3:
            degenerate += 1
            continue
        for a, b in ((verts[0], verts[1]), (verts[1], verts[2]), (verts[2], verts[0])):
            edges[(a, b) if a < b else (b, a)] = edges.get((a, b) if a < b else (b, a), 0) + 1

    open_edges = sum(1 for n in edges.values() if n != 2)
    return {"triangles": count, "degenerate": degenerate,
            "open_edges": open_edges, "watertight": open_edges == 0 and degenerate == 0}


def measure(step_path, stl_path=None, scale=1.0):
    """Every geometric property the checks can reason about.

    `stl_path` is optional: pass it to also gate the mesh deliverable.
    `scale` is millimetres per spec unit - the file is in millimetres, the
    numbers come back in the spec's units, so checks compare like with like.
    """
    cq = _cq()
    shape = cq.importers.importStep(str(step_path))
    solid = shape.val()
    bb = solid.BoundingBox()

    try:
        valid = bool(solid.isValid())
    except Exception:
        valid = False
    try:
        solids = len(solid.Solids())
    except Exception:
        solids = 0

    s = float(scale)
    out = {
        "bbox": [bb.xlen / s, bb.ylen / s, bb.zlen / s],
        "bbox_min": [bb.xmin / s, bb.ymin / s, bb.zmin / s],
        "volume": solid.Volume() / (s ** 3),
        "area": solid.Area() / (s ** 2),
        "solids": solids,
        "valid": valid,
        "faces": len(solid.Faces()),
        "edges": len(solid.Edges()),
        "center": [solid.Center().x / s, solid.Center().y / s,
                   solid.Center().z / s],
        "holes": _holes(solid, s),
        "scale_mm_per_unit": s,
    }
    if stl_path and pathlib.Path(stl_path).exists():
        out["mesh"] = mesh_stats(stl_path)
    return out


def _holes(solid, scale=1.0):
    """Through/blind holes as [{d, depth, axis, at}], largest first.

    A hole and a corner fillet are both cylindrical faces. What separates them
    is which way the surface faces: an internal cylinder comes back REVERSED,
    an external one FORWARD. Verified against a plate carrying both - the two
    0.281 holes and one 0.266 hole were REVERSED, the four R0.25 corner fillets
    FORWARD. Sweep angle agrees (360 vs 90) and is kept as a second signal so a
    half-slot does not get counted as a hole.
    """
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_SurfaceType
    from OCP.TopAbs import TopAbs_Orientation

    found = []
    for face in solid.Faces():
        ad = BRepAdaptor_Surface(face.wrapped)
        if ad.GetType() != GeomAbs_SurfaceType.GeomAbs_Cylinder:
            continue
        if face.wrapped.Orientation() != TopAbs_Orientation.TopAbs_REVERSED:
            continue  # external cylinder: a fillet or a boss, not a hole
        sweep = math.degrees(ad.LastUParameter() - ad.FirstUParameter())
        if sweep < 300:
            continue  # partial wrap: a slot end or a cutout, not a round hole
        cyl = ad.Cylinder()
        ax = cyl.Axis().Direction()
        loc = cyl.Location()
        found.append({
            "d": round(cyl.Radius() * 2 / scale, 5),
            "depth": round((ad.LastVParameter() - ad.FirstVParameter()) / scale, 5),
            "axis": [round(ax.X(), 4), round(ax.Y(), 4), round(ax.Z(), 4)],
            "at": [round(loc.X() / scale, 4), round(loc.Y() / scale, 4),
                   round(loc.Z() / scale, 4)],
        })
    return sorted(found, key=lambda h: -h["d"])


def _in_plane(hole):
    """A hole's position projected onto the plane its axis is normal to.

    A bolt pattern is a 2D thing. Comparing all three coordinates would trip on
    which end of the hole OCC happened to report, so drop the axis component and
    compare where the hole actually sits on the face.
    """
    axis = [abs(a) for a in hole["axis"]]
    dominant = axis.index(max(axis))
    return [v for i, v in enumerate(hole["at"]) if i != dominant]


def _plane_distance(hole, want):
    got = _in_plane(hole)
    if len(got) != len(want):
        return float("inf")
    return max(abs(a - b) for a, b in zip(got, want))


class PartSpec:
    """A part brief plus the numbers its solid must hit."""

    def __init__(self, data, source=None):
        self.source = source
        self.data = data
        for required in ("id", "name", "description"):
            if not data.get(required):
                raise SpecError("spec %s is missing required field %r"
                                % (source or "<inline>", required))
        self.id = data["id"]
        self.name = data["name"]
        self.units = data.get("units", "in")
        self.description = data["description"]
        self.constants = data.get("constants", {})
        self.checks = data.get("checks", {})
        self.notes = data.get("notes", "")
        self._last_bbox = None
        if not self.checks:
            raise SpecError(
                "spec %s declares no checks. A part with no checks cannot fail, "
                "so the loop would accept the first thing that runs." % self.id)

        # An unrecognised key used to be ignored in silence, which meant a typo
        # DELETED a gate rather than failing. A spec written with "volumne" and
        # "hole" passed a solid of 99 in^3 with no holes at all, reporting zero
        # errors. Refuse the spec instead: a misspelled gate is indistinguishable
        # from an absent one, and the cost lands on a supplier.
        unknown = sorted(set(self.checks) - KNOWN_CHECKS)
        if unknown:
            raise SpecError(
                "spec %s has unknown check(s): %s. Known checks: %s. A "
                "misspelled key would silently disable that check."
                % (self.id, ", ".join(unknown), ", ".join(sorted(KNOWN_CHECKS))))
        for entry in self.checks.get("holes", []):
            extra = sorted(set(entry) - KNOWN_HOLE_KEYS)
            if extra:
                raise SpecError(
                    "spec %s has unknown key(s) in a `holes` entry: %s. Known: %s."
                    % (self.id, ", ".join(extra), ", ".join(sorted(KNOWN_HOLE_KEYS))))
            if "d" not in entry:
                raise SpecError(
                    "spec %s has a `holes` entry with no diameter (`d`)." % self.id)

    @property
    def scale(self):
        """Millimetres per spec unit. A STEP on disk is always millimetres."""
        try:
            return MM_PER_UNIT[self.units]
        except KeyError:
            raise SpecError("spec %s uses unknown units %r. Known: %s"
                            % (self.id, self.units,
                               ", ".join(sorted(MM_PER_UNIT)))) from None

    @classmethod
    def load(cls, path):
        path = pathlib.Path(path)
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            raise SpecError("%s is not valid JSON: %s" % (path, e)) from None
        return cls(data, source=str(path))

    def brief(self):
        """The part of the spec the model is shown."""
        lines = ["PART %s - %s" % (self.id, self.name),
                 "UNITS: every number below is in %s. Do not convert."
                 % UNIT_NAMES.get(self.units, self.units),
                 "", self.description.strip()]
        if self.constants:
            lines += ["", "NAMED DIMENSIONS (use these exact values):"]
            lines += ["  %s = %s" % (k, v) for k, v in self.constants.items()]
        want = self.checks
        lines += ["", "THE FINISHED SOLID MUST MEASURE:"]
        if "bbox" in want:
            lines.append("  overall size exactly %s x %s x %s %s"
                         % (want["bbox"][0], want["bbox"][1], want["bbox"][2], self.units))
        if "size_max" in want:
            lines.append("  must fit inside %s x %s x %s %s"
                         % tuple(list(want["size_max"]) + [self.units]))
        if "volume" in want:
            lines.append("  volume %.4f %s^3" % (want["volume"], self.units))
        if "solids" in want:
            lines.append("  exactly %d connected solid(s) - union everything that touches"
                         % want["solids"])
        for h in want.get("holes", []):
            lines.append("  %d hole(s) of diameter %s %s"
                         % (h.get("count", 1), h["d"], self.units))
        if self.notes:
            lines += ["", "NOTES:", self.notes.strip()]
        return "\n".join(lines)

    # -- checking ---------------------------------------------------------

    def check(self, m):
        """Return a list of actionable failure strings. Empty list means pass."""
        errs = []
        want = self.checks
        u = self.units
        # Kept for the `through` check, which needs to know how thick the part
        # is along each hole's axis.
        self._last_bbox = m.get("bbox")

        if want.get("valid", True) and not m["valid"]:
            # Carries counts so this message obeys the same rule as the rest:
            # never hand the model a verdict with nothing measurable in it.
            errs.append(
                "The solid fails OCC validity checks: %d solid(s), %d face(s), "
                "%d edge(s), volume %.4f %s^3. It is self-intersecting or "
                "malformed. Build each feature as a simple primitive and union "
                "them; avoid filleting an edge that a later cut removes."
                % (m.get("solids", 0), m.get("faces", 0), m.get("edges", 0),
                   m.get("volume", 0.0), u))

        if "solids" in want and m["solids"] != want["solids"]:
            got, exp = m["solids"], want["solids"]
            if got > exp:
                why = ("Parts are floating apart. Members that should join must "
                       "overlap or touch exactly, and every piece must be unioned "
                       "into the result.")
            else:
                why = "Pieces are missing, or you unioned away geometry you needed."
            errs.append("Result is %d separate solid(s), expected %d. %s"
                        % (got, exp, why))

        if "bbox" in want:
            tol = want.get("bbox_tol", 0.02)
            for axis, got, exp in zip("XYZ", m["bbox"], want["bbox"]):
                d = got - exp
                if abs(d) > tol:
                    errs.append(
                        "Overall %s size is %.4f%s, expected %.4f%s "
                        "(%+.4f%s off, tolerance +/-%s). Change the %s dimension "
                        "by %+.4f." % (axis, got, u, exp, u, d, u, tol, axis, -d))

        # Named size_max/size_min, NOT bbox_max/bbox_min. measure() already
        # returns a key called "bbox_min", and it means the minimum CORNER
        # COORDINATE, not a minimum size. Sharing the name invites someone to
        # paste a measured [-2.0, -0.75, 0.0] into a spec and get a check that
        # silently passes anything.
        if "size_max" in want:
            for axis, got, cap in zip("XYZ", m["bbox"], want["size_max"]):
                if got > cap + 1e-9:
                    errs.append(
                        "Overall %s size is %.4f%s but must not exceed %.4f%s. "
                        "Reduce %s by at least %.4f." % (axis, got, u, cap, u, axis, got - cap))

        if "size_min" in want:
            for axis, got, floor in zip("XYZ", m["bbox"], want["size_min"]):
                if got < floor - 1e-9:
                    errs.append(
                        "Overall %s size is %.4f%s but must be at least %.4f%s. "
                        "Increase %s by at least %.4f." % (axis, got, u, floor, u, axis, floor - got))

        if "volume" in want:
            exp = float(want["volume"])
            tol = want.get("volume_tol", max(0.01 * exp, 0.01))
            got = m["volume"]
            if abs(got - exp) > tol:
                why = ("Too much material: features overlap and are double-counted, "
                       "or a member is longer than its cut length."
                       if got > exp else
                       "Too little material: pieces are missing, or a cut removed "
                       "more than intended.")
                errs.append(
                    "Volume is %.4f %s^3, expected %.4f %s^3 (%+.4f off, tolerance "
                    "+/-%.4f). %s" % (got, u, exp, u, got - exp, tol, why))

        errs += self._check_holes(m)
        errs += self._check_mesh(m)

        if "faces" in want and m["faces"] != want["faces"]:
            errs.append("Solid has %d faces, expected %d."
                        % (m["faces"], want["faces"]))

        cen = want.get("center")
        if cen:
            tol = want.get("center_tol", 0.02)
            for axis, got, exp in zip("XYZ", m["center"], cen):
                if abs(got - exp) > tol:
                    errs.append(
                        "Centre of mass %s is %.4f%s, expected %.4f%s (%+.4f off). "
                        "The part is not positioned or is not symmetric as specified."
                        % (axis, got, u, exp, u, got - exp))
        return errs

    def _check_mesh(self, m):
        """Gate the STL deliverable, when one was measured.

        Defaults to on: a mesh that was exported and is not watertight is a
        defect whether or not the spec thought to ask.
        """
        mesh = m.get("mesh")
        if not mesh or not self.checks.get("watertight", True):
            return []
        if mesh.get("error"):
            return ["The exported STL is unreadable: %s" % mesh["error"]]
        errs = []
        if mesh.get("degenerate"):
            errs.append(
                "The exported STL has %d degenerate triangle(s) - facets with two "
                "identical corners and no area. The solid has a zero-thickness or "
                "self-touching feature." % mesh["degenerate"])
        if mesh.get("open_edges"):
            errs.append(
                "The exported STL is not watertight: %d edge(s) are not shared by "
                "exactly two triangles, out of %d triangles. The solid has a crack "
                "or a missing face and will not print or quote."
                % (mesh["open_edges"], mesh["triangles"]))
        return errs

    def _check_holes(self, m):
        wanted = self.checks.get("holes")
        if not wanted:
            return []
        errs = []
        u = self.units
        got = list(m["holes"])
        for spec_hole in wanted:
            d = float(spec_hole["d"])
            n = int(spec_hole.get("count", 1))
            tol = float(spec_hole.get("tol", 0.005))
            matched = [h for h in got if abs(h["d"] - d) <= tol]
            if len(matched) != n:
                near = sorted(got, key=lambda h: abs(h["d"] - d))[:3]
                near_txt = (", ".join("%.4f" % h["d"] for h in near)
                            if near else "none at all")
                errs.append(
                    "Found %d hole(s) of diameter %.4f%s (+/-%.4f), expected %d. "
                    "Nearest diameters present: %s. Use .hole(%s) - it takes a "
                    "DIAMETER, not a radius, and drills all the way through."
                    % (len(matched), d, u, tol, n, near_txt, d))
            errs += self._check_hole_placement(spec_hole, matched, d)
            for h in matched:
                got.remove(h)
        if self.checks.get("holes_exact") and got:
            errs.append(
                "There are %d extra hole(s) the spec does not call for: %s. "
                "Remove them." % (len(got), ", ".join("%.4f" % h["d"] for h in got)))
        return errs

    def _check_hole_placement(self, spec_hole, matched, d):
        """Where the holes are, and whether they go through.

        Both were measured and thrown away. Two holes of the right diameter in
        the wrong place change volume by exactly zero, leave the bounding box
        untouched and satisfy `holes_exact` - so a mirrored or mis-spaced bolt
        pattern passed with no errors at all. A blind hole is likewise still an
        internal 360-degree cylinder of the right diameter, and one of them hides
        inside a typical volume tolerance.

        That is the defect a supplier cannot catch and the customer finds on
        install, on a product whose open blocker is a bolt pattern.
        """
        errs = []
        u = self.units

        want_at = spec_hole.get("at")
        if want_at:
            # A single [x, y] is one position; [[x, y], ...] is several.
            positions = want_at if isinstance(want_at[0], (list, tuple)) else [want_at]
            at_tol = float(spec_hole.get("at_tol", 0.01))
            free = list(matched)
            for want in positions:
                hit = None
                for h in free:
                    if _plane_distance(h, want) <= at_tol:
                        hit = h
                        break
                if hit is None:
                    where = ", ".join("%.4f" % v for v in want)
                    found = "; ".join(
                        "(" + ", ".join("%.4f" % v for v in _in_plane(h)) + ")"
                        for h in matched) or "none"
                    errs.append(
                        "No %.4f%s hole at (%s) within +/-%.4f%s. Holes of that "
                        "diameter are at: %s. The diameters are right and the "
                        "positions are not - move them, do not re-drill."
                        % (d, u, where, at_tol, u, found))
                else:
                    free.remove(hit)

        # `through` compares the hole depth to the bounding box along its axis,
        # so it is only meaningful when the material is UNIFORM along that axis -
        # a plate, not an L. On an L-bracket the bbox is the whole part and a
        # perfectly good hole through a 0.25 leg reads as blind. Use an explicit
        # `depth` for parts that are not uniform.
        if spec_hole.get("through"):
            for h in matched:
                axis_len = self._extent_along(h)
                if axis_len is not None and h["depth"] < axis_len - 0.01:
                    errs.append(
                        "A %.4f%s hole is only %.4f%s deep but the material is "
                        "%.4f%s thick along that axis - it is a blind hole, and "
                        "the spec calls for a hole that goes all the way through."
                        % (d, u, h["depth"], u, axis_len, u))

        want_depth = spec_hole.get("depth")
        if want_depth is not None:
            for h in matched:
                if abs(h["depth"] - float(want_depth)) > 0.01:
                    errs.append(
                        "A %.4f%s hole is %.4f%s deep, expected %.4f%s (%+.4f off)."
                        % (d, u, h["depth"], u, float(want_depth), u,
                           h["depth"] - float(want_depth)))
        return errs

    def _extent_along(self, hole):
        """How thick the part is along this hole's axis, from the bounding box."""
        bbox = self._last_bbox
        if bbox is None:
            return None
        axis = [abs(a) for a in hole["axis"]]
        dominant = axis.index(max(axis))
        return bbox[dominant] if max(axis) > 0.99 else None

    def report(self, m):
        """One-line pass summary."""
        return ("bbox %.4f x %.4f x %.4f %s | volume %.4f %s^3 | %d solid(s) | "
                "%d hole(s) | %d faces"
                % (m["bbox"][0], m["bbox"][1], m["bbox"][2], self.units,
                   m["volume"], self.units, m["solids"], len(m["holes"]), m["faces"]))


def load_all(directory):
    """Every spec in a directory, refusing duplicate ids.

    Two specs sharing an `id` write to the same `<id>.step` and clear each
    other's deliverables, and both report a pass - the ordinary result of
    copying an existing spec to start a new part and forgetting to change the
    id, which is exactly how new parts get written.
    """
    d = pathlib.Path(directory)
    specs = [PartSpec.load(p) for p in sorted(d.glob("*.json"))]
    seen = {}
    for item in specs:
        if item.id in seen:
            raise SpecError(
                "two specs share the id %r: %s and %s. They would overwrite each "
                "other's deliverables and both report success."
                % (item.id, seen[item.id], item.source))
        seen[item.id] = item.source
    return specs


def demo():
    s = PartSpec({
        "id": "T-01", "name": "test plate", "description": "a plate",
        "constants": {"L": 4.0},
        "checks": {"bbox": [4.0, 1.5, 0.25], "volume": 1.5, "volume_tol": 0.05,
                   "solids": 1, "holes": [{"d": 0.281, "count": 2}]},
    })
    ok = {"bbox": [4.0, 1.5, 0.25], "volume": 1.5, "solids": 1, "valid": True,
          "faces": 13, "edges": 33, "center": [0, 0, 0.125],
          "holes": [{"d": 0.281}, {"d": 0.281}]}
    assert s.check(ok) == [], s.check(ok)

    bad = dict(ok, bbox=[4.5, 1.5, 0.25])
    msgs = s.check(bad)
    assert len(msgs) == 1 and "4.5000" in msgs[0] and "4.0000" in msgs[0]
    # The message has to tell the model which way to move and by how much.
    assert "-0.5000" in msgs[0], msgs[0]

    bad = dict(ok, holes=[{"d": 0.281}])
    msgs = s.check(bad)
    assert "expected 2" in msgs[0] and "DIAMETER" in msgs[0], msgs[0]

    bad = dict(ok, solids=3)
    assert "3 separate solid(s), expected 1" in s.check(bad)[0]

    bad = dict(ok, volume=2.0)
    assert "Too much material" in s.check(bad)[0]

    # A fitting envelope, not an exact size.
    fit = PartSpec({"id": "T-02", "name": "n", "description": "d",
                    "checks": {"size_max": [24.0, 20.0, 18.0]}})
    assert fit.check(dict(ok, bbox=[23.0, 19.0, 17.0])) == []
    over = fit.check(dict(ok, bbox=[25.0, 19.0, 17.0]))
    assert "must not exceed" in over[0] and "1.0000" in over[0]

    try:
        PartSpec({"id": "x", "name": "y", "description": "z"})
    except SpecError as e:
        assert "no checks" in str(e)
    else:
        raise AssertionError("a spec with no checks must be rejected")

    assert "4.0" in s.brief() and "0.281" in s.brief()
    print("spec demo ok")


if __name__ == "__main__":
    demo()
