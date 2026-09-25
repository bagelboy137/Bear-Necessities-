#!/usr/bin/env python3
"""Deterministic product-drawing quality gate for a DXF and CAD job."""

import json
import pathlib
import sys

import ezdxf

REQUIRED_LAYERS = {"OUTLINE", "HIDDEN", "CENTER", "DIMENSIONS", "TEXT", "TITLEBLOCK"}


def text_of(entity):
    if entity.dxftype() == "TEXT":
        return entity.dxf.text or ""
    if entity.dxftype() == "MTEXT":
        return entity.text or ""
    return ""


def main():
    if len(sys.argv) != 3:
        print("usage: drawing_quality.py JOB.json DRAWING.dxf", file=sys.stderr)
        return 2
    job = json.loads(pathlib.Path(sys.argv[1]).read_text())
    drawing = pathlib.Path(sys.argv[2])
    try:
        doc = ezdxf.readfile(drawing)
    except Exception as exc:
        print(f"DRAWING QUALITY FAILED:\n1. DXF cannot be opened: {exc}", file=sys.stderr)
        return 1

    errors = []
    msp = doc.modelspace()
    entities = list(msp)
    layers = {entity.dxf.layer.upper() for entity in entities if hasattr(entity.dxf, "layer")}
    missing_layers = sorted(REQUIRED_LAYERS - layers)
    if missing_layers:
        errors.append("Missing populated drafting layers: " + ", ".join(missing_layers))
    dims = [entity for entity in entities if entity.dxftype() == "DIMENSION"]
    minimum_dimensions = max(3, len(job["engineering"]["interfaces"]))
    if len(dims) < minimum_dimensions:
        errors.append(f"Only {len(dims)} true DIMENSION entities; need at least {minimum_dimensions}. "
                      "Text labels are not dimensions.")
    texts = " | ".join(text_of(entity) for entity in entities
                       if entity.dxftype() in ("TEXT", "MTEXT")).upper()
    required_text = [
        job["job_id"].upper(), f"REV {job['revision']}".upper(),
        job["engineering"]["material"].upper().split(",")[0],
        job["engineering"]["manufacturing_process"].upper().split(" ")[0],
        "DO NOT SCALE", "UNITS", "TOLERANCE",
    ]
    if job["status"] == "READY_PROTOTYPE":
        required_text.append("PROTOTYPE")
    for phrase in required_text:
        if phrase not in texts:
            errors.append(f"Title block/notes missing required text: {phrase}")
    if not any(entity.dxftype() in ("CENTERLINE", "LINE", "LWPOLYLINE") and
               entity.dxf.layer.upper() == "CENTER" for entity in entities):
        errors.append("No centerline geometry on CENTER layer")
    if not any(entity.dxf.layer.upper() == "TITLEBLOCK" for entity in entities):
        errors.append("No title-block geometry or text on TITLEBLOCK layer")

    if errors:
        print("DRAWING QUALITY FAILED:", file=sys.stderr)
        for index, error in enumerate(errors, 1):
            print(f"{index}. {error}", file=sys.stderr)
        return 1
    print(f"DRAWING QUALITY PASS: {len(dims)} dimensions, {len(layers)} populated layers, "
          f"revision {job['revision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
