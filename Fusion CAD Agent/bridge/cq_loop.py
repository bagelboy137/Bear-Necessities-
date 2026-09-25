#!/usr/bin/env python3
"""
cq_loop.py — closed feedback loop for 3D solid CAD via CadQuery.

Same shape as cad_loop.py (the 2D/ezdxf loop) but produces real solids and
validates them numerically: exact bounding box, exact volume, solid count.
That numeric feedback ("volume is 480.0, expected 232.0, members overlap") is
far more actionable than anything a 2D drawing check can say.

    python3 bridge/cq_loop.py --spec specs/overland-base-frame.md \
        --model qwen2.5-coder-7b-instruct --max-attempts 15
"""
import argparse, json, pathlib, re, subprocess, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
CQ_PY = ROOT / ".venv-cq" / "bin" / "python"
API = "http://localhost:1234/v1/chat/completions"

SYSTEM = """You write Python that uses the `cadquery` library to build 3D solid CAD models.

HARD RULES
1. Output ONE complete Python script in a single ```python code block. No prose.
2. Runs start to finish with no input and no network.
3. Units are INCHES throughout. Put every dimension in named constants at the top.
4. Import as: `import cadquery as cq` and `from cadquery import exporters`.
5. Export with: exporters.export(result, STEP_PATH) and exporters.export(result, STL_PATH)
   using the exact paths given in the task.
6. Use only `cadquery` and the standard library.
7. Do not call sys.exit(). Do not swallow exceptions.

BUILDING BOX MEMBERS - USE THIS EXACT PATTERN
`box(l, w, h, centered=False)` puts the box corner at the origin, then translate
it into place. This is the reliable way to position rectangular members:

    def member(l, w, h, x, y, z):
        return cq.Workplane("XY").box(l, w, h, centered=False).translate((x, y, z))

    result = member(...)                 # first member
    result = result.union(member(...))   # union each additional member

Union ALL members into ONE solid. Members must TOUCH so the result is connected.

MULTI-MEMBER FRAMES - USE A MEMBER TABLE, NOT AD-HOC PLACEMENT
Never eyeball positions. Write an explicit table of (length_x, length_y,
length_z, x, y, z) with `centered=False`, so each member's corner is placed at
an absolute coordinate. Then loop and union. `centered=False` means the box
occupies x..x+length_x, so a member at x=W-P ends exactly at W.

    W, D, H, P = 24.0, 20.0, 18.0, 1.0

    MEMBERS = []
    for x in (0, W - P):                      # 4 vertical posts
        for y in (0, D - P):
            MEMBERS.append((P, P, H, x, y, 0))
    for y in (0, D - P):                      # 4 width rails, along X, between posts
        for z in (0, H - P):
            MEMBERS.append((W - 2*P, P, P, P, y, z))
    for x in (0, W - P):                      # 4 depth rails, along Y, between posts
        for z in (0, H - P):
            MEMBERS.append((P, D - 2*P, P, x, P, z))

    result = None
    for (lx, ly, lz, x, y, z) in MEMBERS:
        m = cq.Workplane("XY").box(lx, ly, lz, centered=False).translate((x, y, z))
        result = m if result is None else result.union(m)

Check your own arithmetic: the union must span exactly 0..W, 0..D, 0..H.

FLAT PLATE WITH ROUNDED CORNERS AND HOLES - USE THIS EXACT PATTERN
Do NOT invent Workplane keyword arguments. There is no centerX, centerY or
centerAt. This is the whole vocabulary you need:

    L, W, T, R = 4.0, 1.5, 0.25, 0.25

    plate = (cq.Workplane("XY")
             .box(L, W, T, centered=(True, True, False))   # centred in X and Y, sits on Z=0
             .edges("|Z")                                   # the 4 vertical corner edges
             .fillet(R))

    # Holes at explicit (x, y) positions measured from the plate centre:
    plate = (plate.faces(">Z").workplane()
             .pushPoints([(-1.0, 0.0), (1.0, 0.0)])          # 2 holes 2.0" apart
             .hole(0.281))                                   # through hole, diameter

    plate = (plate.faces(">Z").workplane()
             .pushPoints([(1.5, 0.0)])
             .hole(0.266))

`.hole(d)` goes all the way through and takes a DIAMETER. `.pushPoints()` takes
coordinates relative to the workplane centre. Chain `.faces(">Z").workplane()`
again before each new set of holes.

If you are given validation errors, fix THOSE specific numbers. Do not start over."""


