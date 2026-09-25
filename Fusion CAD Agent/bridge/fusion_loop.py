#!/usr/bin/env python3
"""
fusion_loop.py — closed feedback loop: LOCAL MODEL -> LIVE FUSION.

The local LM Studio model writes a Fusion Python script; Fusion's built-in MCP
server executes it in the live session and returns stdout AND the real
traceback; failures are fed straight back for another attempt; success is
verified numerically and captured as a screenshot.

This replaces the watcher-add-in design entirely. Fusion ships the execution
and feedback path natively, so nothing has to be installed into Fusion.

    python3 bridge/fusion_loop.py --spec specs/overland-base-frame-ots.md \
        --model qwen2.5-coder-7b-instruct --expect-bbox 24,20,18 --expect-volume 232
"""
import argparse, base64, json, pathlib, re, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bridge"))
from fusion_mcp import FusionMCP  # noqa: E402

LMS = "http://localhost:1234/v1/chat/completions"

SYSTEM = """You write Python for the Autodesk Fusion API. Your script is executed
inside a LIVE Fusion session and its output comes straight back to you.

HARD RULES
1. Output ONE complete Python script in a single ```python code block. No prose.
2. Entry point MUST be exactly:  def run(_context: str):
   Note the underscore and the type hint. Not `context`.
3. DO NOT wrap your code in try/except. Let exceptions propagate - the real
   traceback is returned to you and is how you fix your own bugs. Swallowing it
   blinds you.
4. NEVER call ui.messageBox - it blocks forever with nobody to click it.
5. The Fusion API is ALWAYS in CENTIMETRES. The spec is in INCHES.
   Define IN = 2.54 and multiply every inch dimension by it. State the
   conversion in a comment.
6. print() the finished dimensions so they can be checked.

GETTING A DESIGN
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
You cannot rename rootComponent - it raises. Do not try.

PLACING A RECTANGULAR MEMBER - USE THIS EXACT PATTERN
Sketch a rectangle on XY, then extrude it from an offset start plane:

    def box(root, lx, ly, lz, x, y, z):
        sk = root.sketches.add(root.xYConstructionPlane)
        sk.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point3D.create(x, y, 0),
            adsk.core.Point3D.create(x + lx, y + ly, 0))
        ext = root.features.extrudeFeatures
        op = (adsk.fusion.FeatureOperations.JoinFeatureOperation
              if root.bRepBodies.count else
              adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp = ext.createInput(sk.profiles.item(0), op)
        inp.startExtent = adsk.fusion.FromEntityStartDefinition.create(
            root.xYConstructionPlane, adsk.core.ValueInput.createByReal(z))
        inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(lz))
        return ext.add(inp)

BUILD A MEMBER TABLE - NEVER WRITE INDIVIDUAL box() CALLS BY HAND
Hand-computed offsets are where this goes wrong every time. For a rectangular
cube frame of OUTSIDE size W x D x H from P-square profile, the table is:

    IN = 2.54
    W, D, H, P = 24.0*IN, 20.0*IN, 18.0*IN, 1.0*IN

    MEMBERS = []
    for x in (0, W - P):                      # 4 vertical posts, full height
        for y in (0, D - P):
            MEMBERS.append((P, P, H, x, y, 0))
    for y in (0, D - P):                      # 4 width rails along X, between posts
        for z in (0, H - P):
            MEMBERS.append((W - 2*P, P, P, P, y, z))
    for x in (0, W - P):                      # 4 depth rails along Y, between posts
        for z in (0, H - P):
            MEMBERS.append((P, D - 2*P, P, x, P, z))

    for (lx, ly, lz, x, y, z) in MEMBERS:
        box(root, lx, ly, lz, x, y, z)

Posts are P x P x H - NOT cubes. Rails are (W-2P) or (D-2P) long and P x P in
section. The union must span exactly 0..W, 0..D, 0..H. Join every member so the
result is ONE body.

FLAT PLATE WITH FILLETED CORNERS AND THROUGH HOLES - USE THIS EXACT PATTERN
There is no ConstructionPlane.yDirection. Do not invent plane attributes.
Sketch on root.xYConstructionPlane and work in XY coordinates directly.

    def plate(root, L, W, T, R, holes):   # holes = [(x, y, dia), ...] in cm
        VI = adsk.core.ValueInput
        P3 = adsk.core.Point3D
        ext = root.features.extrudeFeatures

        sk = root.sketches.add(root.xYConstructionPlane)
        sk.sketchCurves.sketchLines.addTwoPointRectangle(
            P3.create(-L/2, -W/2, 0), P3.create(L/2, W/2, 0))
        inp = ext.createInput(sk.profiles.item(0),
                              adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        inp.setDistanceExtent(False, VI.createByReal(T))
        body = ext.add(inp).bodies.item(0)

        # Fillet only the VERTICAL corner edges (start and end share x and y).
        edges = adsk.core.ObjectCollection.create()
        for e in body.edges:
            g = e.geometry
            try:
                sp, ep = g.startPoint, g.endPoint
            except AttributeError:
                continue
            if abs(sp.x - ep.x) < 1e-9 and abs(sp.y - ep.y) < 1e-9:
                edges.add(e)
        fin = root.features.filletFeatures.createInput()
        fin.addConstantRadiusEdgeSet(edges, VI.createByReal(R), True)
        root.features.filletFeatures.add(fin)

        # All holes in ONE sketch, then one cut through everything.
        sk2 = root.sketches.add(root.xYConstructionPlane)
        for (hx, hy, dia) in holes:
            sk2.sketchCurves.sketchCircles.addByCenterRadius(P3.create(hx, hy, 0), dia/2)
        profs = adsk.core.ObjectCollection.create()
        for i in range(sk2.profiles.count):
            profs.add(sk2.profiles.item(i))
        cin = ext.createInput(profs, adsk.fusion.FeatureOperations.CutFeatureOperation)
        cin.setAllExtent(adsk.fusion.ExtentDirections.NegativeExtentDirection)
        ext.add(cin)
        return body

The plate is CENTRED on the origin, so hole coordinates are measured from the
plate centre exactly as the spec states them.

If you are given a traceback, fix THAT specific error. Do not start over."""

