#!/usr/bin/env python3
"""Deterministic mesh integrity evidence for the exported STL deliverables.

Supplier-facing STLs are checked for the failures that survive a clean Fusion
build and only surface downstream: non-manifold edges, inverted normals,
degenerate facets, a dropped body, and a silent unit/scale error on export.

These exports are multi-body assemblies (frame members plus component proxies)
whose bodies touch at coincident corners. Integrity is therefore judged per
solid, not over the merged facet soup -- touching bodies share edges, so the
merged mesh is legitimately non-manifold and checking it as one solid reports
failures that are not there.
"""
import argparse
import json
import math
import pathlib
import struct
from collections import defaultdict, deque

MM_PER_INCH = 25.4
QUANT = 1e-5  # mm; vertex weld tolerance for edge matching


def read_binary_stl(path):
    """Return (triangles, header). Each triangle is (normal, v0, v1, v2)."""
    data = pathlib.Path(path).read_bytes()
    if len(data) < 84:
        raise ValueError("file shorter than an STL header")
    if data[:5].lstrip().lower().startswith(b"solid") and b"facet" in data[:512]:
        raise ValueError("ASCII STL: this gate reads binary STL only")
    count = struct.unpack("<I", data[80:84])[0]
    if len(data) != 84 + 50 * count:
        raise ValueError(f"declares {count} facets, size implies {(len(data)-84)/50:.1f}")
    triangles = []
    for i in range(count):
        off = 84 + 50 * i
        values = struct.unpack("<12f", data[off:off + 48])
        triangles.append((values[0:3], values[3:6], values[6:9], values[9:12]))
    return triangles, data[:80].decode("ascii", "replace").strip()


def _key(vertex):
    return tuple(int(round(c / QUANT)) for c in vertex)


def _edges(triangle):
    keys = [_key(v) for v in triangle[1:]]
    for start, end in ((keys[0], keys[1]), (keys[1], keys[2]), (keys[2], keys[0])):
        yield start, end


def _area(a, b, c):
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    cross = [u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]]
    return 0.5 * math.sqrt(sum(x * x for x in cross))


def split_solids(triangles):
    """Group facets into solids, walking only edges shared by exactly two facets.

    Bodies that merely touch along coincident edges stay separate, which is what
    distinguishes a legitimate touching assembly from one broken body.
    """
    edge_to_facets = defaultdict(list)
    for index, triangle in enumerate(triangles):
        for start, end in _edges(triangle):
            edge_to_facets[(start, end) if start <= end else (end, start)].append(index)

    seen, solids = set(), []
    for index in range(len(triangles)):
        if index in seen:
            continue
        queue, group = deque([index]), []
        seen.add(index)
        while queue:
            current = queue.popleft()
            group.append(current)
            for start, end in _edges(triangles[current]):
                shared = edge_to_facets[(start, end) if start <= end else (end, start)]
                if len(shared) != 2:
                    continue
                neighbour = shared[0] if shared[1] == current else shared[1]
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        solids.append([triangles[i] for i in group])
    return solids


