#!/usr/bin/env python3
"""bncad test suite. No model, no Fusion, no network - runs unattended.

Plain asserts and a counting runner, matching the demo() style already used
across this project. Nothing to install.

The negative cases are the point. A checker that only ever passes is worse than
no checker, because it produces a green report over broken geometry - which is
exactly what happened to the native validation report in this project once
already. Every check here is shown rejecting something as well as accepting it.
"""

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from bncad import loop, provider, spec as S       # noqa: E402
from bncad.spec import PartSpec                    # noqa: E402

SPECS = ROOT / "specs" / "parts"
REF = ROOT / "specs" / "reference"
VENV_PY = ROOT / ".venv-cq" / "bin" / "python"

PASSED = []
FAILED = []
SKIPPED = []


class Skip(Exception):
    """Raised by a check that cannot run here, so it is not counted as a pass.

    Two checks used to `return` early when their prerequisite was missing and
    were tallied as passes, which meant a green run on a machine with no venv
    and no model servers verified less than it claimed to.
    """


def check(name):
    def deco(fn):
        try:
            fn()
        except Skip as e:
            SKIPPED.append((name, str(e)))
        except AssertionError as e:
            FAILED.append((name, "assertion: %s" % e))
        except Exception as e:
            FAILED.append((name, "%s: %s" % (type(e).__name__, e)))
        else:
            PASSED.append(name)
        return fn
    return deco


# -- specs are internally coherent ----------------------------------------

@check("every spec file parses")
def _t():
    files = sorted(SPECS.glob("*.json"))
    assert files, "no spec files found in %s" % SPECS
    for f in files:
        PartSpec.load(f)


@check("every spec validates its own reference solid")
def _t():
    for f in sorted(SPECS.glob("*.json")):
        sp = PartSpec.load(f)
        step = REF / ("%s.step" % sp.id)
        assert step.exists(), "no reference solid for %s" % sp.id
        errs = sp.check(S.measure(step, scale=sp.scale))
        assert not errs, "%s rejects its own reference: %s" % (sp.id, errs)


@check("a spec with no checks is rejected")
def _t():
    try:
        PartSpec({"id": "x", "name": "y", "description": "z"})
    except S.SpecError:
        return
    raise AssertionError("accepted a spec that can never fail")


@check("a spec missing required fields is rejected")
def _t():
    for missing in ("id", "name", "description"):
        data = {"id": "a", "name": "b", "description": "c", "checks": {"solids": 1}}
        del data[missing]
        try:
            PartSpec(data)
        except S.SpecError:
            continue
        raise AssertionError("accepted a spec with no %s" % missing)


# -- checks reject what they should ---------------------------------------

def _mutate(step_path, **kw):
    """Measure a real solid, then corrupt one property."""
    m = S.measure(step_path, scale=25.4)
    m.update(kw)
    return m


@check("wrong overall size is caught, with the delta and direction")
def _t():
    sp = PartSpec.load(SPECS / "P01-plate.json")
    errs = sp.check(_mutate(REF / "P01-plate.step", bbox=[4.5, 1.5, 0.25]))
    assert len(errs) == 1, errs
    msg = errs[0]
    assert "4.5000" in msg and "4.0000" in msg, msg
    assert "+0.5000" in msg, "must state how far off it is: %s" % msg
    assert "-0.5000" in msg, "must state which way to move: %s" % msg


@check("wrong volume is caught and says which way")
def _t():
    sp = PartSpec.load(SPECS / "P01-plate.json")
    over = sp.check(_mutate(REF / "P01-plate.step", volume=3.0))
    assert "Too much material" in over[0], over
    under = sp.check(_mutate(REF / "P01-plate.step", volume=0.5))
    assert "Too little material" in under[0], under


@check("a disconnected result is caught")
def _t():
    sp = PartSpec.load(SPECS / "BN-FRAME-base.json")
    errs = sp.check(_mutate(REF / "BN-FRAME-base.step", solids=12))
    assert "12 separate solid(s), expected 1" in errs[0], errs
    assert "floating apart" in errs[0], errs


@check("a missing hole is caught")
def _t():
    sp = PartSpec.load(SPECS / "C-01-anchor-plate.json")
    m = S.measure(REF / "C-01-anchor-plate.step", scale=25.4)
    m["holes"] = [h for h in m["holes"] if h["d"] != 0.266]
    errs = sp.check(m)
    assert any("0.2660" in e and "expected 1" in e for e in errs), errs


@check("an extra hole is caught when holes_exact is set")
def _t():
    sp = PartSpec.load(SPECS / "P01-plate.json")
    m = S.measure(REF / "P01-plate.step", scale=25.4)
    m["holes"] = m["holes"] + [{"d": 0.75}]
    errs = sp.check(m)
    assert any("extra hole" in e for e in errs), errs


@check("a hole of the wrong diameter is caught, naming what was found")
def _t():
    sp = PartSpec.load(SPECS / "P01-plate.json")
    m = S.measure(REF / "P01-plate.step", scale=25.4)
    m["holes"] = [{"d": 0.5}, {"d": 0.5}]
    errs = sp.check(m)
    assert any("0.5000" in e for e in errs), "must report what it actually found: %s" % errs


