#!/usr/bin/env python3
"""Iterative MLX model -> ezdxf -> geometric + professional drawing gates."""

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

API = "http://127.0.0.1:1234/v1/chat/completions"

SYSTEM = r'''You write standalone Python using ezdxf to create a professional product drawing.
Return exactly one complete Python code block and no prose. Use inches and DXF R2010.
Create and use these layers: OUTLINE, HIDDEN, CENTER, DIMENSIONS, TEXT, TITLEBLOCK.
Place non-overlapping front, top, right, and isometric views. Use true ezdxf
DIMENSION entities with render(), not text pretending to be dimensions. Dimension
every critical interface from the job. Add centerlines/centermarks for holes and
axes. Add a bordered title block containing job ID, `REV <revision>`, material,
manufacturing process, `UNITS: INCH`, `DO NOT SCALE`, and `TOLERANCE` notes.
If status is READY_PROTOTYPE, include a prominent `PROTOTYPE - NOT FOR FABRICATION`
watermark. Include a sourced cut list/BOM; never invent catalog part numbers.
Write only to OUTPUT_PATH. No network, UI, message boxes, or swallowed exceptions.'''


def ask(model, prompt):
    payload = json.dumps({
        "model": model, "temperature": 0.15, "max_tokens": 8000,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(API, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as response:
        return json.load(response)["choices"][0]["message"]["content"]


def code_of(text):
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    return (match.group(1) if match else text).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--spec", help="approved/augmented spec; defaults to job spec")
    parser.add_argument("--fusion-root", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out-name", required=True)
    parser.add_argument("--max-attempts", type=int, default=12)
    args = parser.parse_args()

    job_path = pathlib.Path(args.job).resolve()
    job = json.loads(job_path.read_text())
    root = pathlib.Path(args.fusion_root).resolve()
    spec_path = pathlib.Path(args.spec).resolve() if args.spec else (root / job["spec_path"]).resolve()
    spec = spec_path.read_text()
    output = root / "exports" / f"{args.out_name}.dxf"
    script = root / "scripts" / f"{args.out_name}_drawing.py"
    output.parent.mkdir(exist_ok=True); script.parent.mkdir(exist_ok=True)
    # .venv-cq, not .venv-cad -- see bridge/cad_loop.py. The 3.9 venv was built on
    # Xcode's interpreter and does not survive a move to a new Mac. Retired 2026-09-02.
    venv_python = root / ".venv-cq" / "bin" / "python"
    geometric_validator = root / job["validators"]["drawing"]
    quality_validator = pathlib.Path(__file__).resolve().parent / "drawing_quality.py"
    task = (f"OUTPUT_PATH = {str(output)!r}\n\nJOB JSON:\n{json.dumps(job, indent=2)}"
            f"\n\nPRODUCT SPEC:\n{spec}")
    previous_code = previous_error = None
    best = None

    for attempt in range(1, args.max_attempts + 1):
        prompt = task if previous_error is None else (
            f"{task}\n\nPREVIOUS SCRIPT:\n{previous_code}\n\nVALIDATION FAILURES:\n"
            f"{previous_error}\nFix those exact failures and return the full script.")
        generated = code_of(ask(args.model, prompt))
        if not generated:
            previous_error = "No code returned"; previous_code = ""; continue
        script.write_text(generated)
        if output.exists():
            output.unlink()
        run = subprocess.run([str(venv_python), str(script)], capture_output=True,
                             text=True, timeout=600)
        failures = []
        if run.returncode:
            failures.append((run.stderr or run.stdout)[-4000:])
        elif not output.exists():
            failures.append("Script exited successfully but created no DXF")
        else:
            for validator in (geometric_validator, quality_validator):
                check = subprocess.run([str(venv_python), str(validator),
                                        str(output)] if validator == geometric_validator else
                                       [str(venv_python), str(validator), str(job_path), str(output)],
                                       capture_output=True, text=True)
                if check.returncode:
                    failures.append(check.stderr or check.stdout)
        if not failures:
            best_dxf = output.with_name(output.stem + "-best.dxf")
            best_dxf.write_bytes(output.read_bytes())
            print(f"DRAWING PASS attempt={attempt} output={output}")
            return 0
        previous_code = generated
        previous_error = "\n".join(failures)[-7000:]
        score = previous_error.count("\n")
        if best is None or score < best[0]:
            best = (score, output.read_bytes() if output.exists() else None, generated)
        print(f"attempt {attempt}: drawing validation failed", flush=True)
        time.sleep(1)

    if best and best[1]:
        output.with_name(output.stem + "-best.dxf").write_bytes(best[1])
        script.with_name(script.stem + "-best.py").write_text(best[2])
    print("DRAWING FAILED: no attempt passed both geometric and professional gates", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
