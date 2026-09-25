#!/usr/bin/env python3
"""Generate -> execute -> measure -> repair, until the solid matches its spec.

The model writes CadQuery. We run it, measure the STEP it produced, and hand
back the numeric gap. Numbers are what make this converge: "volume is 480.0,
expected 232.0, +248.0 over - members are overlapping at the corners" is a
repairable message. "invalid" is not.

Generated code is executed under `sandbox-exec` with writes confined to the run
directory and the network denied. This is model-written Python running on a
personal machine; an AST allowlist alone is advisory, the sandbox is enforcement.
Both are used - the AST scan exists to give the model a fixable error message
before the sandbox gives it an unfixable one.
"""

import ast
import fcntl
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

SYSTEM = """You write Python that uses the `cadquery` library to build 3D solid CAD models.

MATCH THE SHAPE BEFORE YOU MATCH A PATTERN
Read what the part actually is - round, rectangular, or an assembly of members -
and pick the pattern for THAT shape. A square plate with rounded corners is not
a disc. They can share a bounding box and they never share a volume, which is
exactly how the wrong choice gets caught. Copying the nearest example instead of
the right one is the most common failure here.

HARD RULES
1. Output ONE complete Python script in a single ```python code block. No prose.
2. It must run start to finish with no input, no network and no file reads.
3. Work in the units the task states, and only those. Put every dimension in
   named constants at the top. Never convert - the task's numbers are final.
4. Import exactly: `import cadquery as cq` and `from cadquery import exporters`.
5. Export with `exporters.export(result, STEP_PATH)` and
   `exporters.export(result, STL_PATH)` using the exact paths given in the task.
6. Use only `cadquery`, `math` and `json`. No other imports.
7. Never call sys.exit(). Never wrap the build in try/except - a traceback is
   wanted, a swallowed error is not.

BOX MEMBERS - USE THIS EXACT PATTERN
`box(l, w, h, centered=False)` puts the box corner at the origin; translate it
into place. Never eyeball positions - write an explicit member table so each
corner sits at an absolute coordinate.

    W, D, H, P = 24.0, 20.0, 18.0, 1.0
    MEMBERS = []
    for x in (0, W - P):                       # 4 vertical posts
        for y in (0, D - P):
            MEMBERS.append((P, P, H, x, y, 0))
    for y in (0, D - P):                       # 4 width rails between the posts
        for z in (0, H - P):
            MEMBERS.append((W - 2*P, P, P, P, y, z))
    for x in (0, W - P):                       # 4 depth rails between the posts
        for z in (0, H - P):
            MEMBERS.append((P, D - 2*P, P, x, P, z))

    result = None
    for (lx, ly, lz, x, y, z) in MEMBERS:
        m = cq.Workplane("XY").box(lx, ly, lz, centered=False).translate((x, y, z))
        result = m if result is None else result.union(m)

`centered=False` means the box occupies x..x+lx, so a member at x=W-P ends
exactly at W. Union every member into ONE connected solid; they must touch.

ROUND PARTS - USE A CIRCLE, NOT A FILLETED SQUARE
A disc, washer, spacer, boss, shaft or tube is round.

    OD, ID, T = 1.5, 0.5, 0.125
    disc = cq.Workplane("XY").circle(OD / 2).extrude(T)   # circle takes a RADIUS
    disc = disc.faces(">Z").workplane().hole(ID)          # hole takes a DIAMETER

`.circle()` takes a RADIUS and `.hole()` takes a DIAMETER. Mixing them up is the
single most common mistake in this loop - halve or double deliberately, never by
habit.

FLAT PLATE WITH ROUNDED CORNERS AND HOLES - USE THIS EXACT PATTERN
Do NOT invent Workplane keyword arguments. There is no centerX, centerY or
centerAt. This is the whole vocabulary needed:

    L, W, T, R = 4.0, 1.5, 0.25, 0.25
    plate = (cq.Workplane("XY")
             .box(L, W, T, centered=(True, True, False))   # centred in X/Y, sits on Z=0
             .edges("|Z").fillet(R))                       # the 4 vertical corner edges

    plate = (plate.faces(">Z").workplane()
             .pushPoints([(-1.0, 0.0), (1.0, 0.0)])        # coordinates from the CENTRE
             .hole(0.281))                                 # DIAMETER, drills through

Chain `.faces(">Z").workplane()` again before each new set of holes.
`.hole(d)` takes a DIAMETER and goes all the way through.

SELECTORS - THE SINGLE BIGGEST TRAP
`.faces(">Z")` selects THE ONE topmost face. `.faces("|Z")` selects EVERY face
parallel to Z - several faces at different places - and calling `.workplane()`
on that set raises "Selected faces must be co-planar."

    >Z  <Z  >X  <X  >Y  <Y    one extreme face - almost always what you want
    |Z  |X  |Y                every face or edge parallel to an axis - a SET

Use `>` when you need a face to work on. Use `|` only to select edges to fillet.

HOLES ON ANY AXIS - CUT A POSITIONED CYLINDER
`.faces(">Z").workplane().hole(d)` only drills straight down through the top.
For a hole along X or Y, or into a shape where the target face is not obvious,
cut an explicitly positioned cylinder instead. This always works, needs no
selector, and cannot pick the wrong face:

    # hole along Z at (x=2.0, y=0.75) through 0.25 of material starting at z=0
    result = result.cut(cq.Workplane("XY").circle(0.281/2).extrude(0.25)
                        .translate((2.0, 0.75, 0)))

    # hole along X at (y=0.75, z=1.5) through 0.25 of material starting at x=0
    result = result.cut(cq.Workplane("YZ").circle(0.281/2).extrude(0.25)
                        .translate((0, 0.75, 1.5)))

`Workplane("XY")` extrudes along +Z, `Workplane("YZ")` along +X, and
`Workplane("XZ")` along +Y. Make the cylinder at least as long as the material
it passes through. Remember `.circle()` takes a RADIUS.

For ANY hole that is not straight down through the single top face, use this
cut-a-cylinder pattern. Do not reach for `.faces(...)` to find the face - that
is the step that fails.

BUILD EVERY BOX ON Workplane("XY") AND TRANSLATE IT
Never build a box on "YZ" or "XZ" to orient it. `box()` always takes
(size_x, size_y, size_z) in world axes, so building it on a rotated workplane
does not rotate the box - it just makes the arguments mean something you did not
intend, and the part comes out the wrong size in one axis. Build every box on
"XY" with its true world dimensions and move it with `.translate((x, y, z))`.

    # a 0.25 thick upright 2.0 tall, standing at the origin corner
    upright = cq.Workplane("XY").box(0.25, 1.5, 2.0, centered=False)

BUILD ONLY WHAT IS ASKED FOR
Do not add fillets, chamfers, holes or rounding the spec does not call for.
Every extra feature changes the volume and fails the check, and filleting an
edge that a later cut runs into raises "BRep_API: command not done".

ARITHMETIC IS YOUR JOB
Before you answer, add up your own numbers and confirm the result spans exactly
the stated overall size and reaches the stated volume. Most failures here are
arithmetic, not API.

WHEN GIVEN VALIDATION ERRORS
Fix those specific numbers. Keep everything that already passed. Do not start
over and do not resend the same script."""