@check("an invalid solid is caught")
def _t():
    sp = PartSpec.load(SPECS / "P01-plate.json")
    errs = sp.check(_mutate(REF / "P01-plate.step", valid=False))
    assert any("validity" in e for e in errs), errs


@check("size_max rejects an oversize part and says by how much")
def _t():
    sp = PartSpec({"id": "fit", "name": "n", "description": "d",
                   "checks": {"size_max": [24.0, 20.0, 18.0]}})
    m = _mutate(REF / "P01-plate.step", bbox=[25.5, 19.0, 17.0])
    errs = sp.check(m)
    assert "must not exceed" in errs[0] and "1.5000" in errs[0], errs
    assert sp.check(_mutate(REF / "P01-plate.step", bbox=[23.0, 19.0, 17.0])) == []


@check("every failure message carries a number, including the categorical ones")
def _t():
    """The lesson from the 30-cycle sweep that died on 'length/type invalid'.

    valid=False and the mesh failures are included deliberately: they are the
    checks with no natural measurement, and they were the ones most likely to
    hand the model a verdict it could not act on.
    """
    sp = PartSpec.load(SPECS / "C-02-U-floor-bracket.json")
    m = _mutate(REF / "C-02-U-floor-bracket.step", bbox=[7.0, 3.0, 0.5],
                volume=9.9, solids=4, valid=False,
                mesh={"triangles": 900, "degenerate": 2, "open_edges": 5,
                      "watertight": False})
    errs = sp.check(m)
    assert len(errs) >= 8, errs
    assert any("validity" in e for e in errs), "the validity path must be covered"
    assert any("watertight" in e for e in errs), "the mesh path must be covered"
    for e in errs:
        assert any(ch.isdigit() for ch in e), "message with no measurement: %r" % e


# -- the gates that were measured but never enforced ----------------------

@check("a misspelled check key is refused, not silently ignored")
def _t():
    """An ignored key is an ignored GATE. Before this, a spec written with
    "volumne" and "hole" passed a 99 in^3 solid with no holes, zero errors."""
    try:
        PartSpec({"id": "T", "name": "n", "description": "d",
                  "checks": {"bbox": [4.0, 1.5, 0.25], "volumne": 1.45,
                             "hole": [{"d": 0.281}]}})
    except S.SpecError as e:
        assert "volumne" in str(e) and "hole" in str(e), str(e)
        assert "Known checks" in str(e), str(e)
    else:
        raise AssertionError("a spec with misspelled gates was accepted")
    # An unknown key inside a holes entry is refused too.
    try:
        PartSpec({"id": "T", "name": "n", "description": "d",
                  "checks": {"holes": [{"d": 0.281, "postion": [[0, 0]]}]}})
    except S.SpecError as e:
        assert "postion" in str(e), str(e)
    else:
        raise AssertionError("an unknown holes key was accepted")


@check("holes in the wrong place are caught")
def _t():
    """Right count, right diameter, wrong bolt pattern. Volume, bbox, solids and
    holes_exact are all identical - position was the only possible signal, and
    it was measured and thrown away."""
    sp = PartSpec.load(SPECS / "P01-plate.json")
    good = S.measure(REF / "P01-plate.step", scale=25.4)
    assert sp.check(good) == [], sp.check(good)

    moved = S.measure(REF / "P01-plate.step", scale=25.4)
    for h in moved["holes"]:
        h["at"] = [h["at"][0] / 2, 0.0, 0.25]      # +/-0.5 instead of +/-1.0
    errs = sp.check(moved)
    assert errs, "a mis-spaced bolt pattern passed"
    assert "0.5000" in errs[0] and "-1.0000" in errs[0], errs[0]
    # Everything else really is unchanged - position was the only signal.
    assert abs(moved["volume"] - good["volume"]) < 1e-9
    assert moved["bbox"] == good["bbox"]


@check("a blind hole is caught where the spec says it goes through")
def _t():
    sp = PartSpec.load(SPECS / "P01-plate.json")
    blind = S.measure(REF / "P01-plate.step", scale=25.4)
    for h in blind["holes"]:
        h["depth"] = 0.01
    errs = sp.check(blind)
    assert any("blind hole" in e for e in errs), errs
    assert any("0.2500" in e for e in errs), errs


@check("an explicit hole depth is enforced")
def _t():
    sp = PartSpec.load(SPECS / "P06-l-bracket.json")
    good = S.measure(REF / "P06-l-bracket.step", scale=25.4)
    assert sp.check(good) == [], sp.check(good)
    shallow = S.measure(REF / "P06-l-bracket.step", scale=25.4)
    for h in shallow["holes"]:
        h["depth"] = 0.10
    errs = sp.check(shallow)
    assert any("0.1000" in e and "0.2500" in e for e in errs), errs


@check("two specs sharing an id are refused")
def _t():
    d = pathlib.Path(tempfile.mkdtemp(prefix="bncad-dup-"))
    try:
        body = {"id": "SAME", "name": "n", "description": "d",
                "checks": {"solids": 1}}
        (d / "a.json").write_text(json.dumps(body))
        (d / "b.json").write_text(json.dumps(body))
        try:
            S.load_all(d)
        except S.SpecError as e:
            assert "SAME" in str(e) and "overwrite" in str(e), str(e)
        else:
            raise AssertionError("duplicate spec ids were accepted")
    finally:
        shutil.rmtree(d, ignore_errors=True)


