#!/usr/bin/env python3
"""Hand a headless-built solid to a live Fusion session.

Fusion is the preferred home for this work, but it cannot be the workhorse: it
has no headless mode, its MCP server exists only while the app is open and
signed in, and on a 16 GB machine it has already crashed under a sustained
render batch. So CadQuery builds the geometry unattended and Fusion picks it up
when it is running - the STEP is the handoff, and it carries the exact solid
that was measured and passed.

The MCP client and port discovery already exist in ../bridge. They are imported,
not reimplemented; bridge owns MCP connectivity for this project.
"""

import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
BRIDGE = HERE.parent / "bridge"
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))

# The one place Fusion actually lives on macOS. It is NOT in /Applications -
# Fusion is a webdeploy app and only sometimes leaves an alias there. Looking in
# /Applications and concluding "not installed" is the standard wrong turn.
APP = pathlib.Path(os.path.expanduser(
    "~/Library/Application Support/Autodesk/webdeploy/production/"
    "Autodesk Fusion.app"))


def installed():
    return APP.exists()


def _client():
    from fusion_mcp import FusionMCP
    from fusion_port import discover
    url = discover(configured="auto")
    c = FusionMCP(url)
    c.connect()
    return c, url


def available():
    """(reachable, url_or_reason). Never raises - callers branch on the bool."""
    try:
        c, url = _client()
        return True, url
    except Exception as e:
        return False, str(e)


# Fusion's script entry point is `def run(_context: str):` - underscore and type
# hint both required. A fresh document per run: deleting bodies does not clear a
# parametric design, the timeline just regenerates them, so reusing a document
# silently mixes old geometry into new measurements.
IMPORT_SCRIPT = '''
def run(_context: str):
    import adsk.core, adsk.fusion, traceback
    try:
        app = adsk.core.Application.get()
        docs = app.documents
        doc = docs.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = app.activeProduct
        root = design.rootComponent

        mgr = app.importManager
        opts = mgr.createSTEPImportOptions({path!r})
        mgr.importToTarget(opts, root)

        bodies = []
        for occ in root.allOccurrences:
            for b in occ.bRepBodies:
                bodies.append(b)
        for b in root.bRepBodies:
            bodies.append(b)

        if not bodies:
            print("IMPORTED_BUT_EMPTY")
            return

        bb = None
        vol = 0.0
        for b in bodies:
            vol += b.volume
            bbox = b.boundingBox
            if bb is None:
                bb = [bbox.minPoint.x, bbox.minPoint.y, bbox.minPoint.z,
                      bbox.maxPoint.x, bbox.maxPoint.y, bbox.maxPoint.z]
            else:
                bb[0] = min(bb[0], bbox.minPoint.x); bb[3] = max(bb[3], bbox.maxPoint.x)
                bb[1] = min(bb[1], bbox.minPoint.y); bb[4] = max(bb[4], bbox.maxPoint.y)
                bb[2] = min(bb[2], bbox.minPoint.z); bb[5] = max(bb[5], bbox.maxPoint.z)

        # Fusion's API is centimetres regardless of document units.
        CM = 2.54
        print("RESULT " + repr({{
            "bodies": len(bodies),
            "volume_in3": vol / (CM ** 3),
            "bbox_in": [(bb[3]-bb[0])/CM, (bb[4]-bb[1])/CM, (bb[5]-bb[2])/CM],
            "doc": doc.name,
        }}))
    except Exception:
        print("TRACEBACK\\n" + traceback.format_exc())
        raise
'''


def import_step(step_path, timeout=300):
    """Import a STEP into a fresh Fusion document and measure it there.

    Returns a dict with Fusion's own bbox and volume, in inches. That is a
    genuinely independent check: if CadQuery and Fusion disagree about the same
    STEP, the file is the problem, not either kernel.
    """
    step_path = str(pathlib.Path(step_path).resolve())
    if not os.path.exists(step_path):
        raise FileNotFoundError(step_path)
    c, url = _client()
    c.timeout = timeout
    out, is_err = c.run_script(IMPORT_SCRIPT.format(path=step_path))
    if is_err:
        raise RuntimeError("Fusion rejected the import script:\n%s" % out)
    parsed = _parse_result(out)
    if parsed is None:
        raise RuntimeError("Fusion ran the script but returned no RESULT line:\n%s" % out)
    return parsed


def _parse_result(out):
    """Pull the RESULT payload out of whatever Fusion wrapped it in.

    Fusion does not hand back the script's stdout verbatim. It returns a JSON
    envelope - {"message": "RESULT {...}\\n", "success": true} - so scanning for
    a line that *starts with* RESULT finds nothing and the real answer sits
    inside the error message. Handle both shapes.
    """
    import ast as _ast
    candidates = [out]
    try:
        envelope = json.loads(out)
    except (ValueError, TypeError):
        pass
    else:
        if isinstance(envelope, dict):
            candidates.append(str(envelope.get("message", "")))
    for blob in candidates:
        for line in blob.splitlines():
            line = line.strip()
            if line.startswith("RESULT "):
                return _ast.literal_eval(line[len("RESULT "):])
    return None


def cross_check(step_path, measured, tol=0.01, scale=25.4):
    """Compare Fusion's measurement of a STEP against CadQuery's. [] means agree.

    `measured` is in the spec's units and Fusion reports inches, so a spec in
    anything other than inches needs converting before the two are comparable.
    """
    f = import_step(step_path)
    to_spec = 25.4 / float(scale)
    f = dict(f, bbox_in=[v * to_spec for v in f["bbox_in"]],
             volume_in3=f["volume_in3"] * (to_spec ** 3))
    errs = []
    for axis, a, b in zip("XYZ", measured["bbox"], f["bbox_in"]):
        if abs(a - b) > tol:
            errs.append("%s: CadQuery %.4f vs Fusion %.4f (%.4f apart)"
                        % (axis, a, b, abs(a - b)))
    if abs(measured["volume"] - f["volume_in3"]) > max(tol, 0.005 * measured["volume"]):
        errs.append("volume: CadQuery %.4f vs Fusion %.4f"
                    % (measured["volume"], f["volume_in3"]))
    return errs, f


def demo():
    # Runs with Fusion closed, which is the normal state. What is checked here
    # is that the module degrades cleanly rather than raising.
    ok, detail = available()
    assert isinstance(ok, bool) and isinstance(detail, str)
    assert "{path!r}" not in IMPORT_SCRIPT.format(path="/x.step")
    assert "'/x.step'" in IMPORT_SCRIPT.format(path="/x.step")
    # The doubled braces must survive formatting as real dict braces.
    body = IMPORT_SCRIPT.format(path="/x.step")
    assert '"bodies": len(bodies)' in body
    compile(body, "<import_script>", "exec")

    # Fusion wraps stdout in a JSON envelope; both shapes must parse.
    raw = "noise\nRESULT {'bodies': 1, 'volume_in3': 2.0, 'bbox_in': [1.0, 2.0, 3.0]}\n"
    assert _parse_result(raw)["bodies"] == 1
    wrapped = json.dumps({"message": raw, "success": True})
    assert _parse_result(wrapped)["bbox_in"] == [1.0, 2.0, 3.0]
    assert _parse_result("nothing useful here") is None
    print("fusion demo ok (installed=%s, reachable=%s)" % (installed(), ok))


if __name__ == "__main__":
    demo()