def ask(prompt, model, max_tokens=6000, timeout=1800, temperature=0.15):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "max_tokens": max_tokens, "temperature": temperature,
    }).encode()
    req = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)["choices"][0]["message"]["content"]


def extract_code(t):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", t, re.S)
    return (m.group(1) if m else t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out-name", default="prototype-3d")
    ap.add_argument("--max-attempts", type=int, default=15)
    ap.add_argument("--validator", default="cq_validate.py")
    a = ap.parse_args()

    spec = pathlib.Path(a.spec).read_text()
    exports = ROOT / "exports"; exports.mkdir(exist_ok=True)
    logs = ROOT / "bridge" / "logs"; logs.mkdir(parents=True, exist_ok=True)

    step = exports / f"{a.out_name}.step"
    stl = exports / f"{a.out_name}.stl"
    script = ROOT / "scripts" / f"{a.out_name}_gen.py"
    best_step = exports / f"{a.out_name}-best.step"
    best_py = script.with_name(script.stem + "-best.py")
    log = logs / f"{a.out_name}.log"

    def note(s):
        print(s, flush=True)
        with log.open("a") as f:
            f.write(s + "\n")

    note(f"\n{'='*70}\nRUN {time.strftime('%Y-%m-%d %H:%M:%S')} model={a.model} backend=cadquery\n{'='*70}")

    task = (f"Build a 3D solid model of this part with CadQuery.\n\n"
            f"STEP_PATH = {str(step)!r}\nSTL_PATH = {str(stl)!r}\n\n"
            f"--- SPEC ---\n{spec}\n--- END SPEC ---\n\n"
            f"Build exactly what the spec describes. Every stated dimension must be exact.")

    prev_err, prev_code, last_code, stuck, temp = None, "", None, 0, 0.15
    best = {"errors": 10**9}

    for attempt in range(1, a.max_attempts + 1):
        note(f"\n--- attempt {attempt}/{a.max_attempts} ---")
        hint = ""
        if stuck:
            hint = ("\n\nYou returned the SAME script as last time and it still fails. "
                    "Do not repeat it - change your approach to the failing numbers.")
        prompt = task if prev_err is None else (
            f"{task}\n\n--- YOUR PREVIOUS SCRIPT ---\n{prev_code}\n"
            f"--- IT FAILED WITH ---\n{prev_err}\n\nFix those specific problems.{hint}")

        t0 = time.time()
        try:
            raw = ask(prompt, a.model, temperature=temp)
        except Exception as e:
            note(f"  model call failed: {e}"); time.sleep(5); continue
        code = extract_code(raw)
        if not code:
            prev_err, prev_code = "You returned no code block.", ""; continue

        if code == last_code:
            stuck += 1; temp = min(0.15 + 0.25 * stuck, 0.9)
            note(f"  identical output (stuck x{stuck}) -> temperature {temp:.2f}")
        else:
            stuck = 0
        last_code = code

        script.write_text(code)
        note(f"  generated {len(code)} chars in {time.time()-t0:.0f}s")

        for f in (step, stl):
            if f.exists():
                f.unlink()

        run = subprocess.run([str(CQ_PY), str(script)], capture_output=True,
                             text=True, timeout=900)
        if run.returncode != 0:
            tail = "\n".join((run.stderr or run.stdout).strip().splitlines()[-12:])
            note(f"  FAILED rc={run.returncode}\n{tail}")
            prev_err, prev_code = tail, code
            continue
        if not step.exists():
            prev_err, prev_code = f"Script exited 0 but wrote no STEP at {step}.", code
            note("  no STEP written"); continue

        chk = subprocess.run([str(CQ_PY), str(ROOT / "bridge" / a.validator), str(step)],
                             capture_output=True, text=True)
        if chk.returncode != 0:
            msg = (chk.stderr or chk.stdout).strip()
            note("  " + msg.replace("\n", "\n  "))
            n = len([l for l in msg.splitlines() if l.strip()[:2].rstrip('.').isdigit()])
            if max(n, 1) < best["errors"]:
                best["errors"] = max(n, 1)
                best_step.write_bytes(step.read_bytes())
                best_py.write_text(code)
                note(f"  ** new best: {best['errors']} error(s)")
            prev_err, prev_code = msg, code
            continue

        note(f"  ✅ SUCCESS on attempt {attempt} — {chk.stdout.strip()}")
        best_step.write_bytes(step.read_bytes()); best_py.write_text(code)
        return 0

    note(f"\n❌ no clean model after {a.max_attempts} attempts")
    if best_step.exists():
        note(f"Best had {best['errors']} error(s), kept at {best_step.name}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