@check("a harness fault is its own exception, not a model failure")
def _t():
    """bench must never score "the venv is broken" as "the model failed"."""
    assert issubclass(loop.HarnessFault, RuntimeError)
    assert not issubclass(loop.HarnessFault, loop.BuildInProgress)


# -- hole detection -------------------------------------------------------

@check("fillets are not counted as holes")
def _t():
    """Four R0.25 corner fillets and three real holes on the same plate."""
    m = S.measure(REF / "C-01-anchor-plate.step", scale=25.4)
    assert len(m["holes"]) == 3, m["holes"]
    assert sorted(h["d"] for h in m["holes"]) == [0.266, 0.281, 0.281]


@check("holes are located, not just counted")
def _t():
    m = S.measure(REF / "P01-plate.step", scale=25.4)
    xs = sorted(round(h["at"][0], 3) for h in m["holes"])
    assert xs == [-1.0, 1.0], xs


@check("a part with no holes reports none")
def _t():
    assert S.measure(REF / "BN-FRAME-base.step", scale=25.4)["holes"] == []


# -- units: the bug that would have shipped a part 25.4x too small --------

@check("a delivered STEP is physically correct in millimetres")
def _t():
    """CadQuery always stamps SI_UNIT(.MILLI.,.METRE.) into a STEP.

    An inch-authored 4.000 plate therefore describes 4mm to every reader.
    Fusion imported exactly that and reported 0.157in. The delivered file must
    carry real millimetres.
    """
    step = REF / "P01-plate.step"
    raw = S.measure(step)                       # believe the file's own units
    assert abs(raw["bbox"][0] - 101.6) < 0.01, (
        "delivered STEP is not in millimetres: %s" % raw["bbox"])
    text = step.read_text(errors="replace")
    assert "SI_UNIT(.MILLI.,.METRE.)" in text, "STEP must declare millimetres"


@check("measuring with a scale returns the spec's units")
def _t():
    step = REF / "P01-plate.step"
    inches = S.measure(step, scale=25.4)
    assert abs(inches["bbox"][0] - 4.0) < 0.001, inches["bbox"]
    assert abs(inches["volume"] - 1.45558) < 0.001, inches["volume"]
    assert abs(inches["holes"][0]["d"] - 0.281) < 0.001, inches["holes"]
    # Volume scales by the cube, not the factor.
    raw = S.measure(step)
    assert abs(raw["volume"] / (25.4 ** 3) - inches["volume"]) < 1e-9


@check("spec.scale resolves units, and rejects an unknown one")
def _t():
    assert PartSpec.load(SPECS / "P01-plate.json").scale == 25.4
    mm = PartSpec({"id": "a", "name": "b", "description": "c", "units": "mm",
                   "checks": {"solids": 1}})
    assert mm.scale == 1.0
    bad = PartSpec({"id": "a", "name": "b", "description": "c",
                    "units": "furlong", "checks": {"solids": 1}})
    try:
        bad.scale
    except S.SpecError as e:
        assert "furlong" in str(e)
    else:
        raise AssertionError("accepted an unknown unit")


@check("to_delivery scales an authored solid without distorting it")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-unit-"))
    try:
        import cadquery as cq
        from cadquery import exporters
        authored = work / "a.step"
        exporters.export(cq.Workplane("XY").box(4.0, 1.5, 0.25), str(authored))
        assert abs(S.measure(authored)["bbox"][0] - 4.0) < 1e-6

        delivered = work / "d.step"
        S.to_delivery(authored, delivered, work / "d.stl", 25.4)
        mm = S.measure(delivered)
        assert abs(mm["bbox"][0] - 101.6) < 0.001, mm["bbox"]
        back = S.measure(delivered, scale=25.4)
        for got, want in zip(back["bbox"], (4.0, 1.5, 0.25)):
            assert abs(got - want) < 0.001, back["bbox"]
        assert (work / "d.stl").exists()
        assert S.mesh_stats(work / "d.stl")["watertight"]
    finally:
        shutil.rmtree(work, ignore_errors=True)


# -- the STL deliverable --------------------------------------------------

def _write_stl(path, triangles):
    """Minimal binary STL writer, for building deliberately broken meshes."""
    import struct
    with open(path, "wb") as fh:
        fh.write(b"test".ljust(80, b"\0"))
        fh.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            fh.write(struct.pack("<3f", 0.0, 0.0, 1.0))
            for vertex in tri:
                fh.write(struct.pack("<3f", *vertex))
            fh.write(struct.pack("<H", 0))