# What generated code may import. Everything else is refused with a message the
# model can act on, before the sandbox refuses it with one it cannot.
ALLOWED_IMPORTS = {"cadquery", "math", "json", "OCP"}
BANNED_CALLS = {"eval", "exec", "compile", "__import__", "open", "input",
                "breakpoint", "globals", "locals", "vars", "getattr", "setattr"}

# Writes are confined to the run directory and nothing else. An earlier version
# also allowed /private/var/folders so the interpreter had somewhere to put temp
# files; the test suite immediately escaped through it, because the system temp
# root is shared. The child now gets a TMPDIR *inside* its run directory, so the
# broad grant is unnecessary. Reads stay open - the interpreter and the OCP
# libraries live all over the filesystem, and reading is not the risk here.
SANDBOX_PROFILE = """(version 1)
(deny default)
(allow process-exec process-fork sysctl-read mach-lookup signal file-ioctl)
(allow file-read*)
(allow file-write*
    (subpath "{workdir}")
    (literal "/dev/null")
    (literal "/dev/urandom")
    (literal "/dev/dtracehelper"))
"""


def extract_code(text):
    """The last fenced python block, or the whole reply if it is bare code.

    The LAST block, not the first: models that narrate often show a wrong
    sketch first and the finished script last.
    """
    # Case-insensitive, and tolerant of any language tag. A model that writes
    # ```Python or ```python3 was previously not matched at all, so the whole
    # reply fell through as "code" and came back to it as a syntax error.
    blocks = re.findall(r"```[^\n]*\n(.*?)```", text, re.S | re.I)
    if blocks:
        return blocks[-1].strip()
    return text.strip()