VERIFY = '''import adsk.core, adsk.fusion

def run(_context: str):
    IN = 2.54
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    b = root.bRepBodies
    if not b.count:
        print("NO_BODIES")
        return
    vol = sum(b.item(i).volume for i in range(b.count))
    bb = b.item(0).boundingBox
    for i in range(1, b.count):
        bb.combine(b.item(i).boundingBox)
    print("BODIES=%d" % b.count)
    print("BBOX=%.4f,%.4f,%.4f" % ((bb.maxPoint.x-bb.minPoint.x)/IN,
                                   (bb.maxPoint.y-bb.minPoint.y)/IN,
                                   (bb.maxPoint.z-bb.minPoint.z)/IN))
    print("VOLUME=%.4f" % (vol/(IN**3)))
'''

CLEAR = '''import adsk.core, adsk.fusion

def run(_context: str):
    # A fresh document per attempt. Deleting bodies is NOT enough in a
    # parametric design: the timeline regenerates them, so deleteMe() reports
    # success while the geometry survives and corrupts the next measurement.
    app = adsk.core.Application.get()
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    print("fresh document:", doc.name, "bodies:", design.rootComponent.bRepBodies.count)
'''


def ask(prompt, model, temperature=0.15, max_tokens=6000):
    body = json.dumps({"model": model, "temperature": temperature,
                       "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(LMS, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def code_of(t):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", t, re.S)
    return (m.group(1) if m else t).strip()


def parse_verify(out):
    d = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            d[k.strip()] = v.strip()
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--model", default="qwen2.5-coder-7b-instruct")
    ap.add_argument("--expect-bbox", help="W,D,H in inches")
    ap.add_argument("--expect-volume", type=float)
    ap.add_argument("--tol", type=float, default=0.03)
    ap.add_argument("--max-attempts", type=int, default=10)
    ap.add_argument("--out-name", default="fusion-part")
    a = ap.parse_args()

    spec = pathlib.Path(a.spec).read_text()
    logs = ROOT / "bridge" / "logs"; logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"{a.out_name}-fusion.log"
    scripts = ROOT / "scripts"; scripts.mkdir(exist_ok=True)
    exports = ROOT / "exports"; exports.mkdir(exist_ok=True)

    def note(s):
        print(s, flush=True)
        with log.open("a") as f:
            f.write(s + "\n")

    m = FusionMCP()
    info = m.connect()
    note(f"\n{'='*68}\nRUN {time.strftime('%Y-%m-%d %H:%M:%S')} model={a.model}")
    note(f"Fusion MCP: {info.get('serverInfo', {}).get('name')}\n{'='*68}")

    want_bbox = [float(x) for x in a.expect_bbox.split(",")] if a.expect_bbox else None

    task = (f"Build this part in Fusion.\n\n--- SPEC ---\n{spec}\n--- END SPEC ---\n\n"
            f"Print the final outside dimensions in inches at the end.")

    prev_err = prev_code = None
    for attempt in range(1, a.max_attempts + 1):
        note(f"\n--- attempt {attempt}/{a.max_attempts} ---")
        prompt = task if prev_err is None else (
            f"{task}\n\n--- YOUR PREVIOUS SCRIPT ---\n{prev_code}\n"
            f"--- IT FAILED WITH ---\n{prev_err}\n\nFix that specific problem.")

        t0 = time.time()
        try:
            code = code_of(ask(prompt, a.model))
        except Exception as e:
            note(f"  model call failed: {e}"); time.sleep(5); continue
        if not code:
            prev_err, prev_code = "You returned no code block.", ""
            continue
        note(f"  generated {len(code)} chars in {time.time()-t0:.0f}s")

        (scripts / f"{a.out_name}_fusion.py").write_text(code)

        m.run_script(CLEAR)                      # fresh slate each attempt
        out, is_err = m.run_script(code)
        try:
            payload = json.loads(out)
        except Exception:
            payload = {"message": out, "success": not is_err}

        if not payload.get("success", False):
            err = payload.get("error", out)[:2500]
            note("  FUSION ERROR:\n    " + err.replace("\n", "\n    ")[:1200])
            prev_err, prev_code = err, code
            continue

        note("  ran OK: " + payload.get("message", "").strip().replace("\n", " | ")[:200])

        vout, _ = m.run_script(VERIFY)
        try:
            vmsg = json.loads(vout).get("message", "")
        except Exception:
            vmsg = vout
        v = parse_verify(vmsg)
        note(f"  measured: {v}")

        problems = []
        if want_bbox and "BBOX" in v:
            got = [float(x) for x in v["BBOX"].split(",")]
            for ax, g, w in zip("XYZ", got, want_bbox):
                if abs(g - w) > a.tol:
                    problems.append(f"{ax} is {g:.3f}in, expected {w:.3f}in")
        if a.expect_volume and "VOLUME" in v:
            gv = float(v["VOLUME"])
            if abs(gv - a.expect_volume) > 0.75:
                problems.append(
                    f"volume is {gv:.2f} in^3, expected {a.expect_volume:.2f} in^3 - "
                    f"members overlap (too much) or are missing (too little)")
        if v.get("BODIES") and int(v["BODIES"]) != 1:
            problems.append(f"{v['BODIES']} bodies, expected 1 - join every member")

        if problems:
            msg = "Geometry is wrong:\n" + "\n".join(f"- {p}" for p in problems)
            note("  " + msg.replace("\n", "\n  "))
            prev_err, prev_code = msg, code
            continue

        # success - capture the view
        # Fit twice with doEvents between: the first fit can run before the
        # new geometry is in the display list, giving a zoomed-in screenshot.
        m.run_script('''import adsk.core
def run(_context: str):
    app = adsk.core.Application.get()
    vp = app.activeViewport
    c = vp.camera
    c.viewOrientation = adsk.core.ViewOrientations.IsoTopRightViewOrientation
    c.isFitView = True
    vp.camera = c
    adsk.doEvents()
    vp.refresh()
    vp.fit()
    adsk.doEvents()
    vp.fit()
    print("fitted")
''')
        r = m._post({"method": "tools/call", "params": {
            "name": "fusion_mcp_read", "arguments": {"queryType": "screenshot"}}})
        shot = exports / f"{a.out_name}-fusion.png"
        for c in r.get("result", {}).get("content", []):
            if c.get("type") == "image":
                shot.write_bytes(base64.b64decode(c["data"]))
                note(f"  screenshot: {shot}")
        note(f"  ✅ SUCCESS on attempt {attempt}")
        return 0

    note(f"\n❌ no valid model after {a.max_attempts} attempts")
    return 1


if __name__ == "__main__":
    sys.exit(main())