@check("a real exported STL is watertight")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-stl-"))
    try:
        import cadquery as cq
        from cadquery import exporters
        stl = work / "box.stl"
        exporters.export(cq.Workplane("XY").box(2, 2, 1), str(stl))
        stats = S.mesh_stats(stl)
        assert stats["watertight"], stats
        assert stats["triangles"] >= 12, stats
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("a cracked mesh is caught")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-stl-"))
    try:
        stl = work / "open.stl"
        # One lone triangle: all three of its edges are unshared.
        _write_stl(stl, [[(0, 0, 0), (1, 0, 0), (0, 1, 0)]])
        stats = S.mesh_stats(stl)
        assert stats["watertight"] is False, stats
        assert stats["open_edges"] == 3, stats

        sp = PartSpec({"id": "m", "name": "n", "description": "d",
                       "checks": {"solids": 1}})
        errs = sp._check_mesh({"mesh": stats})
        assert errs and "not watertight" in errs[0], errs
        assert "3 edge(s)" in errs[0], errs
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("a degenerate facet is caught")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-stl-"))
    try:
        stl = work / "degen.stl"
        _write_stl(stl, [[(0, 0, 0), (1, 0, 0), (1, 0, 0)]])
        stats = S.mesh_stats(stl)
        assert stats["degenerate"] == 1, stats
        sp = PartSpec({"id": "m", "name": "n", "description": "d",
                       "checks": {"solids": 1}})
        errs = sp._check_mesh({"mesh": stats})
        assert errs and "degenerate" in errs[0], errs
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("a truncated STL is reported, not crashed on")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-stl-"))
    try:
        import struct as _s
        stl = work / "short.stl"
        stl.write_bytes(b"too short")
        assert "error" in S.mesh_stats(stl)
        stl.write_bytes(b"h".ljust(80, b"\0") + _s.pack("<I", 999))
        stats = S.mesh_stats(stl)
        assert "error" in stats and "short" in stats["error"], stats
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("mesh checking is skipped when no STL was measured")
def _t():
    sp = PartSpec.load(SPECS / "P01-plate.json")
    assert sp._check_mesh({"bbox": [1, 1, 1]}) == []


# -- the guard ------------------------------------------------------------

@check("the guard allows legitimate CadQuery")
def _t():
    good = ("import cadquery as cq\nfrom cadquery import exporters\n"
            "import math\nr = cq.Workplane('XY').box(1,1,1)\n"
            "exporters.export(r, '/tmp/x.step')\n")
    assert loop.guard(good) == [], loop.guard(good)


@check("the guard refuses dangerous imports and calls")
def _t():
    for bad, needle in (("import subprocess", "subprocess"),
                        ("import socket", "socket"),
                        ("from shutil import rmtree", "shutil"),
                        ("import urllib.request", "urllib"),
                        ("import os", "os"),
                        ("eval('1+1')", "eval"),
                        ("exec('x=1')", "exec"),
                        ("open('/etc/passwd').read()", "open"),
                        ("__import__('os')", "__import__")):
        errs = loop.guard(bad)
        assert errs and needle in errs[0], "%r slipped past the guard: %s" % (bad, errs)


@check("the guard does not trip on methods that share a builtin's name")
def _t():
    code = "import cadquery as cq\nw = cq.Workplane('XY')\nw.val().Volume()\n"
    assert loop.guard(code) == [], loop.guard(code)


@check("unparseable code is reported as a syntax error, not a crash")
def _t():
    errs = loop.guard("def (:\n")
    assert errs and "does not parse" in errs[0] and "line" in errs[0]


# -- the sandbox is real enforcement, not advice --------------------------