def guard(code):
    """Static refusals, phrased so the model can fix them. [] means allowed."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return ["The script does not parse: line %s, %s" % (e.lineno, e.msg)]

    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                if top not in ALLOWED_IMPORTS:
                    bad.append("`import %s` is not permitted. Use only %s."
                               % (a.name, ", ".join(sorted(ALLOWED_IMPORTS))))
        elif isinstance(node, ast.ImportFrom):
            top = (node.module or "").split(".")[0]
            if top and top not in ALLOWED_IMPORTS:
                bad.append("`from %s import ...` is not permitted. Use only %s."
                           % (node.module, ", ".join(sorted(ALLOWED_IMPORTS))))
        elif isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "id", None) or getattr(fn, "attr", None)
            if isinstance(fn, ast.Name) and name in BANNED_CALLS:
                bad.append("`%s(...)` is not permitted. Build the solid directly; "
                           "the export calls are the only file access you need."
                           % name)
    return sorted(set(bad))


def run_sandboxed(script_path, workdir, python, timeout=900):
    """Execute a generated script confined to `workdir`. Returns (rc, output)."""
    workdir = pathlib.Path(workdir).resolve()
    profile = workdir / "_sandbox.sb"
    # /private/tmp and /tmp are the same place; resolve() already gave the real
    # path, which is what the sandbox matches on.
    profile.write_text(SANDBOX_PROFILE.format(workdir=workdir))
    # Give the child a temp directory it is actually allowed to write to, so the
    # profile does not have to open up the shared system temp root.
    tmp = workdir / "tmp"
    tmp.mkdir(exist_ok=True)
    env = dict(os.environ, TMPDIR=str(tmp), TMP=str(tmp), TEMP=str(tmp))

    # `ulimit -t` gives the child its own kernel-enforced CPU limit before exec.
    # The subprocess timeout below only works while THIS process is alive: kill
    # the loop mid-execution - jetsam under memory pressure is the realistic way
    # - and the sandboxed child is orphaned and spins at 100% CPU forever.
    # Reproduced exactly that way. A limit the child carries itself survives the
    # parent's death; `sh` sets it and then execs, so there is no preexec_fn and
    # no thread-safety question.
    cmd = ["/bin/sh", "-c", 'ulimit -t %d; exec "$@"' % max(int(timeout), 1),
           "sh", "sandbox-exec", "-f", str(profile), str(python), "-I",
           str(script_path)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           cwd=str(workdir), env=env)
    except subprocess.TimeoutExpired:
        return 124, ("The script did not finish within %ds. A boolean operation is "
                     "probably running on far more geometry than intended - check "
                     "for a loop building thousands of features." % timeout)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out.strip()


# Failures the interpreter reports before the generated code ever runs. These
# are always the harness's fault - a bad path, a missing interpreter - and are
# not something the model can repair.
#
# These must be phrases only the INTERPRETER emits, never the generated script.
# A bare "No such file or directory" was here first and was exactly wrong: a
# model that exports to a missing subdirectory raises FileNotFoundError with
# that text, and the whole build aborted blaming the harness for a model error
# the model could have fixed. The interpreter's own failure reads
# "can't open file '<path>': [Errno 2] No such file or directory", so the
# distinctive half is what to match on.
_HARNESS_FAULTS = ("can't open file",
                   "cannot find Python",
                   "execvp()",                 # sandbox-exec could not start the interpreter
                   "sandbox-exec: ",           # a malformed or unreadable profile
                   "ModuleNotFoundError: No module named 'cadquery'")


def _is_our_fault(output):
    return any(marker in output for marker in _HARNESS_FAULTS)


def _tail(text, lines=14):
    got = [l for l in text.splitlines() if l.strip()]
    return "\n".join(got[-lines:])


def _prompt_for(task, prev_err, prev_code, stuck):
    """Build the attempt prompt.

    Showing the model its own failed script is what makes repair work - and,
    once it is stuck, is exactly what keeps it stuck. A model that has returned
    byte-identical code twice is anchored on that code, so the third attempt
    drops the script entirely and restates the task with only the errors. It
    cannot copy what it cannot see.
    """
    if prev_err is None:
        return task
    if stuck >= 2:
        return ("%s\n\n--- YOUR LAST %d ATTEMPTS WERE IDENTICAL AND ALL FAILED ---\n%s\n\n"
                "That approach is wrong at the root - do not reproduce it. Start again "
                "from the pattern that matches this part's SHAPE, and satisfy every "
                "measurement above."
                % (task, stuck + 1, prev_err))
    hint = ("\n\nYou returned an IDENTICAL script to last time and it still fails. "
            "Change the specific numbers named in the errors."
            if stuck else "")
    return ("%s\n\n--- YOUR PREVIOUS SCRIPT ---\n%s\n--- IT FAILED WITH ---\n%s\n\n"
            "Fix those specific problems and return the complete corrected script.%s"
            % (task, prev_code, prev_err, hint))


def _log(msg):
    """Unbuffered, because these runs are watched through a log file.

    A plain print() buffers when stdout is not a terminal, so a background
    bench shows an empty log for an hour and looks hung when it is working
    perfectly.
    """
    print(msg, flush=True)


class BuildInProgress(RuntimeError):
    """Another build of this part is already running in this output directory."""


class HarnessFault(RuntimeError):
    """bncad itself could not run the generated script.

    Distinct from a model error so `bench` can refuse to score it. A broken venv
    recorded as "the model failed this part" is a lie that outlives the run.
    """


class _BuildLock:
    """One build per (output directory, part) at a time, via flock.

    Two overlapping builds of the same part share `_work-<id>`, and build()
    clears that directory on entry - so the second run deletes the first run's
    files mid-flight and the first dies with FileNotFoundError. Reproduced
    exactly that way before this existed.

    Refusing the second run is the honest behaviour rather than letting them
    race: on a machine running scheduled jobs, an overlap means a human started
    something while cron was already working, and silently picking a winner
    would leave a deliverable nobody can attribute.

    **The kernel owns this lock, not a pid written in a file.** The first version
    recorded a pid and took over the lock when that pid looked dead, which had
    three separate problems on a machine that runs for months: two processes
    could both judge the same lock stale and the second would then unlink the
    first's *live* lock; a recycled pid made a dead lock look alive forever; and
    a SIGKILL or a reboot left a file nothing would clear. `flock` has none of
    them - the OS drops the lock when the process dies, however it dies, and
    acquisition is atomic. The file itself is only a place to record who holds
    it, for the error message.
    """

    def __init__(self, outdir, spec_id):
        self.path = pathlib.Path(outdir) / (".%s.lock" % spec_id)
        self.spec_id = spec_id
        self.fd = None

    def __enter__(self):
        self.fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            owner = self._owner()
            os.close(self.fd)
            self.fd = None
            raise BuildInProgress(
                "another build of %s is already running in %s%s. Wait for it, "
                "or build into a different --out directory."
                % (self.spec_id, self.path.parent,
                   " (pid %s)" % owner if owner else ""))
        os.ftruncate(self.fd, 0)
        os.write(self.fd, ("%d\n" % os.getpid()).encode())
        os.fsync(self.fd)
        return self

    def _owner(self):
        """The pid recorded by whoever holds the lock, for the message only."""
        try:
            return self.path.read_text().strip().splitlines()[0]
        except (OSError, IndexError):
            return None

    def __exit__(self, *exc):
        if self.fd is not None:
            # Releasing the flock is what matters. The file stays: unlinking it
            # is what let the old version delete a lock another process was
            # holding, and an empty marker file costs nothing.
            try:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
            finally:
                os.close(self.fd)
                self.fd = None
        return False


def build(spec, provider, model, outdir, max_attempts=8, temperature=0.15,
          python=None, timeout=900, log=_log, keep_workdir=False):
    """Run the loop for one part. Returns a result dict.

    Raises BuildInProgress if another build of this part is already running in
    the same output directory.
    """
    lock_dir = pathlib.Path(outdir).resolve()
    lock_dir.mkdir(parents=True, exist_ok=True)
    with _BuildLock(lock_dir, spec.id):
        return _build(spec, provider, model, outdir, max_attempts, temperature,
                      python, timeout, log, keep_workdir)


def _build(spec, provider, model, outdir, max_attempts, temperature,
           python, timeout, log, keep_workdir):
    # Absolute, for the same reason outdir is: the child runs with cwd set to
    # its own work directory, so a relative interpreter path fails with
    # "execvp() ... No such file or directory" - which the loop would then hand
    # to the model as if it had written bad code.
    #
    # abspath, NOT resolve(). A uv venv's bin/python is a SYMLINK to the base
    # interpreter outside the venv, so resolving it silently leaves the venv
    # behind and every import of cadquery fails. That is a very confusing way to
    # lose an environment.
    python = os.path.abspath(python or sys.executable)
    # Absolute, always. The generated script runs with cwd set to its own work
    # directory, so a relative outdir gets resolved against that directory and
    # the path doubles - "..._work-P06/exports/.../_work-P06/gen.py". That cost
    # a 36-minute run, because the loop happily fed the resulting "can't open
    # file" back to the model as though the model had written it.
    outdir = pathlib.Path(outdir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    workdir = outdir / ("_work-%s" % spec.id)
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    # Clear this part's previous deliverables before starting. Without this a
    # failed run leaves the LAST run's passing STEP sitting in the export
    # directory with nothing to mark it stale, and the next person to open it
    # has no way to tell it is not what the run just produced.
    # Exact names, not a "<id>*" glob. A prefix glob would sweep another part's
    # validated deliverables whenever one id is a prefix of another - building
    # "P01-plate" would delete "P01-plate-v2.step" sitting beside it.
    for name in ("%s.step", "%s.stl", "%s.py",
                 "%s-best.step", "%s-best.stl", "%s-best.py",
                 "%s-REJECTED.step", "%s-REJECTED.stl", "%s-REJECTED.py",
                 "%s-run.json"):
        stale = outdir / (name % spec.id)
        if stale.is_file():
            stale.unlink()

    # The model authors in the spec's units (inches here). `step`/`stl` are that
    # raw output; `mm_step`/`mm_stl` are the millimetre-correct conversion, and
    # those are what get measured, checked and delivered - so the file that is
    # validated is the file that leaves the building.
    step = workdir / ("%s-authored.step" % spec.id)
    stl = workdir / ("%s-authored.stl" % spec.id)
    mm_step = workdir / ("%s.step" % spec.id)
    mm_stl = workdir / ("%s.stl" % spec.id)
    script = workdir / ("%s_gen.py" % spec.id)

    task = ("Build a 3D solid model of this part with CadQuery.\n\n"
            "STEP_PATH = %r\nSTL_PATH = %r\n\n"
            "--- SPEC ---\n%s\n--- END SPEC ---\n\n"
            "Build exactly what the spec describes. Every stated dimension must "
            "be exact." % (str(step), str(stl), spec.brief()))

    result = {"spec": spec.id, "name": spec.name, "model": model,
              "provider": provider.name, "attempts": [], "ok": False,
              "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    best = {"errors": 10 ** 9}
    prev_err = prev_code = None
    last_code, stuck, temp = None, 0, temperature

    for attempt in range(1, max_attempts + 1):
        rec = {"n": attempt}
        log("  attempt %d/%d" % (attempt, max_attempts))

        prompt = _prompt_for(task, prev_err, prev_code, stuck)

        try:
            raw, secs, usage = provider.chat(SYSTEM, prompt, model,
                                             temperature=temp, timeout=timeout)
        except Exception as e:
            rec.update(stage="model", error=str(e))
            result["attempts"].append(rec)
            log("    model call failed: %s" % e)
            time.sleep(3)
            continue
        rec["model_seconds"] = round(secs, 1)
        rec["tokens"] = usage.get("completion_tokens")

        code = extract_code(raw)

        # Stuck-detection runs BEFORE the empty-reply branch. When it ran after,
        # a model returning nothing twice never escalated - it `continue`d past
        # this - and `last_code` went stale, so the next real reply was compared
        # against something several attempts old.
        if code == last_code:
            stuck += 1
            temp = min(temperature + 0.25 * stuck, 0.9)
            log("    identical output (stuck x%d) -> temperature %.2f" % (stuck, temp))
        else:
            # Reset the temperature too, not just the counter. Leaving it
            # ratcheted meant one stuck episode on attempt 2 ran every later
            # attempt at 0.90 regardless of --temperature, long after the model
            # had started varying its output again.
            stuck = 0
            temp = temperature
        last_code = code

        if not code:
            prev_err, prev_code = "You returned no code block at all.", ""
            rec.update(stage="extract", error="no code block")
            result["attempts"].append(rec)
            continue

        refusals = guard(code)
        if refusals:
            prev_err = "\n".join("%d. %s" % (i, m) for i, m in enumerate(refusals, 1))
            prev_code = code
            rec.update(stage="guard", error=prev_err)
            result["attempts"].append(rec)
            log("    refused: %s" % refusals[0])
            continue

        script.write_text(code)
        for f in (step, stl):
            if f.exists():
                f.unlink()

        rc, out = run_sandboxed(script, workdir, python, timeout=timeout)
        if rc != 0 and _is_our_fault(out):
            # Never spend the model's attempts on our own bug. Retrying this
            # cannot help, and the failure reads like the model's code to
            # anyone reading the log later.
            raise HarnessFault(
                "bncad could not run the generated script - this is a harness "
                "fault, not a model error:\n%s" % out)
        if rc != 0:
            prev_err, prev_code = _tail(out), code
            rec.update(stage="execute", rc=rc, error=prev_err)
            result["attempts"].append(rec)
            log("    execution failed rc=%d" % rc)
            continue
        if not step.exists():
            prev_err = ("The script exited 0 but wrote no STEP file at %s. "
                        "Call exporters.export(result, STEP_PATH)." % step)
            prev_code = code
            rec.update(stage="export", error=prev_err)
            result["attempts"].append(rec)
            log("    no STEP written")
            continue

        from . import spec as spec_mod
        try:
            spec_mod.to_delivery(step, mm_step, mm_stl, spec.scale)
            m = spec_mod.measure(mm_step, mm_stl, scale=spec.scale)
        except Exception as e:
            prev_err = ("The exported STEP will not re-open: %s. The solid is "
                        "malformed." % e)
            prev_code = code
            rec.update(stage="measure", error=prev_err)
            result["attempts"].append(rec)
            continue

        errs = spec.check(m)
        rec["measured"] = m
        rec["errors"] = errs
        result["attempts"].append(rec)

        if len(errs) < best["errors"]:
            best = {"errors": len(errs), "code": code, "measured": m}
            _promote(spec, outdir, mm_step, mm_stl, script, suffix="-best")

        if errs:
            prev_err = "VALIDATION FAILED:\n" + "\n".join(
                "%d. %s" % (i, e) for i, e in enumerate(errs, 1))
            prev_code = code
            log("    %d check(s) failed" % len(errs))
            for e in errs[:3]:
                log("      - %s" % e[:150])
            continue

        _promote(spec, outdir, mm_step, mm_stl, script)
        result.update(ok=True, attempt=attempt, measured=m,
                      report=spec.report(m))
        log("    PASS on attempt %d - %s" % (attempt, spec.report(m)))
        break

    result["best_errors"] = None if best["errors"] > 10 ** 8 else best["errors"]
    result["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    # "-best" means "the least wrong attempt", which reads far too much like
    # "the best available part" to leave sitting in an export directory. On a
    # pass it is a duplicate of the deliverable, so delete it; on a failure
    # rename it to -REJECTED, which nobody will mistake for something to send.
    for ext in (".step", ".stl", ".py"):
        best_file = outdir / ("%s-best%s" % (spec.id, ext))
        if not best_file.exists():
            continue
        if result["ok"]:
            best_file.unlink()
        else:
            best_file.replace(outdir / ("%s-REJECTED%s" % (spec.id, ext)))

    if not keep_workdir and result["ok"]:
        shutil.rmtree(workdir, ignore_errors=True)
    (outdir / ("%s-run.json" % spec.id)).write_text(
        json.dumps(result, indent=2, default=float))
    return result


def _promote(spec, outdir, step, stl, script, suffix=""):
    """Copy a run's artefacts out of the scratch dir into the export dir."""
    for src, ext in ((step, ".step"), (stl, ".stl"), (script, ".py")):
        if src.exists():
            shutil.copyfile(src, outdir / ("%s%s%s" % (spec.id, suffix, ext)))


