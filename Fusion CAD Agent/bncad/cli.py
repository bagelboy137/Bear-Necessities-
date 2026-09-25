#!/usr/bin/env python3
"""bncad command line.

    python -m bncad doctor              what works right now
    python -m bncad models              every model on every live provider
    python -m bncad specs               known part specs
    python -m bncad build <spec>        generate, validate, export
    python -m bncad check <spec> <step> validate an existing STEP
    python -m bncad reference <spec> <step>
                                        adopt a hand-built STEP as the spec's
                                        reference, and print its measurements
    python -m bncad fusion <step>       import into the live Fusion session
    python -m bncad bench               score models against the spec library
    python -m bncad selftest            every module demo, no model needed
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SPEC_DIR = pathlib.Path(os.environ.get("BN_SPEC_DIR", ROOT / "specs" / "parts"))
OUT_DIR = pathlib.Path(os.environ.get("BN_OUT_DIR", ROOT / "exports" / "bncad"))


def _venv_python():
    """The interpreter that has cadquery. Falls back to the current one."""
    cand = ROOT / ".venv-cq" / "bin" / "python"
    return str(cand) if cand.exists() else sys.executable


def _has_cadquery():
    try:
        import cadquery  # noqa: F401
        return True
    except Exception:
        return False


# -- commands -------------------------------------------------------------

def cmd_doctor(a):
    from . import provider, fusion, loop
    rows, blocking = [], []

    ok = _has_cadquery()
    rows.append(("cadquery", ok, "%s on python %s" % (
        __import__("cadquery").__version__ if ok else "-",
        ".".join(map(str, sys.version_info[:3])))))
    if not ok:
        blocking.append(
            "cadquery is not importable. Run through %s, or build that venv with "
            "uv (which fetches the interpreter too, since a fresh Mac has no "
            "system python3.12): uv venv --python 3.12 '%s' && uv pip install "
            "--python '%s' cadquery"
            % (_venv_python(), ROOT / ".venv-cq", _venv_python()))

    sb = loop.sandbox_backend()
    want = "sandbox-exec" if sys.platform == "darwin" else "bwrap (apt install bubblewrap)"
    rows.append(("sandbox", bool(sb), sb or "%s not found" % want))
    if not sb:
        blocking.append("%s is missing; generated code would run "
                        "unconfined. Refusing to treat that as fine." % want)

    provs = provider.discover()
    rows.append(("providers", bool(provs),
                 ", ".join("%s (%d models)" % (p.name, len(p.models()))
                           for p in provs) or "none answering"))
    if not provs:
        blocking.append("No local model server answering. Start LM Studio "
                        "(port 1234) or Ollama (port 11434).")

    freachable, fdetail = fusion.available()
    rows.append(("Fusion app", fusion.installed(), str(fusion.APP)))
    rows.append(("Fusion MCP", freachable,
                 fdetail if freachable else "not running (optional - "
                 "headless builds do not need it)"))

    n = len(list(SPEC_DIR.glob("*.json"))) if SPEC_DIR.exists() else 0
    rows.append(("part specs", n > 0, "%d in %s" % (n, SPEC_DIR)))

    print("bncad doctor")
    for name, good, detail in rows:
        print("  [%s] %-12s %s" % ("OK  " if good else "FAIL", name, detail))
    if blocking:
        print("\nBLOCKED:")
        for b in blocking:
            print("  - %s" % b)
        return 1
    print("\nReady. Headless builds can run now; Fusion handoff needs the app open.")
    return 0


def cmd_models(a):
    from . import provider
    provs = provider.discover()
    if not provs:
        print("No local provider is answering.")
        return 1
    for p in provs:
        print("%s  (%s)" % (p.name, p.base_url))
        for m in p.models():
            print("    %s" % m)
    return 0


def cmd_specs(a):
    from .spec import PartSpec
    if not SPEC_DIR.exists():
        print("No spec directory at %s" % SPEC_DIR)
        return 1
    for p in sorted(SPEC_DIR.glob("*.json")):
        try:
            s = PartSpec.load(p)
            print("%-10s %-34s %s" % (s.id, s.name, p.name))
        except Exception as e:
            print("%-10s %-34s %s" % ("BROKEN", str(e)[:34], p.name))
    return 0


def _resolve_spec(token):
    from .spec import PartSpec
    p = pathlib.Path(token)
    if p.exists():
        return PartSpec.load(p)
    for cand in (SPEC_DIR / token, SPEC_DIR / ("%s.json" % token)):
        if cand.exists():
            return PartSpec.load(cand)
    known = ", ".join(sorted(x.stem for x in SPEC_DIR.glob("*.json")))
    raise SystemExit("No spec %r. Known: %s" % (token, known))


def cmd_build(a):
    from . import provider, loop
    spec = _resolve_spec(a.spec)
    p, model = provider.resolve(a.model)
    outdir = pathlib.Path(a.out) if a.out else OUT_DIR
    print("building %s (%s) with %s/%s" % (spec.id, spec.name, p.name, model))
    r = loop.build(spec, p, model, outdir, max_attempts=a.attempts,
                   temperature=a.temperature, python=_venv_python(),
                   timeout=a.timeout, keep_workdir=a.keep)
    if r["ok"]:
        print("\nPASS in %d attempt(s): %s" % (r["attempt"], r["report"]))
        print("  %s/%s.step" % (outdir, spec.id))
        if a.fusion:
            return _fusion_handoff(outdir / ("%s.step" % spec.id), r["measured"],
                                   scale=spec.scale)
        return 0
    print("\nFAIL after %d attempt(s); best had %s error(s)"
          % (len(r["attempts"]), r["best_errors"]))
    return 1


def cmd_check(a):
    from .spec import measure
    spec = _resolve_spec(a.spec)
    # STEP is millimetres on disk; the spec is in its own units.
    #
    # Pass the sibling STL when there is one, or the watertightness gate quietly
    # does nothing on the single command a human uses to bless an existing file.
    step = pathlib.Path(a.step)
    stl = step.with_suffix(".stl")
    m = measure(step, stl if stl.exists() else None,
                scale=1.0 if a.raw else spec.scale)
    if not stl.exists():
        print("note: no %s beside it, so the mesh was not checked" % stl.name)
    errs = spec.check(m)
    if errs:
        print("FAIL - %d problem(s):" % len(errs))
        for i, e in enumerate(errs, 1):
            print("  %d. %s" % (i, e))
        return 1
    print("PASS - %s" % spec.report(m))
    return 0


def cmd_reference(a):
    """Turn a hand-built authored STEP into this spec's reference solid.

    Adding a part is the framework's main extension point, and doing it by hand
    walked straight back into the units bug: a hand-exported STEP carries the
    spec's numbers but declares millimetres, so measuring it as a delivery
    divided everything by 25.4. This does the conversion and prints numbers that
    can be pasted into `checks` as-is.
    """
    from . import spec as spec_mod
    spec = _resolve_spec(a.spec)
    refdir = pathlib.Path(a.out) if a.out else (ROOT / "specs" / "reference")
    refdir.mkdir(parents=True, exist_ok=True)

    authored = pathlib.Path(a.step)
    dest_step = refdir / ("%s.step" % spec.id)
    dest_stl = refdir / ("%s.stl" % spec.id)
    if authored.resolve() == dest_step.resolve():
        raise SystemExit(
            "Refusing to convert %s onto itself - it would be scaled by %g every "
            "time this runs. Export the hand-built solid somewhere else first."
            % (dest_step, spec.scale))

    spec_mod.to_delivery(authored, dest_step, dest_stl, spec.scale)
    m = spec_mod.measure(dest_step, dest_stl, scale=spec.scale)
    print("wrote %s (+ .stl), in real millimetres" % dest_step)
    print("measured back in %s:\n" % spec.units)
    # Group holes by diameter - that is the shape a spec's `holes` takes, and
    # emitting one entry per hole makes the output useless to paste.
    #
    # `at` is included deliberately. Without it no spec written through this
    # command would ever carry a position check, and a bolt pattern in the wrong
    # place passes every other gate untouched.
    grouped = []
    for h in m["holes"]:
        at = [round(v, 4) for v in spec_mod._in_plane(h)]
        for g in grouped:
            if abs(g["d"] - h["d"]) <= 1e-4:
                g["count"] += 1
                g["at"].append(at)
                break
        else:
            grouped.append({"d": h["d"], "count": 1, "at": [at]})
    # `through` only means anything where the material is uniform along the
    # hole's axis, so offer it for a plate and an explicit depth otherwise.
    uniform = sorted(m["bbox"])[0] < 0.5 * sorted(m["bbox"])[1]
    for g in grouped:
        if uniform:
            g["through"] = True
        else:
            g["depth"] = round(
                min(h["depth"] for h in m["holes"]
                    if abs(h["d"] - g["d"]) <= 1e-4), 4)
    print(json.dumps({
        "bbox": [round(v, 5) for v in m["bbox"]],
        "volume": round(m["volume"], 5),
        "solids": m["solids"],
        "valid": m["valid"],
        "holes": grouped,
        "holes_exact": True,
    }, indent=2))
    errs = spec.check(m)
    if errs:
        print("\nThe spec does NOT yet match this solid - %d difference(s):"
              % len(errs))
        for i, e in enumerate(errs, 1):
            print("  %d. %s" % (i, e))
        print("\nPaste the measurements above into the spec's `checks`.")
        return 1
    print("\nThe spec already matches this reference solid.")
    return 0


def _fusion_handoff(step, measured=None, scale=25.4):
    from . import fusion, spec as spec_mod
    ok, detail = fusion.available()
    if not ok:
        print("Fusion is not reachable: %s" % detail)
        print("Open Fusion, sign in, and tick Preferences > General > API > "
              "Fusion MCP Server. The STEP is already on disk and will import "
              "by hand.")
        return 2
    if measured is None:
        measured = spec_mod.measure(step, scale=scale)
    errs, f = fusion.cross_check(step, measured, scale=scale)
    print("Fusion imported it: %d body/bodies, bbox %.4f x %.4f x %.4f in, "
          "volume %.4f in^3" % (f["bodies"], f["bbox_in"][0], f["bbox_in"][1],
                                f["bbox_in"][2], f["volume_in3"]))
    if errs:
        print("DISAGREEMENT between CadQuery and Fusion:")
        for e in errs:
            print("  - %s" % e)
        return 1
    print("Both kernels agree on the geometry.")
    return 0


def cmd_fusion(a):
    from .spec import MM_PER_UNIT
    return _fusion_handoff(a.step, scale=MM_PER_UNIT[a.units])


def _slug(model_id):
    """A model id that is safe as a directory name.

    Only "/" was replaced before, so Ollama's "qwen3:8b" produced a directory
    literally named `qwen3:8b` - legal on this Mac, but a colon is not portable
    and makes every shell path that touches it need quoting.
    """
    return "".join(c if (c.isalnum() or c in "-._") else "_" for c in model_id)


def cmd_bench(a):
    from . import provider, loop
    from .spec import load_all
    specs = load_all(SPEC_DIR)
    if a.spec:
        specs = [s for s in specs if s.id in a.spec]
    models = a.model or []
    if not models and os.environ.get("BN_MODEL"):
        # `build.sh parts` sets BN_MODEL to the configured reviewer and expects
        # it honoured. Without this, a plain `bench` swept every model on every
        # provider instead - hours of work, and not what was asked for.
        models = [os.environ["BN_MODEL"]]
    if not models:
        provs = provider.discover()
        models = [m for p in provs for m in p.models()
                  if "embed" not in m and "-vl-" not in m]
        print("no --model and no BN_MODEL: benchmarking all %d discovered "
              "model(s)" % len(models))
    outdir = pathlib.Path(a.out) if a.out else (OUT_DIR / "bench")
    outdir.mkdir(parents=True, exist_ok=True)

    board = []
    for model in models:
        try:
            p, mid = provider.resolve(model)
        except Exception as e:
            print("skip %s: %s" % (model, e))
            continue
        for s in specs:
            for run in range(1, a.repeat + 1):
                label = s.id if a.repeat == 1 else "%s #%d" % (s.id, run)
                print("\n=== %s x %s ===" % (mid, label))
                t0 = time.time()
                # Each repeat needs its own directory, or run 2 overwrites run 1
                # and the variance the repeat exists to expose is invisible.
                dest = outdir / _slug(mid)
                if a.repeat > 1:
                    dest = dest / ("run%d" % run)
                row = {"model": mid, "spec": s.id, "run": run}
                try:
                    r = loop.build(s, p, mid, dest, max_attempts=a.attempts,
                                   python=_venv_python(), timeout=a.timeout)
                except loop.HarnessFault:
                    # The environment is broken, not the model. Scoring this as
                    # a model failure would put a false result in the scoreboard
                    # and hide the real problem.
                    raise
                except loop.BuildInProgress:
                    # Never score a part the bench did not actually build. If
                    # something else is writing into this directory the whole
                    # scoreboard is unreliable, so stop rather than record a
                    # phantom failure against the model.
                    raise
                except Exception as e:
                    print("  crashed: %s" % e)
                    row.update(ok=False, error=str(e)[:200])
                else:
                    row.update(ok=r["ok"], attempts=len(r["attempts"]),
                               best_errors=r["best_errors"])
                row["seconds"] = round(time.time() - t0, 1)
                board.append(row)
                (outdir / "scoreboard.json").write_text(json.dumps(board, indent=2))

    print("\n%-30s %-22s %-5s %-6s %s"
          % ("MODEL", "PART", "PASS", "TRIES", "SECONDS"))
    for row in board:
        name = row["spec"] if a.repeat == 1 else "%s #%d" % (row["spec"], row["run"])
        print("%-30s %-22s %-5s %-6s %s"
              % (row["model"][:30], name, "yes" if row["ok"] else "no",
                 row.get("attempts", "-"), row.get("seconds", "-")))
    passed = sum(1 for r in board if r["ok"])
    if a.repeat > 1:
        # A part that passes 1 run in 2 is neither "works" nor "broken", and
        # reporting either is misleading. C-02-U did exactly that on the 7B.
        print("\nper-part pass rate over %d run(s):" % a.repeat)
        seen = []
        for row in board:
            key = (row["model"], row["spec"])
            if key in seen:
                continue
            seen.append(key)
            runs = [r for r in board if (r["model"], r["spec"]) == key]
            wins = sum(1 for r in runs if r["ok"])
            flag = "" if wins in (0, len(runs)) else "   <- marginal"
            print("  %-30s %-22s %d/%d%s"
                  % (key[0][:30], key[1], wins, len(runs), flag))
    if not board:
        # "0/0 passed" satisfied `passed == len(board)` and exited 0, so a
        # mistyped --spec or an empty spec directory reported success having
        # benchmarked nothing at all. Benching nothing is a failure.
        print("\nNothing was benchmarked - no spec matched and/or no model "
              "resolved. Check --spec against `bncad specs` and --model against "
              "`bncad models`.")
        return 1
    print("\n%d/%d runs passed. Scoreboard: %s"
          % (passed, len(board), outdir / "scoreboard.json"))
    # A partial pass is still a failure for a gate to act on.
    return 0 if passed == len(board) else 1


def cmd_selftest(a):
    mods = ["provider", "spec", "loop", "fusion"]
    fails = []
    for m in mods:
        r = subprocess.run([_venv_python(), str(HERE / ("%s.py" % m))],
                           capture_output=True, text=True)
        status = "ok" if r.returncode == 0 else "FAIL"
        print("  [%s] %s %s" % (status, m, (r.stdout or r.stderr).strip().splitlines()[-1]
                                if (r.stdout or r.stderr).strip() else ""))
        if r.returncode != 0:
            fails.append((m, (r.stderr or r.stdout).strip()))
    suite = HERE / "tests" / "test_bncad.py"
    if suite.exists():
        r = subprocess.run([_venv_python(), str(suite)], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode != 0:
            fails.append(("suite", r.stderr))
    if fails:
        print("\nFAILURES:")
        for name, detail in fails:
            print("--- %s ---\n%s" % (name, detail[-1500:]))
        return 1
    print("\nAll self-tests pass.")
    return 0


# -- wiring ---------------------------------------------------------------

def main(argv=None):
    # Bench runs are watched through a log file; block buffering makes a working
    # run look hung.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="bncad", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    sub.add_parser("models").set_defaults(fn=cmd_models)
    sub.add_parser("specs").set_defaults(fn=cmd_specs)
    sub.add_parser("selftest").set_defaults(fn=cmd_selftest)

    b = sub.add_parser("build")
    b.add_argument("spec")
    b.add_argument("--model", default=None,
                   help="model id, or provider/model. Default: BN_MODEL, else first available")
    b.add_argument("--attempts", type=int, default=8)
    b.add_argument("--temperature", type=float, default=0.15)
    b.add_argument("--timeout", type=int, default=900)
    b.add_argument("--out", default=None)
    b.add_argument("--fusion", action="store_true",
                   help="after a pass, import into the live Fusion session")
    b.add_argument("--keep", action="store_true", help="keep the scratch dir")
    b.set_defaults(fn=cmd_build)

    c = sub.add_parser("check")
    c.add_argument("spec")
    c.add_argument("step")
    c.add_argument("--raw", action="store_true",
                   help="the STEP is already numbered in the spec's units "
                        "(an authored file, not a millimetre delivery)")
    c.set_defaults(fn=cmd_check)

    r = sub.add_parser("reference",
                       help="convert a hand-built STEP into a spec's reference "
                            "solid and print paste-ready measurements")
    r.add_argument("spec")
    r.add_argument("step", help="the authored STEP, numbered in the spec's units")
    r.add_argument("--out", default=None)
    r.set_defaults(fn=cmd_reference)

    f = sub.add_parser("fusion")
    f.add_argument("step")
    f.add_argument("--units", default="in", choices=sorted(["in", "mm", "cm", "m"]),
                   help="units the STEP's geometry represents (default: in)")
    f.set_defaults(fn=cmd_fusion)

    n = sub.add_parser("bench")
    n.add_argument("--model", action="append")
    n.add_argument("--spec", action="append")
    n.add_argument("--attempts", type=int, default=6)
    n.add_argument("--repeat", type=int, default=1,
                   help="build each part N times - one pass cannot tell a robust "
                        "loop from a lucky one")
    n.add_argument("--timeout", type=int, default=900)
    n.add_argument("--out", default=None)
    n.set_defaults(fn=cmd_bench)

    a = ap.parse_args(argv)
    if not getattr(a, "fn", None):
        ap.print_help()
        return 0
    from .provider import ProviderError
    from .spec import SpecError
    from .loop import BuildInProgress, HarnessFault
    try:
        return a.fn(a)
    except HarnessFault as e:
        print("harness fault: %s" % e, file=sys.stderr)
        return 2
    except BuildInProgress as e:
        # Distinct exit code: a scheduled run that collided with a manual one
        # has not failed, it has declined to race, and a wrapper should be able
        # to tell those apart without parsing the message.
        print("busy: %s" % e, file=sys.stderr)
        return 3
    except (ProviderError, SpecError) as e:
        # These carry the roster or the offending field already. A stack trace
        # over the top of that just buries the one line worth reading.
        print("error: %s" % e, file=sys.stderr)
        return 2
    except OSError as e:
        # An unwritable or missing output directory is a configuration problem,
        # not a crash. A scheduled run's log should say which path and why, in
        # one line, rather than a traceback ending in PermissionError.
        where = getattr(e, "filename", None)
        print("error: cannot use the filesystem here%s: %s"
              % (" (%s)" % where if where else "", e.strerror or e),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