@check("the sandbox blocks writes outside the run directory")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-sb-"))
    target = work.parent / "bncad-escape-probe.txt"
    if target.exists():
        target.unlink()
    try:
        script = work / "escape.py"
        script.write_text(
            "try:\n"
            "    open(%r, 'w').write('escaped')\n"
            "    print('ESCAPED')\n"
            "except Exception as e:\n"
            "    print('BLOCKED', type(e).__name__)\n" % str(target))
        rc, out = loop.run_sandboxed(script, work, sys.executable, timeout=60)
        assert "BLOCKED" in out, out
        assert not target.exists(), "generated code wrote outside its run directory"
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("the sandbox blocks network access")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-sb-"))
    try:
        script = work / "net.py"
        script.write_text(
            "import socket\n"
            "try:\n"
            "    socket.create_connection(('1.1.1.1', 53), timeout=5)\n"
            "    print('NETWORK OPEN')\n"
            "except Exception as e:\n"
            "    print('BLOCKED', type(e).__name__)\n")
        rc, out = loop.run_sandboxed(script, work, sys.executable, timeout=60)
        assert "BLOCKED" in out, out
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("the sandbox allows writes inside the run directory")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-sb-"))
    try:
        script = work / "ok.py"
        script.write_text("open(%r, 'w').write('fine')\nprint('WROTE')\n"
                          % str(work / "out.txt"))
        rc, out = loop.run_sandboxed(script, work, sys.executable, timeout=60)
        assert rc == 0 and "WROTE" in out, (rc, out)
        assert (work / "out.txt").exists()
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("cadquery works inside the sandbox")
def _t():
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-sb-"))
    try:
        out_step = work / "b.step"
        script = work / "build.py"
        script.write_text(
            "import cadquery as cq\nfrom cadquery import exporters\n"
            "exporters.export(cq.Workplane('XY').box(2,2,1), %r)\nprint('BUILT')\n"
            % str(out_step))
        rc, out = loop.run_sandboxed(script, work, str(VENV_PY), timeout=300)
        assert rc == 0, out
        assert out_step.exists(), "no STEP produced under the sandbox"
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("a runaway child carries its own CPU limit, so it cannot outlive us")
def _t():
    """subprocess timeouts only work while THIS process is alive. Kill the loop
    mid-execution - jetsam under memory pressure is the realistic way - and the
    sandboxed child is orphaned and spins at 100% CPU forever. `ulimit -t` is
    set before exec, so the kernel stops it regardless of what happens here."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-cpu-"))
    try:
        script = work / "spin.py"
        script.write_text("x = 0\nwhile True:\n    x += 1\n")
        # Launch the same way run_sandboxed does, then abandon it.
        profile = work / "_sandbox.sb"
        profile.write_text(loop.SANDBOX_PROFILE.format(workdir=work.resolve()))
        child = subprocess.Popen(
            ["/bin/sh", "-c", 'ulimit -t 2; exec "$@"', "sh",
             "sandbox-exec", "-f", str(profile), sys.executable, "-I", str(script)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(work))
        try:
            # Nobody is enforcing a timeout here; only the child's own limit is.
            child.wait(timeout=45)
        except subprocess.TimeoutExpired:
            child.kill()
            raise AssertionError(
                "the child ignored its CPU limit and would orphan forever")
        assert child.returncode != 0, child.returncode
    finally:
        shutil.rmtree(work, ignore_errors=True)


@check("a runaway script is killed and reported as a timeout")
def _t():
    work = pathlib.Path(tempfile.mkdtemp(prefix="bncad-sb-"))
    try:
        script = work / "spin.py"
        script.write_text("while True:\n    pass\n")
        rc, out = loop.run_sandboxed(script, work, sys.executable, timeout=3)
        assert rc == 124, (rc, out)
        assert "did not finish" in out, out
    finally:
        shutil.rmtree(work, ignore_errors=True)


# -- harness faults must not be blamed on the model -----------------------

@check("the interpreter's own file error is recognised as a harness fault")
def _t():
    assert loop._is_our_fault("python: can't open file '/x/y.py': [Errno 2] "
                              "No such file or directory")
    assert loop._is_our_fault("ModuleNotFoundError: No module named 'cadquery'")
    # A relative interpreter path fails this way, because the child runs with
    # cwd set to its work directory.
    assert loop._is_our_fault(
        "sandbox-exec: execvp() of '.venv-cq/bin/python' failed: "
        "No such file or directory")


@check("making the interpreter absolute must not follow it out of its venv")
def _t():
    """A uv venv's bin/python is a symlink to the base interpreter.

    Path.resolve() follows it, leaving the venv - and every `import cadquery`
    in the sandbox then fails with ModuleNotFoundError, which reads as a broken
    install rather than a lost environment.
    """
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    made = os.path.abspath(str(VENV_PY))
    assert pathlib.Path(made).parent.parent.name == ".venv-cq", made
    probe = subprocess.run([made, "-c", "import cadquery; print('ok')"],
                           capture_output=True, text=True)
    assert probe.returncode == 0, (
        "the absolute interpreter lost its venv: %s" % probe.stderr.strip()[-200:])


@check("the model's own FileNotFoundError is NOT a harness fault")
def _t():
    """It exported into a directory it never made. That is the model's to fix.

    Treating it as ours aborted the entire build - the exact inverse of the bug
    the harness-fault check exists to prevent.
    """
    traceback = ("Traceback (most recent call last):\n"
                 "  File \"gen.py\", line 9, in <module>\n"
                 "    exporters.export(result, 'out/part.step')\n"
                 "FileNotFoundError: [Errno 2] No such file or directory: "
                 "'out/part.step'")
    assert not loop._is_our_fault(traceback)
    for real_model_error in (
            "ValueError: Selected faces must be co-planar.",
            "OCP.Standard.Standard_Failure: BRep_API: command not done",
            "AttributeError: 'Workplane' object has no attribute 'centerX'"):
        assert not loop._is_our_fault(real_model_error), real_model_error


# -- the loop itself, end to end, with a scripted "model" -----------------

class FakeProvider:
    """A provider that returns a canned script instead of calling a model.

    This is what lets the whole of build() be exercised offline: the loop's
    real risk is not the model, it is the plumbing around it - which file gets
    promoted, in which units, and whether a failure is reported as one.
    """

    def __init__(self, *scripts):
        self.name = "fake"
        self.scripts = list(scripts)
        self.calls = 0

    def chat(self, system, user, model, temperature=0.15, max_tokens=8000,
             timeout=None, retries=2):
        import re as _re
        step = _re.search(r"STEP_PATH = '([^']+)'", user).group(1)
        stl = _re.search(r"STL_PATH = '([^']+)'", user).group(1)
        body = self.scripts[min(self.calls, len(self.scripts) - 1)]
        self.calls += 1
        code = body % {"step": step, "stl": stl}
        return "```python\n%s\n```" % code, 0.01, {"completion_tokens": 1}


_GOOD_PLATE = """
import cadquery as cq
from cadquery import exporters
result = (cq.Workplane("XY").box(4.0, 1.5, 0.25, centered=(True, True, False))
          .edges("|Z").fillet(0.25)
          .faces(">Z").workplane().pushPoints([(-1.0, 0.0), (1.0, 0.0)])
          .hole(0.281))
