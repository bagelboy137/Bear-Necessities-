#!/usr/bin/env python3
"""A read-only inventory of the active Fusion design, for an agent to diff.

The single most useful thing an agent editing CAD can do is measure before and
after every change and compare the numbers with what it predicted. Asking the
model to write that measuring code each time wastes a round trip and invites
mistakes in the very code meant to catch mistakes, so it is written once, here,
and the MCP proxy exposes it as the `bn_snapshot` tool.

SCRIPT runs inside Fusion's own interpreter (it is never imported here). It
reports document identity, every body with its bounding box and volume in
assembly coordinates, occurrences, timeline health, user parameters and joints.
Each section is measured independently: an API call that a future Fusion build
renames costs that one section an "error" entry, not the whole snapshot.

API members used are ones this project has already run against live Fusion
(bodies, bounding boxes, volume, allOccurrences), ones exercised live by the
public fusion-mcp-client project (dataFile id/version, isModified, timeline
healthState), or ones checked in Autodesk's API reference (Component.allJoints,
Design.analyzeInterference). It has not yet been run against live Fusion from
this repo - treat the first run on the Mac as its acceptance test.

    python3 fusion_snapshot.py --demo     # self-check, no Fusion needed
"""

import ast
import json
import sys

MARKER = "BN_SNAPSHOT "
UNITS = ("in", "mm", "cm")

SCRIPT = r'''
import adsk.core, adsk.fusion, json

UNITS = __UNITS__
DETAIL = __DETAIL__
# Fusion's API is centimetres whatever the document displays.
SCALE = {"in": 1 / 2.54, "mm": 10.0, "cm": 1.0}[UNITS]
LIMIT = 400


def _len(v):
    return round(v * SCALE, 4)


def _vol(v):
    return round(v * SCALE ** 3, 4)


def _box(bb):
    lo, hi = bb.minPoint, bb.maxPoint
    return {"min": [_len(lo.x), _len(lo.y), _len(lo.z)],
            "max": [_len(hi.x), _len(hi.y), _len(hi.z)],
            "size": [_len(hi.x - lo.x), _len(hi.y - lo.y), _len(hi.z - lo.z)]}


def _section(fn):
    try:
        return fn()
    except Exception as e:
        return {"error": "%s: %s" % (type(e).__name__, e)}


def _bodies(root):
    for b in root.bRepBodies:
        yield "root::" + b.name, b
    for occ in root.allOccurrences:
        for b in occ.bRepBodies:
            yield occ.fullPathName + "::" + b.name, b


def run(_context: str):
    app = adsk.core.Application.get()
    out = {"units": UNITS, "detail": DETAIL}
    out["fusion_version"] = _section(lambda: app.version)
    doc = app.activeDocument
    if not doc:
        out["error"] = "no active document"
        print("BN_SNAPSHOT " + json.dumps(out))
        return

    def document():
        data = doc.dataFile
        return {"name": doc.name, "modified": doc.isModified,
                "id": data.id if data else None,
                "version": data.versionNumber if data else None}
    out["document"] = _section(document)

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        out["error"] = "the active product is not a Fusion design"
        print("BN_SNAPSHOT " + json.dumps(out))
        return
    root = design.rootComponent

    def design_info():
        parametric = design.designType == adsk.fusion.DesignTypes.ParametricDesignType
        return {"type": "parametric" if parametric else "direct",
                "display_units": design.unitsManager.defaultLengthUnits,
                "components": design.allComponents.count,
                "occurrences": root.allOccurrences.count}
    out["design"] = _section(design_info)

    def bodies():
        rows, total, envelope = [], 0, None
        for selector, b in _bodies(root):
            total += 1
            box = _box(b.boundingBox)
            if b.isVisible:
                if envelope is None:
                    envelope = [list(box["min"]), list(box["max"])]
                else:
                    envelope[0] = [min(a, c) for a, c in zip(envelope[0], box["min"])]
                    envelope[1] = [max(a, c) for a, c in zip(envelope[1], box["max"])]
            if DETAIL == "full" and len(rows) < LIMIT:
                material = None
                try:
                    material = b.material.name if b.material else None
                except Exception:
                    pass
                rows.append({"selector": selector, "visible": b.isVisible,
                             "solid": b.isSolid, "lumps": b.lumps.count,
                             "volume": _vol(b.volume), "bbox": box,
                             "material": material})
        summary = {"count": total, "visible_envelope": None}
        if envelope:
            summary["visible_envelope"] = {
                "min": envelope[0], "max": envelope[1],
                "size": [round(h - l, 4) for l, h in zip(*envelope)]}
        if DETAIL == "full":
            summary["items"] = rows
            summary["truncated"] = total > LIMIT
        return summary
    out["bodies"] = _section(bodies)

    def occurrences():
        rows = []
        for occ in root.allOccurrences:
            if len(rows) >= LIMIT:
                break
            try:
                t = occ.transform2.translation
            except Exception:
                t = occ.transform.translation
            rows.append({"path": occ.fullPathName, "component": occ.component.name,
                         "grounded": occ.isGrounded, "visible": occ.isVisible,
                         "translation": [_len(t.x), _len(t.y), _len(t.z)]})
        return rows
    if DETAIL == "full":
        out["occurrences"] = _section(occurrences)

    def timeline():
        tl = design.timeline
        problems, suppressed = [], 0
        for i in range(tl.count):
            item = tl.item(i)
            if item.isSuppressed:
                suppressed += 1
            entity = item.entity
            if entity is not None and hasattr(entity, "healthState"):
                healthy = adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
                if entity.healthState != healthy:
                    problems.append({"name": item.name,
                                     "message": entity.errorOrWarningMessage})
        return {"count": tl.count, "marker": tl.markerPosition,
                "suppressed": suppressed, "unhealthy": problems}
    if design.designType == adsk.fusion.DesignTypes.ParametricDesignType:
        out["timeline"] = _section(timeline)

    def parameters():
        return [{"name": p.name, "expression": p.expression, "unit": p.unit,
                 "comment": p.comment} for p in design.userParameters]
    out["user_parameters"] = _section(parameters)

    # adsk.fusion.JointTypes values, from Autodesk's API reference.
    joint_types = {0: "rigid", 1: "revolute", 2: "slider", 3: "cylindrical",
                   4: "pin-slot", 5: "planar", 6: "ball"}

    def joints():
        rows = []
        for j in root.allJoints:
            one, two = j.occurrenceOne, j.occurrenceTwo
            kind = j.jointMotion.jointType
            rows.append({"name": j.name,
                         "type": joint_types.get(kind, str(kind)),
                         "one": one.fullPathName if one else "root",
                         "two": two.fullPathName if two else "root",
                         "suppressed": j.isSuppressed})
        return {"count": len(rows), "items": rows if DETAIL == "full" else None,
                "as_built": len(root.allAsBuiltJoints),
                "rigid_groups": len(root.allRigidGroups)}
    out["joints"] = _section(joints)

    print("BN_SNAPSHOT " + json.dumps(out))
'''


