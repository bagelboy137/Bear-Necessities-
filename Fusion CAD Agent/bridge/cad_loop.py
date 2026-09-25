#!/usr/bin/env python3
"""
cad_loop.py — the closed feedback loop.

Sends a part spec to the LOCAL model, runs the Python/ezdxf script it writes,
and on failure feeds the traceback back for another attempt. Stops when the
script runs and produces a valid DXF, or after --max-attempts.

This is the piece the project has been designing toward: the model can SEE its
own errors. Everything runs headless, so it works unattended.

    python3 bridge/cad_loop.py --spec specs/overland-base-frame.md \
        --model qwen/qwen2.5-coder-14b --max-attempts 8
"""
import argparse, json, pathlib, re, subprocess, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
# .venv-cq, not .venv-cad: the old 3.9 venv was built on *Xcode's* interpreter
# (/Applications/Xcode.app/...), which does not exist on a machine with only the
# Command Line Tools -- so it arrives on a new Mac as a dead symlink farm that
# fails at import and reads like a missing package. .venv-cq is a superset
# (ezdxf, matplotlib, numpy, Pillow + cadquery) and is the one venv the setup
# checklist rebuilds. Retired 2026-09-02.
VENV_PY = ROOT / ".venv-cq" / "bin" / "python"
API = "http://localhost:1234/v1/chat/completions"

SYSTEM = """You write Python that uses the `ezdxf` library to produce 2D CAD drawings.

HARD RULES
1. Output ONE complete Python script in a single ```python code block. No prose.
2. The script must run start to finish with no input and no network.
3. Write the DXF to the exact path given in the task as OUTPUT_PATH.
4. Use only `ezdxf` and the standard library. No other third-party imports.
5. Units are INCHES. Set the header var $INSUNITS to 1 (inches).
6. Put every dimension in named constants at the top.
7. Use `doc = ezdxf.new("R2010", setup=True)` and `msp = doc.modelspace()`.
8. Draw with msp.add_lwpolyline, msp.add_line, msp.add_circle, msp.add_text.
9. For text use: msp.add_text("s", height=H).set_placement((x, y))
   Do NOT pass dxfattribs={"insert": ...} to add_text.
10. Call doc.saveas(OUTPUT_PATH) at the end.
11. Do not call sys.exit(). Do not wrap everything in try/except that swallows errors.

LAYING OUT MULTIPLE VIEWS - USE THIS EXACT PATTERN
Views MUST NOT overlap. Never draw two views at the same origin. Define one
offset per view and add it to EVERY point in that view, via a helper:

    def place(points, dx, dy):
        return [(x + dx, y + dy) for x, y in points]

    FRONT_DX, FRONT_DY = 0.0, 0.0
    TOP_DX,   TOP_DY   = 0.0, 30.0      # above the front view
    RIGHT_DX, RIGHT_DY = 34.0, 0.0      # to the right of the front view

    msp.add_lwpolyline(place([(0,0), (W,0), (W,H), (0,H)], FRONT_DX, FRONT_DY), close=True)
    msp.add_lwpolyline(place([(0,0), (W,0), (W,D), (0,D)], TOP_DX,   TOP_DY),   close=True)
    msp.add_lwpolyline(place([(0,0), (D,0), (D,H), (0,H)], RIGHT_DX, RIGHT_DY), close=True)

Offset the view LABELS by the same amounts. The right view's width is DEPTH.

If you are given errors from your previous attempt, fix THOSE specific errors.
Do not rewrite the whole script from scratch."""