exporters.export(result, %(step)r)
exporters.export(result, %(stl)r)
"""

_WRONG_PLATE = _GOOD_PLATE.replace("box(4.0,", "box(5.0,")


@check("build() end to end delivers a MILLIMETRE file, measured back in inches")
def _t():
    """The regression guard for the 25.4x bug.

    If build() ever promotes the authored STEP instead of the converted one,
    the raw file reads 4.0 instead of 101.6 and this fails. Nothing else in the
    suite would notice.
    """
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-e2e-"))
    try:
        sp = PartSpec.load(SPECS / "P01-plate.json")
        r = loop.build(sp, FakeProvider(_GOOD_PLATE), "canned", out,
                       max_attempts=2, python=str(VENV_PY), timeout=300,
                       log=lambda m: None)
        assert r["ok"], r
        assert r["attempt"] == 1, r["attempt"]

        step = out / "P01-plate.step"
        assert step.exists(), sorted(p.name for p in out.iterdir())

        raw = S.measure(step)                       # believe the file's units
        assert abs(raw["bbox"][0] - 101.6) < 0.01, (
            "build() promoted a file that is not in millimetres: %s" % raw["bbox"])

        assert abs(r["measured"]["bbox"][0] - 4.0) < 0.001, r["measured"]["bbox"]
        assert abs(r["measured"]["volume"] - 1.45558) < 0.01, r["measured"]

        assert (out / "P01-plate.stl").exists()
        assert S.mesh_stats(out / "P01-plate.stl")["watertight"]
        assert (out / "P01-plate-run.json").exists()
        assert not (out / "_work-P01-plate").exists(), "workdir kept after a pass"
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("build() reports a failure as a failure and repairs from real numbers")
def _t():
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-e2e-"))
    try:
        sp = PartSpec.load(SPECS / "P01-plate.json")
        r = loop.build(sp, FakeProvider(_WRONG_PLATE), "canned", out,
                       max_attempts=2, python=str(VENV_PY), timeout=300,
                       log=lambda m: None)
        assert not r["ok"], "a 5.0in plate passed a 4.0in spec"
        errs = r["attempts"][0]["errors"]
        assert any("5.0000" in e and "4.0000" in e for e in errs), errs
        # A failed run must not leave a file that looks like a delivery.
        assert not (out / "P01-plate.step").exists(), \
            "a failed build left a deliverable behind"
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("a failed run leaves nothing that reads like a deliverable")
def _t():
    """"-best" means "least wrong attempt". Left in an export directory that
    reads far too much like "best available part" for something that goes to a
    supplier, so a failure renames it to -REJECTED and a pass deletes it."""
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-reject-"))
    try:
        sp = PartSpec.load(SPECS / "P01-plate.json")
        r = loop.build(sp, FakeProvider(_WRONG_PLATE), "canned", out,
                       max_attempts=2, python=str(VENV_PY), timeout=300,
                       log=lambda m: None)
        assert not r["ok"]
        names = sorted(f.name for f in out.iterdir() if f.is_file())
        assert "P01-plate.step" not in names, names
        assert "P01-plate-best.step" not in names, names
        assert "P01-plate-REJECTED.step" in names, names
        # And the rejected solid really does fail the spec.
        m = S.measure(out / "P01-plate-REJECTED.step", scale=sp.scale)
        assert sp.check(m), "the REJECTED artefact actually meets the spec"

        # A later passing run must clear the REJECTED files, not leave them
        # beside the good deliverable.
        r2 = loop.build(sp, FakeProvider(_GOOD_PLATE), "canned", out,
                        max_attempts=2, python=str(VENV_PY), timeout=300,
                        log=lambda m: None)
        assert r2["ok"]
        names = sorted(f.name for f in out.iterdir() if f.is_file())
        assert "P01-plate.step" in names, names
        assert not any("REJECTED" in n for n in names), names
        assert not any("-best" in n for n in names), names
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("build() recovers when a later attempt fixes an earlier failure")
def _t():
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-e2e-"))
    try:
        sp = PartSpec.load(SPECS / "P01-plate.json")
        r = loop.build(sp, FakeProvider(_WRONG_PLATE, _GOOD_PLATE), "canned",
                       out, max_attempts=3, python=str(VENV_PY), timeout=300,
                       log=lambda m: None)
        assert r["ok"] and r["attempt"] == 2, r
        assert (out / "P01-plate.step").exists()
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("a relative interpreter path is resolved, not handed to the sandbox raw")
def _t():
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    import re as _re
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-relpy-"))
    try:
        sp = PartSpec.load(SPECS / "P01-plate.json")
        rel = os.path.relpath(str(VENV_PY), str(ROOT))
        cwd = os.getcwd()
        os.chdir(str(ROOT))
        try:
            r = loop.build(sp, FakeProvider(_GOOD_PLATE), "canned", out,
                           max_attempts=2, python=rel, timeout=300,
                           log=lambda m: None)
        finally:
            os.chdir(cwd)
        assert r["ok"], "a relative --python path broke the run: %s" % r["attempts"][0]
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("a second build of the same part in the same directory is refused")
def _t():
    """Overlapping builds share _work-<id>, which build() clears on entry, so
    the second run deletes the first run's files and the first dies with
    FileNotFoundError. Reproduced exactly that way before the lock existed."""
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-lock-"))
    try:
        held = loop._BuildLock(out, "P01-plate")
        held.__enter__()
        try:
            sp = PartSpec.load(SPECS / "P01-plate.json")
            try:
                loop.build(sp, FakeProvider(_GOOD_PLATE), "canned", out,
                           max_attempts=1, python=str(VENV_PY), timeout=120,
                           log=lambda m: None)
            except loop.BuildInProgress as e:
                assert "P01-plate" in str(e) and str(os.getpid()) in str(e), str(e)
            else:
                raise AssertionError("a concurrent build was allowed to race")
        finally:
            held.__exit__()
        # Released: the next acquisition must succeed.
        with loop._BuildLock(out, "P01-plate"):
            pass
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("a lock file left by a dead process does not block anything")
def _t():
    """flock is released by the kernel when the holder dies, however it dies.

    The first version tracked a pid in the file and "took over" when that pid
    looked dead, which meant a SIGKILL, a panic or a reboot could leave a file
    that blocked a part forever - and a recycled pid could make a dead lock look
    permanently alive.
    """
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-lock-"))
    try:
        (out / ".P01-plate.lock").write_text("99999999\n")
        with loop._BuildLock(out, "P01-plate"):
            pass
        # A file with our own live pid in it is likewise not a lock.
        (out / ".P01-plate.lock").write_text("%d\n" % os.getpid())
        with loop._BuildLock(out, "P01-plate"):
            pass
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("a lock held by a live process in another interpreter is refused")
def _t():
    """The real overlap: cron and a human, in two separate processes."""
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-lock-"))
    try:
        holder = subprocess.Popen(
            [sys.executable, "-c",
             "import fcntl, os, sys, time\n"
             "fd = os.open(sys.argv[1], os.O_CREAT | os.O_RDWR)\n"
             "fcntl.flock(fd, fcntl.LOCK_EX)\n"
             "os.write(fd, str(os.getpid()).encode())\n"
             "print('held', flush=True)\n"
             "time.sleep(60)\n",
             str(out / ".P01-plate.lock")],
            stdout=subprocess.PIPE, text=True)
        try:
            assert holder.stdout.readline().strip() == "held"
            try:
                with loop._BuildLock(out, "P01-plate"):
                    raise AssertionError("acquired a lock another process holds")
            except loop.BuildInProgress as e:
                assert "P01-plate" in str(e), str(e)
        finally:
            holder.kill()
            holder.wait(timeout=10)
        # Once that process is gone the kernel has already released it.
        with loop._BuildLock(out, "P01-plate"):
            pass
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("clearing one part's deliverables does not touch a similarly named part")
def _t():
    """A "<id>*" glob swept siblings: building "P01-plate" would delete
    "P01-plate-v2.step" sitting beside it in the same directory."""
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-glob-"))
    try:
        sibling = out / "P01-plate-v2.step"
        sibling.write_text("a neighbouring part's validated deliverable")
        sp = PartSpec.load(SPECS / "P01-plate.json")
        r = loop.build(sp, FakeProvider(_GOOD_PLATE), "canned", out,
                       max_attempts=2, python=str(VENV_PY), timeout=300,
                       log=lambda m: None)
        assert r["ok"], r
        assert sibling.exists(), "building P01-plate deleted P01-plate-v2.step"
        assert sibling.read_text().startswith("a neighbouring")
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("a corrupt lock file does not wedge the build forever")
def _t():
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-lock-"))
    try:
        (out / ".P01-plate.lock").write_text("not a pid at all")
        with loop._BuildLock(out, "P01-plate"):
            pass
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("the lock is released even when the build raises")
def _t():
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-lock-"))
    try:
        class Boom:
            name = "boom"
            def chat(self, *a, **k):
                raise RuntimeError("provider exploded")
        sp = PartSpec.load(SPECS / "P01-plate.json")
        # A provider that always raises burns its attempts and returns not-ok;
        # either way the lock must not survive the call.
        try:
            loop.build(sp, Boom(), "boom", out, max_attempts=1,
                       python=str(VENV_PY), timeout=60, log=lambda m: None)
        except Exception:
            pass
        # The file persists by design under flock; what matters is that the
        # lock itself is free for the next run.
        with loop._BuildLock(out, "P01-plate"):
            pass
    finally:
        shutil.rmtree(out, ignore_errors=True)


@check("a stale deliverable from a previous run is cleared before building")
def _t():
    if not VENV_PY.exists():
        raise Skip("no CadQuery venv at %s" % VENV_PY)
    out = pathlib.Path(tempfile.mkdtemp(prefix="bncad-e2e-"))
    try:
        sp = PartSpec.load(SPECS / "P01-plate.json")
        loop.build(sp, FakeProvider(_GOOD_PLATE), "canned", out,
                   max_attempts=2, python=str(VENV_PY), timeout=300,
                   log=lambda m: None)
        assert (out / "P01-plate.step").exists()
        # Now a run that cannot succeed must not leave the good file looking
        # like it came from this run.
        loop.build(sp, FakeProvider(_WRONG_PLATE), "canned", out,
                   max_attempts=1, python=str(VENV_PY), timeout=300,
                   log=lambda m: None)
        assert not (out / "P01-plate.step").exists(), \
            "the previous run's passing STEP survived a failing run"
    finally:
        shutil.rmtree(out, ignore_errors=True)


# -- code extraction ------------------------------------------------------

@check("a fence with any language tag or capitalisation is extracted")
def _t():
    """```Python previously matched nothing, so the whole reply became "code"
    and came back to the model as a syntax error against text it never wrote."""
    for fence in ("```python", "```Python", "```PYTHON", "```py", "```python3",
                  "```"):
        text = "here you go\n%s\nresult = 1\n```" % fence
        assert loop.extract_code(text) == "result = 1", fence