def inspect(triangles, min_area=1e-6):
    """Topology and orientation facts for one facet set. No judgement."""
    undirected, directed = {}, set()
    reversed_facets = degenerate = 0
    volume = 0.0
    lo, hi = [math.inf] * 3, [-math.inf] * 3

    for _normal, a, b, c in triangles:
        if _area(a, b, c) <= min_area:
            degenerate += 1
        # signed volume of the tetrahedron to the origin (divergence theorem)
        volume += (a[0] * (b[1] * c[2] - b[2] * c[1])
                   - a[1] * (b[0] * c[2] - b[2] * c[0])
                   + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6.0
        for vertex in (a, b, c):
            for axis in range(3):
                lo[axis] = min(lo[axis], vertex[axis])
                hi[axis] = max(hi[axis], vertex[axis])
        for start, end in _edges((_normal, a, b, c)):
            if (start, end) in directed:
                reversed_facets += 1
            directed.add((start, end))
            edge = (start, end) if start <= end else (end, start)
            undirected[edge] = undirected.get(edge, 0) + 1

    boundary = sum(1 for n in undirected.values() if n == 1)
    nonmanifold = sum(1 for n in undirected.values() if n > 2)
    return {
        "facets": len(triangles),
        "degenerate_facets": degenerate,
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "reversed_facets": reversed_facets,
        "watertight": boundary == 0 and nonmanifold == 0,
        "signed_volume_mm3": round(volume, 4),
        "bbox_mm": [round(hi[i] - lo[i], 4) for i in range(3)],
        "origin_mm": [round(x, 4) for x in lo],
    }


def envelope(triangles):
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for _normal, *vertices in triangles:
        for vertex in vertices:
            for axis in range(3):
                lo[axis] = min(lo[axis], vertex[axis])
                hi[axis] = max(hi[axis], vertex[axis])
    return [round(hi[i] - lo[i], 4) for i in range(3)]


def expected_solids(job):
    """Frame members from the cut list, plus one proxy per declared component."""
    members = sum(entry["quantity"] for entry in job["frame"]["cut_list"])
    return members + len(job.get("components", []))


def check_file(stl_path, job, tolerance_in, scale):
    record = {"module_id": job["module_id"], "stl": str(stl_path), "reasons": []}
    try:
        triangles, header = read_binary_stl(stl_path)
    except ValueError as exc:
        record["reasons"] = [f"unreadable STL: {exc}"]
        record["pass"] = False
        return record

    record["exporter"] = header
    record["facets"] = len(triangles)

    solids = split_solids(triangles)
    facts = [inspect(solid) for solid in solids]
    record["solids"] = len(solids)
    record["expected_solids"] = expected_solids(job)

    broken = []
    for index, fact in enumerate(facts):
        reasons = []
        if not fact["watertight"]:
            reasons.append(f"{fact['boundary_edges']} boundary / "
                           f"{fact['nonmanifold_edges']} non-manifold edges")
        if fact["reversed_facets"]:
            reasons.append(f"{fact['reversed_facets']} facets with inconsistent winding")
        if fact["degenerate_facets"]:
            reasons.append(f"{fact['degenerate_facets']} degenerate facets")
        # signed volume only means anything on a closed surface
        if fact["watertight"] and fact["signed_volume_mm3"] <= 0:
            reasons.append(f"signed volume {fact['signed_volume_mm3']} <= 0 "
                           "(normals point inward)")
        if reasons:
            broken.append({"solid_index": index, "bbox_mm": fact["bbox_mm"],
                           "reasons": reasons})

    record["broken_solids"] = broken
    record["solid_volumes_mm3"] = [f["signed_volume_mm3"] for f in facts]
    for entry in broken:
        record["reasons"].append(f"solid {entry['solid_index']} "
                                 f"{entry['bbox_mm']}mm: {'; '.join(entry['reasons'])}")

    if record["solids"] != record["expected_solids"]:
        record["reasons"].append(
            f"{record['solids']} solids in STL, job declares "
            f"{record['expected_solids']} (cut list + components); a body was "
            "dropped, merged, or added on export")

    measured = [round(d / scale, 4) for d in envelope(triangles)]
    declared = job["frame"]["outside_in"]
    drift = [round(abs(m - d), 4) for m, d in zip(measured, declared)]
    record["declared_frame_in"] = declared
    record["measured_bbox_in"] = measured
    record["bbox_drift_in"] = drift
    if any(x > tolerance_in for x in drift):
        record["reasons"].append(
            f"bbox {measured}in != declared {declared}in (drift {drift} > "
            f"{tolerance_in}); check export units/scale")

    record["pass"] = not record["reasons"]
    return record


def evaluate(job_dir, export_dir, tolerance_in, stl_units):
    scale = MM_PER_INCH if stl_units == "mm" else 1.0
    results, failures = [], []
    for job_path in sorted(pathlib.Path(job_dir).glob("*.job.json")):
        job = json.loads(job_path.read_text())
        stl_path = pathlib.Path(export_dir) / f"{job['module_id']}.stl"
        if not stl_path.is_file():
            record = {"module_id": job["module_id"], "stl": str(stl_path),
                      "reasons": ["STL deliverable missing"], "pass": False}
        else:
            record = check_file(stl_path, job, tolerance_in, scale)
        results.append(record)
        if not record["pass"]:
            failures.append(record)

    return {
        "gate": "mesh_integrity",
        "pass": bool(results) and not failures,
        "tolerance_in": tolerance_in,
        "stl_units_assumed": stl_units,
        "modules_checked": len(results),
        "results": results,
        "failures": failures,
        "limitations": [
            "Per-solid topology, body count, and overall scale only. Says nothing "
            "about structural adequacy, tolerances, fabrication readiness, or fit "
            "of purchased components.",
            "Bodies that interpenetrate rather than touch are not detected here; "
            "packaging clearance is clearance_check.py's job.",
            "Geometry proxies, not manufacturing geometry.",
        ],
    }


def _cube(origin=(0.0, 0.0, 0.0), size=1.0):
    x, y, z = origin
    s = size
    p = [(x, y, z), (x+s, y, z), (x+s, y+s, z), (x, y+s, z),
         (x, y, z+s), (x+s, y, z+s), (x+s, y+s, z+s), (x, y+s, z+s)]

    def quad(a, b, c, d):
        return [((0.0, 0.0, 0.0), a, b, c), ((0.0, 0.0, 0.0), a, c, d)]
    return (quad(p[0], p[3], p[2], p[1]) + quad(p[4], p[5], p[6], p[7])
            + quad(p[0], p[1], p[5], p[4]) + quad(p[1], p[2], p[6], p[5])
            + quad(p[2], p[3], p[7], p[6]) + quad(p[3], p[0], p[4], p[7]))


def selftest():
    cube = _cube()
    good = inspect(cube)
    assert good["watertight"] and good["reversed_facets"] == 0, good
    assert good["degenerate_facets"] == 0, good
    assert abs(good["signed_volume_mm3"] - 1.0) < 1e-6, good
    assert good["bbox_mm"] == [1.0, 1.0, 1.0], good

    holed = inspect(cube[:-1])
    assert not holed["watertight"] and holed["boundary_edges"] == 3, holed

    inverted = inspect([(n, a, c, b) for n, a, b, c in cube])
    assert inverted["watertight"] and inverted["signed_volume_mm3"] < 0, inverted

    flat = inspect(cube + [((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0),
                            (1.0, 0.0, 0.0))])
    assert flat["degenerate_facets"] == 1, flat

    # the regression this gate exists to avoid: two cubes sharing a corner edge
    # are two clean solids, even though the merged soup is non-manifold.
    touching = cube + _cube(origin=(1.0, 1.0, 0.0))
    merged = inspect(touching)
    assert not merged["watertight"], "touching bodies should look non-manifold merged"
    solids = split_solids(touching)
    assert len(solids) == 2, len(solids)
    for solid in solids:
        fact = inspect(solid)
        assert fact["watertight"] and fact["reversed_facets"] == 0, fact
        assert fact["signed_volume_mm3"] > 0, fact

    # a genuinely broken body is still caught after splitting
    broken = split_solids(cube[:-1] + _cube(origin=(5.0, 5.0, 5.0)))
    assert sum(1 for s in broken if not inspect(s)["watertight"]) == 1, broken

    assert expected_solids({"frame": {"cut_list": [{"length": 18.0, "quantity": 8},
                                                   {"length": 22.0, "quantity": 4}]},
                            "components": [{}, {}]}) == 14
    print("selftest OK")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", default="jobs")
    parser.add_argument("--exports", default="exports")
    parser.add_argument("--output")
    parser.add_argument("--tolerance", type=float, default=0.01,
                        help="allowed bbox drift, inches")
    parser.add_argument("--stl-units", choices=["mm", "inch"], default="mm")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    if not args.output:
        parser.error("--output is required")

    report = evaluate(args.jobs, args.exports, args.tolerance, args.stl_units)
    pathlib.Path(args.output).write_text(json.dumps(report, indent=2) + "\n")
    if not report["pass"]:
        for failure in report["failures"]:
            for reason in failure["reasons"]:
                print(f"FAIL {failure['module_id']}: {reason}")
        return 1
    print(f"MESH INTEGRITY PASS: {report['modules_checked']} modules -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