def ask(prompt, model, max_tokens=6000, timeout=1800, temperature=0.15):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()
    req = urllib.request.Request(API, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"]


def extract_code(text):
    m = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--out-name", default="prototype")
    ap.add_argument("--max-attempts", type=int, default=8)
    a = ap.parse_args()

    spec = pathlib.Path(a.spec).read_text()
    workdir = ROOT / "exports"
    workdir.mkdir(exist_ok=True)
    logdir = ROOT / "bridge" / "logs"
    logdir.mkdir(parents=True, exist_ok=True)

    dxf_path = workdir / f"{a.out_name}.dxf"
    script_path = ROOT / "scripts" / f"{a.out_name}_gen.py"
    script_path.parent.mkdir(exist_ok=True)
    log = logdir / f"{a.out_name}.log"

    def note(s):
        print(s, flush=True)
        with log.open("a") as f:
            f.write(s + "\n")

    note(f"\n{'='*70}\nRUN {time.strftime('%Y-%m-%d %H:%M:%S')}  model={a.model}\n{'='*70}")

    task = (f"Produce a 2D CAD drawing for this part.\n\n"
            f"OUTPUT_PATH = {str(dxf_path)!r}\n\n"
            f"--- SPEC ---\n{spec}\n--- END SPEC ---\n\n"
            f"Include three orthographic views (front, top, right) laid out so they "
            f"do not overlap, each labelled, plus a text cut list of all 12 members "
            f"with quantities and cut lengths. Add an overall title.")

    prev_err = None
    prev_code = ""
    last_code = None
    stuck = 0
    temp = 0.15
    # Keep the best attempt so a later worse one cannot destroy it. An
    # all-or-nothing loop that overwrites its own output can end a long run
    # with nothing to show, which is exactly what happened the first time.
    best = {"errors": 10**6, "dxf": None, "code": None, "report": ""}
    best_dxf = dxf_path.with_name(dxf_path.stem + "-best.dxf")
    best_py = script_path.with_name(script_path.stem + "-best.py")

    def remember(n_errors, report):
        if n_errors < best["errors"] and dxf_path.exists():
            best["errors"] = n_errors
            best["report"] = report
            best_dxf.write_bytes(dxf_path.read_bytes())
            best_py.write_text(script_path.read_text())
            note(f"  ** new best: {n_errors} error(s) -> {best_dxf.name}")
    for attempt in range(1, a.max_attempts + 1):
        note(f"\n--- attempt {attempt}/{a.max_attempts} ---")
        prompt = task if prev_err is None else (
            f"{task}\n\n--- YOUR PREVIOUS SCRIPT ---\n{prev_code}\n"
            f"--- IT FAILED WITH ---\n{prev_err}\n\nFix those errors and return the full "
            f"corrected script.{globals().get('_hint', '')}")

        t0 = time.time()
        try:
            raw = ask(prompt, a.model, temperature=temp)
        except Exception as e:
            note(f"  model call failed: {e}")
            time.sleep(5)
            continue
        gen_s = time.time() - t0

        code = extract_code(raw)
        if not code:
            note("  no code returned")
            prev_err, prev_code = "You returned no code block.", ""
            continue

        if code == last_code:
            stuck += 1
            temp = min(0.15 + 0.25 * stuck, 0.9)
            note(f"  identical output to last attempt (stuck x{stuck}) -> raising temperature to {temp:.2f}")
            prompt_hint = ("\n\nYou returned the SAME script as last time and it still "
                           "fails. Do not repeat it. Change your APPROACH to the failing "
                           "point specifically.")
            globals()["_hint"] = prompt_hint
        else:
            stuck = 0
            globals()["_hint"] = ""
        last_code = code

        script_path.write_text(code)
        note(f"  generated {len(code)} chars in {gen_s:.0f}s -> {script_path.name}")

        if dxf_path.exists():
            dxf_path.unlink()

        run = subprocess.run([str(VENV_PY), str(script_path)],
                             capture_output=True, text=True, timeout=300)

        if run.returncode != 0:
            err = (run.stderr or run.stdout).strip()
            tail = "\n".join(err.splitlines()[-15:])
            note(f"  FAILED rc={run.returncode}\n{tail}")
            prev_err, prev_code = tail, code
            continue

        if not dxf_path.exists():
            note("  script ran but wrote no DXF")
            prev_err, prev_code = f"The script exited 0 but no file appeared at {dxf_path}.", code
            continue

        # Validate the drawing is CORRECT, not merely valid. This is the real
        # feedback signal: "it ran" is a low bar that wrong geometry clears.
        check = subprocess.run(
            [str(VENV_PY), str(ROOT / "bridge" / "validate_drawing.py"), str(dxf_path)],
            capture_output=True, text=True)

        if check.returncode != 0:
            msg = (check.stderr or check.stdout).strip()
            note("  " + msg.replace("\n", "\n  "))
            n_err = len([l for l in msg.splitlines() if l.strip()[:2].rstrip('.').isdigit()])
            remember(max(n_err, 1), msg)
            prev_err, prev_code = msg, code
            continue

        note(f"  ✅ SUCCESS on attempt {attempt} — {check.stdout.strip()}")
        note(f"  DXF: {dxf_path}")
        remember(0, "clean")
        return 0

    note(f"\n❌ no fully-clean script after {a.max_attempts} attempts")
    if best["dxf"] or best_dxf.exists():
        note(f"Best attempt had {best['errors']} remaining error(s):")
        note("  " + best["report"].replace("\n", "\n  "))
        note(f"Kept: {best_dxf}")
        note(f"      {best_py}")
    else:
        note("No attempt produced a readable DXF at all.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