@check("the last code block wins")
def _t():
    text = "here is a sketch\n```python\nWRONG\n```\nand the answer\n```python\nRIGHT\n```"
    assert loop.extract_code(text) == "RIGHT"


@check("bare code with no fences is accepted")
def _t():
    assert loop.extract_code("import cadquery as cq") == "import cadquery as cq"


@check("a code fence inside a reasoning block is discarded")
def _t():
    text = "<think>```python\nSCRATCH\n```</think>```python\nFINAL\n```"
    assert loop.extract_code(provider.strip_reasoning(text)) == "FINAL"


# -- providers degrade cleanly -------------------------------------------

@check("a dead provider reports dead instead of raising")
def _t():
    p = provider.Provider("dead", "http://127.0.0.1:9/v1")
    assert p.alive(timeout=1) is False
    assert p.models() == []


@check("an unknown model names the real roster")
def _t():
    if not provider.discover(timeout=2):
        raise Skip("no local model server answering")
    try:
        provider.resolve("definitely-not-a-real-model-xyz")
    except provider.ProviderError as e:
        assert "Available" in str(e), str(e)
        return
    raise AssertionError("resolved a model that does not exist")


@check("reasoning scratchpad is stripped, closed or not")
def _t():
    assert provider.strip_reasoning("<think>a</think>B") == "B"
    assert provider.strip_reasoning("keep<think>dropped forever") == "keep"
    assert provider.strip_reasoning("<REASONING>x</REASONING>ok") == "ok"