def demo():
    assert extract_code("blah ```python\nx=1\n``` more") == "x=1"
    assert extract_code("```\na\n```\ntext\n```python\nb\n```") == "b", \
        "the LAST block wins - models sketch before they answer"
    assert extract_code("bare code") == "bare code"

    assert guard("import cadquery as cq\nx=1") == []
    assert guard("import math, json\n") == []
    assert "subprocess" in guard("import subprocess")[0]
    assert "socket" in guard("from socket import socket")[0]
    assert "eval" in guard("eval('1')")[0]
    assert "open" in guard("open('/etc/passwd')")[0]
    assert "does not parse" in guard("def (:")[0]
    # A method named like a banned builtin is not a banned call.
    assert guard("import cadquery as cq\ncq.Workplane('XY').val().Volume()") == []

    assert _tail("a\n\nb\nc", lines=2) == "b\nc"

    assert _is_our_fault("python: can't open file '/x/y.py'")
    assert _is_our_fault("ModuleNotFoundError: No module named 'cadquery'")
    # A traceback from the model's own code must NOT be blamed on the harness.
    assert not _is_our_fault(
        "ValueError: Selected faces must be co-planar.")
    assert not _is_our_fault("OCP.Standard.Standard_Failure: BRep_API: command not done")
    # The model exporting into a directory it never created is ITS bug to fix,
    # and aborting the run on it wastes the whole build.
    assert not _is_our_fault(
        "FileNotFoundError: [Errno 2] No such file or directory: 'out/p.step'")

    assert _prompt_for("TASK", None, None, 0) == "TASK"
    repair = _prompt_for("TASK", "ERR", "OLDCODE", 0)
    assert "OLDCODE" in repair and "ERR" in repair
    # Once stuck, the failed script must be gone from the prompt entirely.
    reset = _prompt_for("TASK", "ERR", "OLDCODE", 2)
    assert "OLDCODE" not in reset, "a stuck retry must not re-show the failed script"
    assert "ERR" in reset and "SHAPE" in reset
    print("loop demo ok")


if __name__ == "__main__":
    demo()