def script(units="in", detail="full"):
    """The snapshot as Fusion-ready source. Raises ValueError on bad options,
    before anything is sent to Fusion."""
    if units not in UNITS:
        raise ValueError("units must be one of %s, not %r" % (", ".join(UNITS), units))
    if detail not in ("summary", "full"):
        raise ValueError("detail must be 'summary' or 'full', not %r" % (detail,))
    return SCRIPT.replace("__UNITS__", repr(units)).replace("__DETAIL__", repr(detail))


def _texts(result):
    """Every string a tool result could carry the script's stdout in."""
    blobs = []
    if not isinstance(result, dict):
        return [str(result)]
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        blobs.append(str(structured.get("message", "")))
    for block in result.get("content", []) or []:
        if block.get("type") != "text":
            continue
        text = block.get("text", "")
        blobs.append(text)
        # Fusion wraps stdout in {"message": "...", "success": true}.
        try:
            envelope = json.loads(text)
        except (TypeError, ValueError):
            continue
        if isinstance(envelope, dict):
            blobs.append(str(envelope.get("message", "")))
    return blobs


def parse(result):
    """The snapshot dict from a fusion_mcp_execute result, or None."""
    for blob in _texts(result):
        for line in blob.splitlines():
            line = line.strip()
            if line.startswith(MARKER):
                return json.loads(line[len(MARKER):])
    return None


def demo():
    for units in UNITS:
        for detail in ("summary", "full"):
            src = script(units, detail)
            tree = ast.parse(src)
            assert any(isinstance(n, ast.FunctionDef) and n.name == "run"
                       for n in tree.body), "Fusion needs a module-level run()"
            assert "__UNITS__" not in src and "__DETAIL__" not in src
    for bad in (("ft", "full"), ("in", "everything")):
        try:
            script(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError("accepted %r" % (bad,))

    payload = {"units": "in", "bodies": {"count": 2}}
    line = MARKER + json.dumps(payload)
    plain = {"content": [{"type": "text", "text": "noise\n" + line + "\n"}]}
    wrapped = {"content": [{"type": "text",
                            "text": json.dumps({"message": line, "success": True})}]}
    structured = {"structuredContent": {"message": line, "success": True}}
    for shape in (plain, wrapped, structured):
        assert parse(shape) == payload, shape
    assert parse({"content": [{"type": "text", "text": "nothing"}]}) is None
    print("fusion_snapshot demo ok: script compiles for every option; "
          "plain, enveloped and structured replies all parse")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        demo()
    else:
        sys.stdout.write(script(*(sys.argv[1:3] or ["in"])))