@check("a truncated completion is named as truncation, not a syntax error")
def _t():
    """finish_reason='length' used to be dropped, so a reply cut off at the
    token limit reached the model as "your code does not parse". Ollama's
    default 4096-token context makes this the likely failure, not a rare one."""
    import json as _json
    import urllib.request as _u

    payload = {
        "choices": [{"finish_reason": "length",
                     "message": {"content": "```python\nresult = cq.Workplane("}}],
        "usage": {"completion_tokens": 4096},
    }

    class _Resp:
        def read(self):
            return _json.dumps(payload).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    real = _u.urlopen
    _u.urlopen = lambda *a, **k: _Resp()
    try:
        provider.Provider("t", "http://127.0.0.1:1/v1").chat(
            "sys", "user", "m", retries=0)
    except provider.ProviderError as e:
        assert "truncated" in str(e) and "4096" in str(e), str(e)
    else:
        raise AssertionError("a length-truncated reply was accepted as an answer")
    finally:
        _u.urlopen = real


@check("the LM Studio URL override is honoured under both spellings")
def _t():
    """runtime.json and preflight.py say BN_LM_STUDIO_URL; bncad said
    BN_LMSTUDIO_URL. Exporting the documented one and silently reaching a
    different endpoint is a bad afternoon."""
    for name in ("BN_LMSTUDIO_URL", "BN_LM_STUDIO_URL"):
        os.environ.pop("BN_LMSTUDIO_URL", None)
        os.environ.pop("BN_LM_STUDIO_URL", None)
        os.environ[name] = "http://127.0.0.1:4321/v1"
        try:
            got = provider._env_url("BN_LMSTUDIO_URL", provider.LM_STUDIO)
            assert got == "http://127.0.0.1:4321/v1", (name, got)
        finally:
            os.environ.pop(name, None)
    assert provider._env_url("BN_LMSTUDIO_URL", provider.LM_STUDIO) == provider.LM_STUDIO


# -- fusion module is safe with Fusion closed -----------------------------

@check("the fusion module reports unreachable without raising")
def _t():
    from bncad import fusion
    ok, detail = fusion.available()
    assert isinstance(ok, bool) and isinstance(detail, str) and detail


@check("the fusion import script is valid python once formatted")
def _t():
    from bncad import fusion
    body = fusion.IMPORT_SCRIPT.format(path="/tmp/x.step")
    compile(body, "<fusion>", "exec")
    assert "'/tmp/x.step'" in body
    assert "def run(_context: str):" in body, "Fusion's entry point signature is exact"


def main():
    print("bncad test suite")
    for n in PASSED:
        print("  ok   %s" % n)
    for n, why in SKIPPED:
        print("  SKIP %s (%s)" % (n, why))
    for n, why in FAILED:
        print("  FAIL %s\n         %s" % (n, why))
    tail = ", %d skipped" % len(SKIPPED) if SKIPPED else ""
    print("\n%d passed, %d failed%s" % (len(PASSED), len(FAILED), tail))
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
