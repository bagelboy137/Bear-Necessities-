#!/usr/bin/env python3
"""Host-side driver for Fusion marketing renders.

Writes a render job, fires it inside Fusion over the MCP bridge, then polls for
the output files. Fusion queues local renders one at a time and runs them in a
background process that outlives any single MCP call, so polling for files is the
only reliable completion signal.

    python3 render_module.py --module BN-M01 --views hero front detail
    python3 render_module.py --sweep scene-variants.json --module BN-M01
    python3 render_module.py --all

Requires Fusion running and signed in, with the MCP server enabled
(Preferences > General > API > Fusion MCP Server). There is no headless mode on
macOS - this is the one constraint the render path cannot design around.

TWO OPERATIONAL HAZARDS, both learned the hard way on 2026-08-26:

1. Fusion's MCP server stops answering for the duration of a render (curl returns
   000, then 405 again once the queue drains). Do not read that as Fusion having
   died. The RenderLock below keeps two drivers from overlapping because of it.

2. Killing this driver does NOT cancel the renders. Fusion has already accepted
   them and will finish them in its own time, overwriting the output files
   minutes later - long after you think the run is dead. That produced several
   measurements of images that had been silently replaced underneath the scoring
   pass. After killing a driver, wait for the render directory to stop changing
   before trusting anything in it.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
STUDY = HERE.parent
EXPORTS_ROOT = STUDY / "fusion-native" / "exports"
RENDER_DIR = HERE / "renders"
JOB_PATH = HERE / "render-job.json"
RESULT_PATH = HERE / "render-job-result.json"
FUSION_SCRIPT = HERE / "fusion_render.py"
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]

# Resolve the bridge the same way build.sh resolves everything: walk up to the
# Claude root rather than hard-coding a home directory.
def _claude_root():
    for parent in HERE.resolve().parents:
        if (parent / "Fusion CAD Agent").is_dir() and (parent / "Mac Mini Setup").is_dir():
            return parent
    raise SystemExit("could not discover the Claude root from %s" % HERE)


BRIDGE = _claude_root() / "Fusion CAD Agent" / "bridge" / "fusion_mcp.py"


sys.path.insert(0, str(_claude_root() / "Fusion CAD Agent" / "bridge"))
from fusion_port import discover as _discover, speaks_mcp as _answers  # noqa: E402


def discover_mcp_url(default="http://127.0.0.1:27182/mcp"):
    """Where is Fusion's MCP server really? See bridge/fusion_port.py.

    One implementation, shared with preflight.py, build.sh and fusion_mcp.py -
    the port moves, and four copies of the search would drift.
    """
    return _discover(default=default, configured="auto")


BASE_SCENE = {
    # Tuned on BN-M01 over three sweeps, 2026-08-26. Photobooth is the only
    # environment that is a photographic backdrop rather than a studio light RIG:
    # the rig environments (Soft Light, Sharp Highlights, Rim Highlights, Grid
    # Light) render their own softbox geometry into frame when used as a visible
    # background. light_angle rotates the remaining bright lobe out of shot.
    # A flattened ground is what actually puts a floor under the product -
    # isGroundDisplayed alone renders nothing visible.
    "environment": "Photobooth",
    "ground": True,
    "ground_flattened": True,
    "ground_position": 0.0,
    "brightness": 1200.0,
    "exposure": 8.2,
    "focal_length": 85.0,
    "light_angle": 1.2,
    "quality": 75,
    # Multiple of the 36.06 in body diagonal. Smaller is closer. viewExtents-based
    # zoom does not work - see _apply_camera in fusion_render.py.
    "distance_factor": 0.95,
    # Measured, not guessed: with the target at the module's geometric centre the
    # subject lands 206 px BELOW frame centre (0.115 of height) on both BN-M01 and
    # BN-M02 - identical to three decimals, so it is the scene, not the module.
    # Worse, the subject's bottom edge sits 36 px off the frame edge, which puts
    # the ground under the module out of shot entirely and is why the contact
    # shadow measured 1.239 (brighter than the floor beside it) on both. Dropping
    # the aim point ~4 in raises the subject in frame and opens the floor beneath
    # it, which is the same fix for both failures.
    "target_offset_in": [0.0, 0.0, -4.1],
}

VIEW_OUTPUT = {
    "hero": {"width": 2400, "height": 1800},
    "front": {"width": 1600, "height": 1200, "distance_factor": 1.5},
    "detail": {"width": 1600, "height": 1200, "distance_factor": 0.8},
    "alpha": {"width": 2400, "height": 1800, "transparent": True, "ground": False,
              "ground_flattened": False},
}


LOCK_PATH = HERE / ".render.lock"


class RenderLock:
    """One driver at a time.

    Fusion queues local renders internally, but its MCP server stops answering
    while a render is running (observed 2026-08-26: curl returned 000 for the
    duration, then 405 again once the queue drained). Two overlapping drivers
    therefore fight - the second deletes the first's output files before its own
    job is accepted, and both end up with nothing.
    """

    def __init__(self, path=LOCK_PATH, stale_seconds=7200):
        self.path, self.stale_seconds = path, stale_seconds

    def __enter__(self):
        if self.path.exists():
            age = time.time() - self.path.stat().st_mtime
            if age < self.stale_seconds:
                raise SystemExit(
                    "another render driver holds %s (started %.0fs ago). Renders "
                    "must be serial; wait for it or delete the lock if it died."
                    % (self.path, age))
            print("clearing a stale render lock (%.0fs old)" % age)
        self.path.write_text(str(os.getpid()))
        return self

    def __exit__(self, *_):
        self.path.unlink(missing_ok=True)


PROGRESS_PATH = HERE / "render-progress.json"


TELEMETRY_PATH = HERE / "render-telemetry.json"

# Fusion leaks across renders on this machine. Rather than waiting for the crash,
# recycle it proactively while it is still healthy. Tuned below from measurement.
# One module per Fusion instance. Measured 2026-08-26: importing an F3D into a
# freshly launched Fusion takes 10s and works every time; importing into an
# instance that has already rendered wedges it permanently - the process stays
# alive at ~0% CPU and every subsequent API call hangs until it is killed. So a
# render session is deliberately short-lived. Restarting costs ~90s, which is
# cheaper than one wedge.
RECYCLE_AFTER_RENDERS = 3
RECYCLE_ABOVE_RSS_GB = 3.0
MIN_FREE_PERCENT = 25
# Load average is a BAD guard for this workload and was originally set far too
# low. Fusion's ray tracer is heavily threaded: a single render pegs ~9 of 10
# cores and drives the 1-minute load average past 70 while free memory sits at
# 75% and nothing is thrashing. A ceiling of 12 blocked on load the render itself
# created, and the sweep deadlocked waiting for a quiet machine that its own work
# was preventing. Free memory is the signal that actually matters here; this is
# kept only to catch a genuinely wedged machine.
MAX_LOAD = 120.0
COOLDOWN_SECONDS = 12
BRIDGE_TIMEOUT = 120


# The main application binary. Used for "is Fusion up?" and for health probes.
FUSION_MAIN = "Autodesk Fusion.app/Contents/MacOS"
# Everything Fusion spawns, including Contents/Libraries helpers. The local
# render worker lives there, and it does NOT die with its parent: killing only
# the main binary orphans a worker that keeps ~9 of 10 cores busy indefinitely
# (observed 2026-08-26: PID reparented to 1, 888% CPU, 12 minutes and counting,
# producing nothing). Recycling has to take the whole tree.
FUSION_ALL = "Autodesk Fusion.app/Contents"


def fusion_pids(pattern=FUSION_MAIN):
    try:
        return subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True, timeout=10).stdout.split()
    except (FileNotFoundError, subprocess.SubprocessError):
        return []


def fusion_rss_gb():
    """Resident memory of the main Fusion process, in GB."""
    pids = fusion_pids()
    if not pids:
        return 0.0
    try:
        out = subprocess.run(["ps", "-o", "rss=", "-p", pids[0]],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip() or 0) / 1048576.0
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return 0.0


def memory_free_percent():
    """Same probe the local-model framework uses, for one consistent signal."""
    try:
        out = subprocess.run(["memory_pressure", "-Q"], capture_output=True,
                             text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", out)
    return int(match.group(1)) if match else None


def health():
    return {"fusion_rss_gb": round(fusion_rss_gb(), 2),
            "free_percent": memory_free_percent(),
            "load": round(os.getloadavg()[0], 2)}


def wait_for_headroom(timeout=900):
    """Do not start a render into a machine that is already under pressure.

    The local-model side of this project learned the same lesson the hard way:
    starting heavy work without checking free memory is how a 16 GB laptop panics.
    """
    started = time.time()
    announced = False
    while time.time() - started < timeout:
        state = health()
        free, load = state["free_percent"], state["load"]
        if (free is None or free >= MIN_FREE_PERCENT) and load <= MAX_LOAD:
            if announced:
                _say("        headroom ok: free=%s%% load=%.2f" % (free, load))
            return True
        if not announced:
            _say("        waiting for headroom: free=%s%%/%d load=%.2f/%.1f"
                 % (free, MIN_FREE_PERCENT, load, MAX_LOAD))
            announced = True
        time.sleep(15)
    return False


def _clear_crash_flag():
    """Tell Autodesk's crash reporter there is nothing to report.

    CEROption.xml accumulates CrashCount and SessionCleanCloseCount. After an
    unclean shutdown Fusion shows a modal "send report?" dialog on next launch,
    and a modal dialog blocks EVERY API script - which is the wedge this pipeline
    kept hitting. Resetting the counters after we deliberately kill Fusion stops
    our own recycling from arming that dialog against us.

    Only the counters are touched; the file is left otherwise intact.
    """
    import re as _re
    base = pathlib.Path.home() / "Library/Application Support/Autodesk/Autodesk Fusion 360"
    for path in base.glob("*/CEROption.xml"):
        try:
            raw = path.read_bytes().decode("utf-16", errors="ignore")
            fixed = _re.sub(r"<CrashCount>\s*\d+\s*</CrashCount>",
                            "<CrashCount>0</CrashCount>", raw)
            fixed = _re.sub(r"<SessionCleanCloseCount>\s*\d+\s*</SessionCleanCloseCount>",
                            "<SessionCleanCloseCount>1</SessionCleanCloseCount>", fixed)
            if fixed != raw:
                # Record what we are about to erase. Resetting CrashCount stops
                # the modal dialog, but it also destroys the one number that says
                # whether this pipeline is still crashing Fusion. Keep it.
                before = _re.search(r"<CrashCount>\s*(\d+)\s*</CrashCount>", raw)
                if before and before.group(1) != "0":
                    _say("        note: Fusion CrashCount was %s before reset"
                         % before.group(1))
                    try:
                        log = HERE / "fusion-crash-history.json"
                        history = json.loads(log.read_text()) if log.is_file() else []
                        history.append({"crash_count": int(before.group(1)),
                                        "cleared_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
                        log.write_text(json.dumps(history, indent=2) + "\n")
                    except Exception:
                        pass
                path.write_bytes(fixed.encode("utf-16"))
        except Exception:
            pass


def quit_fusion(grace=75):
    """Shut Fusion down as cleanly as it will allow.

    Order matters. A graceful quit records a clean close and leaves the crash
    reporter quiet; SIGKILL does not, and the resulting dialog wedges the next
    launch. So: ask nicely, then insist, then force - and clear the crash flag
    either way.
    """
    if not fusion_pids():
        return True
    try:                                        # ask nicely
        subprocess.run(["osascript", "-e", 'quit app "Autodesk Fusion"'],
                       timeout=25, capture_output=True)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    deadline = time.time() + grace
    while fusion_pids() and time.time() < deadline:
        time.sleep(3)
    for signal_name in ("-TERM", "-KILL"):      # then insist, then force
        if not fusion_pids(FUSION_ALL):
            break
        for pid in fusion_pids(FUSION_ALL):
            subprocess.run(["kill", signal_name, pid], timeout=10,
                           capture_output=True)
        stop = time.time() + 20
        while fusion_pids(FUSION_ALL) and time.time() < stop:
            time.sleep(2)
    # Sweep up any orphaned render worker that outlived the app.
    for pid in fusion_pids(FUSION_ALL):
        subprocess.run(["kill", "-9", pid], timeout=10, capture_output=True)
    _clear_crash_flag()
    return not fusion_pids(FUSION_ALL)


def restart_fusion(reason):
    """Recycle Fusion. The cure for both the leak and the wedge.

    Documents are never saved by this pipeline - every design is a throwaway
    import of a committed F3D - so a restart loses nothing.
    """
    _say("        recycling Fusion (%s)" % reason)
    quit_fusion()
    time.sleep(6)
    return ensure_fusion()


def fusion_alive():
    try:
        return bool(subprocess.run(
            ["pgrep", "-f", "Autodesk Fusion.app/Contents/MacOS"],
            capture_output=True, text=True, timeout=10).stdout.strip())
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def ensure_fusion(boot_timeout=240):
    """Get Fusion running with a reachable MCP server, launching it if needed.

    Fusion crashes under this workload - repeatedly. Rather than failing the run,
    bring it back and carry on. Returns the MCP URL, or None if it will not come
    up. Note that a relaunched Fusion often binds a DIFFERENT port, which is why
    the URL is rediscovered every time rather than cached.
    """
    if not fusion_alive():
        print("  Fusion is not running; launching it", flush=True)
        try:
            subprocess.run(["open", "-a", "Autodesk Fusion"], timeout=30,
                           capture_output=True)
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            print("  could not launch Fusion: %s" % exc, file=sys.stderr)
            return None
    started = time.time()
    while time.time() - started < boot_timeout:
        url = discover_mcp_url()
        if _answers(url):
            return url
        time.sleep(10)
    return None


PROBE_SCRIPT = """
def run(_context: str):
    import adsk.core
    app = adsk.core.Application.get()
    print("BN_PROBE_OK docs=%d" % app.documents.count)
"""


def can_execute(url, timeout=120):
    """Can Fusion actually RUN a script, not merely answer a handshake?

    This is the check that was missing, and it is the one that matters. Fusion
    does not only crash - it WEDGES. After the crash on 2026-08-26 it relaunched,
    bound its MCP port, completed the initialize handshake perfectly, and then
    never executed anything: 0.6% CPU, resident memory flat, every script call
    hanging until it timed out. A modal dialog on the main thread does that, and
    crash-recovery prompts are modal.

    An initialize handshake cannot tell a working Fusion from a wedged one. Only
    running a trivial script can.
    """
    probe = HERE / ".probe.py"
    probe.write_text(PROBE_SCRIPT)
    try:
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), "--url", url, "--exec-file", str(probe)],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    finally:
        probe.unlink(missing_ok=True)
    return "BN_PROBE_OK" in proc.stdout


def fusion_cpu():
    pids = fusion_pids()
    if not pids:
        return 0.0
    try:
        out = subprocess.run(["ps", "-o", "%cpu=", "-p", pids[0]],
                             capture_output=True, text=True, timeout=10).stdout
        return float(out.strip() or 0.0)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return 0.0


def wait_until_settled(min_age=75, quiet_cpu=6.0, quiet_samples=4, timeout=300):
    """Wait for Fusion to finish starting up before asking it to do real work.

    THIS is the fix for the wedge, and it took a step-trace to find. The trace
    stopped at "import:start" with nothing after it, on a Fusion that was 49
    seconds old and still burning 10% CPU. The identical import into an instance
    that had been up for a few minutes completed in 10 seconds, every time.

    An MCP handshake, and even a trivial script, succeed long before Fusion is
    actually ready - they need almost nothing. importToNewDocument needs the
    whole application, and calling it too early wedges the process permanently.

    So: require a minimum age AND several consecutive quiet CPU samples before
    the first real call.
    """
    started = time.time()
    quiet = 0
    while time.time() - started < timeout:
        age = time.time() - started
        cpu = fusion_cpu()
        if cpu <= quiet_cpu:
            quiet += 1
        else:
            quiet = 0
        if age >= min_age and quiet >= quiet_samples:
            _say("        Fusion settled (%.0fs, cpu %.1f%%)" % (age, cpu))
            return True
        time.sleep(8)
    _say("        Fusion never settled; proceeding anyway", err=True)
    return False


def healthy_fusion(attempts=3):
    """Return a URL to a Fusion that is up AND executing, recycling if it is not."""
    for attempt in range(1, attempts + 1):
        url = ensure_fusion()
        if url:
            wait_until_settled()
        if url and can_execute(url):
            return url
        if url is None:
            _say("        Fusion did not come up (attempt %d)" % attempt, err=True)
        else:
            _say("        Fusion answers MCP but will not execute - wedged, "
                 "recycling (attempt %d)" % attempt, err=True)
        restart_fusion("wedged or unreachable")
    return None


def load_progress():
    if PROGRESS_PATH.is_file():
        try:
            return json.loads(PROGRESS_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {"done": {}}


def save_progress(progress):
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2) + "\n")


def render_one(entries, url, timeout):
    """Fire one module's renders in a single bridge call, wait for the files.

    All of a module's views go in one call so the F3D is imported once, not once
    per view. The import is the operation that wedges Fusion, so halving the
    number of them halves the exposure.
    """
    if isinstance(entries, dict):
        entries = [entries]
    job = build_job(entries)
    JOB_PATH.write_text(json.dumps(job, indent=2) + "\n")
    if RESULT_PATH.exists():
        RESULT_PATH.unlink()
    targets = [str(RENDER_DIR / (e["name"] + ".png")) for e in entries]
    # Inject this machine's job path into the script before sending it. The
    # bridge transmits contents, not a path, so the Fusion side cannot work out
    # where it lives on its own.
    prepared = HERE / ".fusion_render.prepared.py"
    prepared.write_text(
        FUSION_SCRIPT.read_text().replace("__BN_JOB_PATH__", str(JOB_PATH)))
    try:
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), "--url", url,
             "--exec-file", str(prepared)],
            capture_output=True, text=True, timeout=BRIDGE_TIMEOUT)
    except subprocess.TimeoutExpired:
        # The script only FIRES the render and returns; it never waits for the
        # image. A call that takes longer than this is not slow, it is wedged.
        return False, "bridge call wedged (>%ds)" % BRIDGE_TIMEOUT
    if "RENDER_JOB_DONE" not in proc.stdout:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
        return False, "Fusion did not accept the job: %s" % tail[0][:160]
    done, missing = wait_for(targets, timeout=timeout, poll=5)
    if missing:
        return False, "did not produce %s" % ", ".join(p.name for p in missing)
    return True, "%d image(s), %d bytes" % (
        len(done), sum(done.values()))


def _say(message, err=False):
    """Print and flush. Python buffers stdout when it is not a tty, so an
    unattended run writes nothing to its log for an hour and looks hung."""
    print(message, file=sys.stderr if err else sys.stdout, flush=True)


def render_supervised(entries, timeout, attempts=3):
    """Render entries one at a time, and keep Fusion healthy while doing it.

    Three things keep it alive, in order of how much they matter:

    1. One document open at a time (enforced in fusion_render.py). Caching ten
       imported designs is what crashed the material-library service.
    2. Proactive recycling. Fusion's resident memory climbs across renders and
       does not come back down; restarting it every RECYCLE_AFTER_RENDERS renders,
       or whenever it passes RECYCLE_ABOVE_RSS_GB, retires the leak before it
       becomes a crash. Nothing is ever saved, so a restart costs only startup
       time.
    3. A headroom guard and a cool-down, so a render never starts into a machine
       that is already under memory pressure.

    Every render's before/after health is written to render-telemetry.json, which
    is what makes the leak visible instead of theoretical.
    """
    progress = load_progress()
    telemetry = []
    rendered, failed = [], []
    since_recycle = 0

    # Group by module: one import per module, all its views from that import.
    by_module = {}
    for entry in entries:
        by_module.setdefault(entry["module"], []).append(entry)
    groups = list(by_module.items())

    for index, (module_id, group) in enumerate(groups, 1):
        name = module_id
        outstanding = [e for e in group
                       if not (progress["done"].get(e["name"])
                               and (RENDER_DIR / (e["name"] + ".png")).is_file())]
        if not outstanding:
            _say("[%d/%d] %s already rendered, skipping" % (index, len(groups), name))
            rendered.append(name)
            continue

        for attempt in range(1, attempts + 1):
            before = health()
            if (since_recycle >= RECYCLE_AFTER_RENDERS
                    or before["fusion_rss_gb"] >= RECYCLE_ABOVE_RSS_GB):
                restart_fusion("%d renders done, rss %.2f GB"
                               % (since_recycle, before["fusion_rss_gb"]))
                since_recycle = 0
                before = health()
            url = healthy_fusion()
            if url is None:
                failed.append((name, "Fusion would not come up"))
                break
            if not wait_for_headroom():
                failed.append((name, "never got memory headroom"))
                break

            _say("[%d/%d] %s x%d views attempt %d  rss=%.2f GB free=%s%% port=%s"
                 % (index, len(groups), name, len(outstanding), attempt,
                    before["fusion_rss_gb"], before["free_percent"],
                    url.rsplit(":", 1)[-1].split("/")[0]))
            ok, note = render_one(outstanding, url, timeout)
            after = health()
            telemetry.append({"name": name, "attempt": attempt, "ok": ok,
                              "note": note, "before": before, "after": after,
                              "renders_since_recycle": since_recycle})
            TELEMETRY_PATH.write_text(json.dumps(telemetry, indent=2) + "\n")

            if ok:
                since_recycle += 1
                _say("        ok, %s  rss %.2f -> %.2f GB (%+.2f)"
                     % (note, before["fusion_rss_gb"], after["fusion_rss_gb"],
                        after["fusion_rss_gb"] - before["fusion_rss_gb"]))
                for e in outstanding:
                    path = RENDER_DIR / (e["name"] + ".png")
                    if path.is_file():
                        progress["done"][e["name"]] = {"bytes": path.stat().st_size}
                save_progress(progress)
                rendered.append(name)
                time.sleep(COOLDOWN_SECONDS)
                break

            _say("        failed: %s" % note, err=True)
            if not fusion_alive():
                _say("        Fusion died on this module", err=True)
                since_recycle = 0
            else:
                restart_fusion("recovering from a failed render")
                since_recycle = 0
            time.sleep(COOLDOWN_SECONDS)
        else:
            failed.append((name, "exhausted %d attempts" % attempts))

    return rendered, failed


def build_job(entries):
    return {
        "exports_root": str(EXPORTS_ROOT),
        "output_dir": str(RENDER_DIR),
        "renders": entries,
    }


LOCK_PATH = HERE / ".render.lock"


class RenderLock:
    """One driver at a time.

    Fusion queues local renders internally, but its MCP server stops answering
    while a render is running (observed 2026-08-26: curl returned 000 for the
    duration, then 405 again once the queue drained). Two overlapping drivers
    therefore fight - the second deletes the first's output files before its own
    job is accepted, and both end up with nothing.
    """

    def __init__(self, path=LOCK_PATH, stale_seconds=7200):
        self.path, self.stale_seconds = path, stale_seconds

    def __enter__(self):
        if self.path.exists():
            age = time.time() - self.path.stat().st_mtime
            if age < self.stale_seconds:
                raise SystemExit(
                    "another render driver holds %s (started %.0fs ago). Renders "
                    "must be serial; wait for it or delete the lock if it died."
                    % (self.path, age))
            print("clearing a stale render lock (%.0fs old)" % age)
        self.path.write_text(str(os.getpid()))
        return self

    def __exit__(self, *_):
        self.path.unlink(missing_ok=True)


PROGRESS_PATH = HERE / "render-progress.json"


TELEMETRY_PATH = HERE / "render-telemetry.json"

# Fusion leaks across renders on this machine. Rather than waiting for the crash,
# recycle it proactively while it is still healthy. Tuned below from measurement.
# One module per Fusion instance. Measured 2026-08-26: importing an F3D into a
# freshly launched Fusion takes 10s and works every time; importing into an
# instance that has already rendered wedges it permanently - the process stays
# alive at ~0% CPU and every subsequent API call hangs until it is killed. So a
# render session is deliberately short-lived. Restarting costs ~90s, which is
# cheaper than one wedge.
RECYCLE_AFTER_RENDERS = 3
RECYCLE_ABOVE_RSS_GB = 3.0
MIN_FREE_PERCENT = 25
MAX_LOAD = 12.0
COOLDOWN_SECONDS = 12
BRIDGE_TIMEOUT = 120


# The main application binary. Used for "is Fusion up?" and for health probes.
FUSION_MAIN = "Autodesk Fusion.app/Contents/MacOS"
# Everything Fusion spawns, including Contents/Libraries helpers. The local
# render worker lives there, and it does NOT die with its parent: killing only
# the main binary orphans a worker that keeps ~9 of 10 cores busy indefinitely
# (observed 2026-08-26: PID reparented to 1, 888% CPU, 12 minutes and counting,
# producing nothing). Recycling has to take the whole tree.
FUSION_ALL = "Autodesk Fusion.app/Contents"


def fusion_pids(pattern=FUSION_MAIN):
    try:
        return subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True, timeout=10).stdout.split()
    except (FileNotFoundError, subprocess.SubprocessError):
        return []


def fusion_rss_gb():
    """Resident memory of the main Fusion process, in GB."""
    pids = fusion_pids()
    if not pids:
        return 0.0
    try:
        out = subprocess.run(["ps", "-o", "rss=", "-p", pids[0]],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip() or 0) / 1048576.0
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return 0.0


def memory_free_percent():
    """Same probe the local-model framework uses, for one consistent signal."""
    try:
        out = subprocess.run(["memory_pressure", "-Q"], capture_output=True,
                             text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", out)
    return int(match.group(1)) if match else None


def health():
    return {"fusion_rss_gb": round(fusion_rss_gb(), 2),
            "free_percent": memory_free_percent(),
            "load": round(os.getloadavg()[0], 2)}


def wait_for_headroom(timeout=900):
    """Do not start a render into a machine that is already under pressure.

    The local-model side of this project learned the same lesson the hard way:
    starting heavy work without checking free memory is how a 16 GB laptop panics.
    """
    started = time.time()
    announced = False
    while time.time() - started < timeout:
        state = health()
        free, load = state["free_percent"], state["load"]
        if (free is None or free >= MIN_FREE_PERCENT) and load <= MAX_LOAD:
            if announced:
                _say("        headroom ok: free=%s%% load=%.2f" % (free, load))
            return True
        if not announced:
            _say("        waiting for headroom: free=%s%%/%d load=%.2f/%.1f"
                 % (free, MIN_FREE_PERCENT, load, MAX_LOAD))
            announced = True
        time.sleep(15)
    return False


def _clear_crash_flag():
    """Tell Autodesk's crash reporter there is nothing to report.

    CEROption.xml accumulates CrashCount and SessionCleanCloseCount. After an
    unclean shutdown Fusion shows a modal "send report?" dialog on next launch,
    and a modal dialog blocks EVERY API script - which is the wedge this pipeline
    kept hitting. Resetting the counters after we deliberately kill Fusion stops
    our own recycling from arming that dialog against us.

    Only the counters are touched; the file is left otherwise intact.
    """
    import re as _re
    base = pathlib.Path.home() / "Library/Application Support/Autodesk/Autodesk Fusion 360"
    for path in base.glob("*/CEROption.xml"):
        try:
            raw = path.read_bytes().decode("utf-16", errors="ignore")
            fixed = _re.sub(r"<CrashCount>\s*\d+\s*</CrashCount>",
                            "<CrashCount>0</CrashCount>", raw)
            fixed = _re.sub(r"<SessionCleanCloseCount>\s*\d+\s*</SessionCleanCloseCount>",
                            "<SessionCleanCloseCount>1</SessionCleanCloseCount>", fixed)
            if fixed != raw:
                # Record what we are about to erase. Resetting CrashCount stops
                # the modal dialog, but it also destroys the one number that says
                # whether this pipeline is still crashing Fusion. Keep it.
                before = _re.search(r"<CrashCount>\s*(\d+)\s*</CrashCount>", raw)
                if before and before.group(1) != "0":
                    _say("        note: Fusion CrashCount was %s before reset"
                         % before.group(1))
                    try:
                        log = HERE / "fusion-crash-history.json"
                        history = json.loads(log.read_text()) if log.is_file() else []
                        history.append({"crash_count": int(before.group(1)),
                                        "cleared_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
                        log.write_text(json.dumps(history, indent=2) + "\n")
                    except Exception:
                        pass
                path.write_bytes(fixed.encode("utf-16"))
        except Exception:
            pass


def quit_fusion(grace=75):
    """Shut Fusion down as cleanly as it will allow.

    Order matters. A graceful quit records a clean close and leaves the crash
    reporter quiet; SIGKILL does not, and the resulting dialog wedges the next
    launch. So: ask nicely, then insist, then force - and clear the crash flag
    either way.
    """
    if not fusion_pids():
        return True
    try:                                        # ask nicely
        subprocess.run(["osascript", "-e", 'quit app "Autodesk Fusion"'],
                       timeout=25, capture_output=True)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    deadline = time.time() + grace
    while fusion_pids() and time.time() < deadline:
        time.sleep(3)
    for signal_name in ("-TERM", "-KILL"):      # then insist, then force
        if not fusion_pids(FUSION_ALL):
            break
        for pid in fusion_pids(FUSION_ALL):
            subprocess.run(["kill", signal_name, pid], timeout=10,
                           capture_output=True)
        stop = time.time() + 20
        while fusion_pids(FUSION_ALL) and time.time() < stop:
            time.sleep(2)
    # Sweep up any orphaned render worker that outlived the app.
    for pid in fusion_pids(FUSION_ALL):
        subprocess.run(["kill", "-9", pid], timeout=10, capture_output=True)
    _clear_crash_flag()
    return not fusion_pids(FUSION_ALL)


def restart_fusion(reason):
    """Recycle Fusion. The cure for both the leak and the wedge.

    Documents are never saved by this pipeline - every design is a throwaway
    import of a committed F3D - so a restart loses nothing.
    """
    _say("        recycling Fusion (%s)" % reason)
    quit_fusion()
    time.sleep(6)
    return ensure_fusion()


def fusion_alive():
    try:
        return bool(subprocess.run(
            ["pgrep", "-f", "Autodesk Fusion.app/Contents/MacOS"],
            capture_output=True, text=True, timeout=10).stdout.strip())
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def ensure_fusion(boot_timeout=240):
    """Get Fusion running with a reachable MCP server, launching it if needed.

    Fusion crashes under this workload - repeatedly. Rather than failing the run,
    bring it back and carry on. Returns the MCP URL, or None if it will not come
    up. Note that a relaunched Fusion often binds a DIFFERENT port, which is why
    the URL is rediscovered every time rather than cached.
    """
    if not fusion_alive():
        print("  Fusion is not running; launching it", flush=True)
        try:
            subprocess.run(["open", "-a", "Autodesk Fusion"], timeout=30,
                           capture_output=True)
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            print("  could not launch Fusion: %s" % exc, file=sys.stderr)
            return None
    started = time.time()
    while time.time() - started < boot_timeout:
        url = discover_mcp_url()
        if _answers(url):
            return url
        time.sleep(10)
    return None


PROBE_SCRIPT = """
def run(_context: str):
    import adsk.core
    app = adsk.core.Application.get()
    print("BN_PROBE_OK docs=%d" % app.documents.count)
"""


def can_execute(url, timeout=120):
    """Can Fusion actually RUN a script, not merely answer a handshake?

    This is the check that was missing, and it is the one that matters. Fusion
    does not only crash - it WEDGES. After the crash on 2026-08-26 it relaunched,
    bound its MCP port, completed the initialize handshake perfectly, and then
    never executed anything: 0.6% CPU, resident memory flat, every script call
    hanging until it timed out. A modal dialog on the main thread does that, and
    crash-recovery prompts are modal.

    An initialize handshake cannot tell a working Fusion from a wedged one. Only
    running a trivial script can.
    """
    probe = HERE / ".probe.py"
    probe.write_text(PROBE_SCRIPT)
    try:
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), "--url", url, "--exec-file", str(probe)],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    finally:
        probe.unlink(missing_ok=True)
    return "BN_PROBE_OK" in proc.stdout


def fusion_cpu():
    pids = fusion_pids()
    if not pids:
        return 0.0
    try:
        out = subprocess.run(["ps", "-o", "%cpu=", "-p", pids[0]],
                             capture_output=True, text=True, timeout=10).stdout
        return float(out.strip() or 0.0)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return 0.0


def wait_until_settled(min_age=75, quiet_cpu=6.0, quiet_samples=4, timeout=300):
    """Wait for Fusion to finish starting up before asking it to do real work.

    THIS is the fix for the wedge, and it took a step-trace to find. The trace
    stopped at "import:start" with nothing after it, on a Fusion that was 49
    seconds old and still burning 10% CPU. The identical import into an instance
    that had been up for a few minutes completed in 10 seconds, every time.

    An MCP handshake, and even a trivial script, succeed long before Fusion is
    actually ready - they need almost nothing. importToNewDocument needs the
    whole application, and calling it too early wedges the process permanently.

    So: require a minimum age AND several consecutive quiet CPU samples before
    the first real call.
    """
    started = time.time()
    quiet = 0
    while time.time() - started < timeout:
        age = time.time() - started
        cpu = fusion_cpu()
        if cpu <= quiet_cpu:
            quiet += 1
        else:
            quiet = 0
        if age >= min_age and quiet >= quiet_samples:
            _say("        Fusion settled (%.0fs, cpu %.1f%%)" % (age, cpu))
            return True
        time.sleep(8)
    _say("        Fusion never settled; proceeding anyway", err=True)
    return False


def healthy_fusion(attempts=3):
    """Return a URL to a Fusion that is up AND executing, recycling if it is not."""
    for attempt in range(1, attempts + 1):
        url = ensure_fusion()
        if url:
            wait_until_settled()
        if url and can_execute(url):
            return url
        if url is None:
            _say("        Fusion did not come up (attempt %d)" % attempt, err=True)
        else:
            _say("        Fusion answers MCP but will not execute - wedged, "
                 "recycling (attempt %d)" % attempt, err=True)
        restart_fusion("wedged or unreachable")
    return None


def load_progress():
    if PROGRESS_PATH.is_file():
        try:
            return json.loads(PROGRESS_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {"done": {}}


def save_progress(progress):
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2) + "\n")


def render_one(entries, url, timeout):
    """Fire one module's renders in a single bridge call, wait for the files.

    All of a module's views go in one call so the F3D is imported once, not once
    per view. The import is the operation that wedges Fusion, so halving the
    number of them halves the exposure.
    """
    if isinstance(entries, dict):
        entries = [entries]
    job = build_job(entries)
    JOB_PATH.write_text(json.dumps(job, indent=2) + "\n")
    if RESULT_PATH.exists():
        RESULT_PATH.unlink()
    targets = [str(RENDER_DIR / (e["name"] + ".png")) for e in entries]
    # Inject this machine's job path into the script before sending it. The
    # bridge transmits contents, not a path, so the Fusion side cannot work out
    # where it lives on its own.
    prepared = HERE / ".fusion_render.prepared.py"
    prepared.write_text(
        FUSION_SCRIPT.read_text().replace("__BN_JOB_PATH__", str(JOB_PATH)))
    try:
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), "--url", url,
             "--exec-file", str(prepared)],
            capture_output=True, text=True, timeout=BRIDGE_TIMEOUT)
    except subprocess.TimeoutExpired:
        # The script only FIRES the render and returns; it never waits for the
        # image. A call that takes longer than this is not slow, it is wedged.
        return False, "bridge call wedged (>%ds)" % BRIDGE_TIMEOUT
    if "RENDER_JOB_DONE" not in proc.stdout:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
        return False, "Fusion did not accept the job: %s" % tail[0][:160]
    done, missing = wait_for(targets, timeout=timeout, poll=5)
    if missing:
        return False, "did not produce %s" % ", ".join(p.name for p in missing)
    return True, "%d image(s), %d bytes" % (
        len(done), sum(done.values()))


def _say(message, err=False):
    """Print and flush. Python buffers stdout when it is not a tty, so an
    unattended run writes nothing to its log for an hour and looks hung."""
    print(message, file=sys.stderr if err else sys.stdout, flush=True)


def render_supervised(entries, timeout, attempts=3):
    """Render entries one at a time, and keep Fusion healthy while doing it.

    Three things keep it alive, in order of how much they matter:

    1. One document open at a time (enforced in fusion_render.py). Caching ten
       imported designs is what crashed the material-library service.
    2. Proactive recycling. Fusion's resident memory climbs across renders and
       does not come back down; restarting it every RECYCLE_AFTER_RENDERS renders,
       or whenever it passes RECYCLE_ABOVE_RSS_GB, retires the leak before it
       becomes a crash. Nothing is ever saved, so a restart costs only startup
       time.
    3. A headroom guard and a cool-down, so a render never starts into a machine
       that is already under memory pressure.

    Every render's before/after health is written to render-telemetry.json, which
    is what makes the leak visible instead of theoretical.
    """
    progress = load_progress()
    telemetry = []
    rendered, failed = [], []
    since_recycle = 0

    # Group by module: one import per module, all its views from that import.
    by_module = {}
    for entry in entries:
        by_module.setdefault(entry["module"], []).append(entry)
    groups = list(by_module.items())

    for index, (module_id, group) in enumerate(groups, 1):
        name = module_id
        outstanding = [e for e in group
                       if not (progress["done"].get(e["name"])
                               and (RENDER_DIR / (e["name"] + ".png")).is_file())]
        if not outstanding:
            _say("[%d/%d] %s already rendered, skipping" % (index, len(groups), name))
            rendered.append(name)
            continue

        for attempt in range(1, attempts + 1):
            before = health()
            if (since_recycle >= RECYCLE_AFTER_RENDERS
                    or before["fusion_rss_gb"] >= RECYCLE_ABOVE_RSS_GB):
                restart_fusion("%d renders done, rss %.2f GB"
                               % (since_recycle, before["fusion_rss_gb"]))
                since_recycle = 0
                before = health()
            url = healthy_fusion()
            if url is None:
                failed.append((name, "Fusion would not come up"))
                break
            if not wait_for_headroom():
                failed.append((name, "never got memory headroom"))
                break

            _say("[%d/%d] %s x%d views attempt %d  rss=%.2f GB free=%s%% port=%s"
                 % (index, len(groups), name, len(outstanding), attempt,
                    before["fusion_rss_gb"], before["free_percent"],
                    url.rsplit(":", 1)[-1].split("/")[0]))
            ok, note = render_one(outstanding, url, timeout)
            after = health()
            telemetry.append({"name": name, "attempt": attempt, "ok": ok,
                              "note": note, "before": before, "after": after,
                              "renders_since_recycle": since_recycle})
            TELEMETRY_PATH.write_text(json.dumps(telemetry, indent=2) + "\n")

            if ok:
                since_recycle += 1
                _say("        ok, %s  rss %.2f -> %.2f GB (%+.2f)"
                     % (note, before["fusion_rss_gb"], after["fusion_rss_gb"],
                        after["fusion_rss_gb"] - before["fusion_rss_gb"]))
                for e in outstanding:
                    path = RENDER_DIR / (e["name"] + ".png")
                    if path.is_file():
                        progress["done"][e["name"]] = {"bytes": path.stat().st_size}
                save_progress(progress)
                rendered.append(name)
                time.sleep(COOLDOWN_SECONDS)
                break

            _say("        failed: %s" % note, err=True)
            if not fusion_alive():
                _say("        Fusion died on this module", err=True)
                since_recycle = 0
            else:
                restart_fusion("recovering from a failed render")
                since_recycle = 0
            time.sleep(COOLDOWN_SECONDS)
        else:
            failed.append((name, "exhausted %d attempts" % attempts))

    return rendered, failed


PROGRESS_PATH = HERE / "render-progress.json"


TELEMETRY_PATH = HERE / "render-telemetry.json"

# Fusion leaks across renders on this machine. Rather than waiting for the crash,
# recycle it proactively while it is still healthy. Tuned below from measurement.
# One module per Fusion instance. Measured 2026-08-26: importing an F3D into a
# freshly launched Fusion takes 10s and works every time; importing into an
# instance that has already rendered wedges it permanently - the process stays
# alive at ~0% CPU and every subsequent API call hangs until it is killed. So a
# render session is deliberately short-lived. Restarting costs ~90s, which is
# cheaper than one wedge.
RECYCLE_AFTER_RENDERS = 3
RECYCLE_ABOVE_RSS_GB = 3.0
MIN_FREE_PERCENT = 25
MAX_LOAD = 12.0
COOLDOWN_SECONDS = 12
BRIDGE_TIMEOUT = 120


# The main application binary. Used for "is Fusion up?" and for health probes.
FUSION_MAIN = "Autodesk Fusion.app/Contents/MacOS"
# Everything Fusion spawns, including Contents/Libraries helpers. The local
# render worker lives there, and it does NOT die with its parent: killing only
# the main binary orphans a worker that keeps ~9 of 10 cores busy indefinitely
# (observed 2026-08-26: PID reparented to 1, 888% CPU, 12 minutes and counting,
# producing nothing). Recycling has to take the whole tree.
FUSION_ALL = "Autodesk Fusion.app/Contents"


def fusion_pids(pattern=FUSION_MAIN):
    try:
        return subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True, timeout=10).stdout.split()
    except (FileNotFoundError, subprocess.SubprocessError):
        return []


def fusion_rss_gb():
    """Resident memory of the main Fusion process, in GB."""
    pids = fusion_pids()
    if not pids:
        return 0.0
    try:
        out = subprocess.run(["ps", "-o", "rss=", "-p", pids[0]],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip() or 0) / 1048576.0
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return 0.0


def memory_free_percent():
    """Same probe the local-model framework uses, for one consistent signal."""
    try:
        out = subprocess.run(["memory_pressure", "-Q"], capture_output=True,
                             text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", out)
    return int(match.group(1)) if match else None


def health():
    return {"fusion_rss_gb": round(fusion_rss_gb(), 2),
            "free_percent": memory_free_percent(),
            "load": round(os.getloadavg()[0], 2)}


def wait_for_headroom(timeout=900):
    """Do not start a render into a machine that is already under pressure.

    The local-model side of this project learned the same lesson the hard way:
    starting heavy work without checking free memory is how a 16 GB laptop panics.
    """
    started = time.time()
    announced = False
    while time.time() - started < timeout:
        state = health()
        free, load = state["free_percent"], state["load"]
        if (free is None or free >= MIN_FREE_PERCENT) and load <= MAX_LOAD:
            if announced:
                _say("        headroom ok: free=%s%% load=%.2f" % (free, load))
            return True
        if not announced:
            _say("        waiting for headroom: free=%s%%/%d load=%.2f/%.1f"
                 % (free, MIN_FREE_PERCENT, load, MAX_LOAD))
            announced = True
        time.sleep(15)
    return False


def _clear_crash_flag():
    """Tell Autodesk's crash reporter there is nothing to report.

    CEROption.xml accumulates CrashCount and SessionCleanCloseCount. After an
    unclean shutdown Fusion shows a modal "send report?" dialog on next launch,
    and a modal dialog blocks EVERY API script - which is the wedge this pipeline
    kept hitting. Resetting the counters after we deliberately kill Fusion stops
    our own recycling from arming that dialog against us.

    Only the counters are touched; the file is left otherwise intact.
    """
    import re as _re
    base = pathlib.Path.home() / "Library/Application Support/Autodesk/Autodesk Fusion 360"
    for path in base.glob("*/CEROption.xml"):
        try:
            raw = path.read_bytes().decode("utf-16", errors="ignore")
            fixed = _re.sub(r"<CrashCount>\s*\d+\s*</CrashCount>",
                            "<CrashCount>0</CrashCount>", raw)
            fixed = _re.sub(r"<SessionCleanCloseCount>\s*\d+\s*</SessionCleanCloseCount>",
                            "<SessionCleanCloseCount>1</SessionCleanCloseCount>", fixed)
            if fixed != raw:
                # Record what we are about to erase. Resetting CrashCount stops
                # the modal dialog, but it also destroys the one number that says
                # whether this pipeline is still crashing Fusion. Keep it.
                before = _re.search(r"<CrashCount>\s*(\d+)\s*</CrashCount>", raw)
                if before and before.group(1) != "0":
                    _say("        note: Fusion CrashCount was %s before reset"
                         % before.group(1))
                    try:
                        log = HERE / "fusion-crash-history.json"
                        history = json.loads(log.read_text()) if log.is_file() else []
                        history.append({"crash_count": int(before.group(1)),
                                        "cleared_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
                        log.write_text(json.dumps(history, indent=2) + "\n")
                    except Exception:
                        pass
                path.write_bytes(fixed.encode("utf-16"))
        except Exception:
            pass


def quit_fusion(grace=75):
    """Shut Fusion down as cleanly as it will allow.

    Order matters. A graceful quit records a clean close and leaves the crash
    reporter quiet; SIGKILL does not, and the resulting dialog wedges the next
    launch. So: ask nicely, then insist, then force - and clear the crash flag
    either way.
    """
    if not fusion_pids():
        return True
    try:                                        # ask nicely
        subprocess.run(["osascript", "-e", 'quit app "Autodesk Fusion"'],
                       timeout=25, capture_output=True)
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    deadline = time.time() + grace
    while fusion_pids() and time.time() < deadline:
        time.sleep(3)
    for signal_name in ("-TERM", "-KILL"):      # then insist, then force
        if not fusion_pids(FUSION_ALL):
            break
        for pid in fusion_pids(FUSION_ALL):
            subprocess.run(["kill", signal_name, pid], timeout=10,
                           capture_output=True)
        stop = time.time() + 20
        while fusion_pids(FUSION_ALL) and time.time() < stop:
            time.sleep(2)
    # Sweep up any orphaned render worker that outlived the app.
    for pid in fusion_pids(FUSION_ALL):
        subprocess.run(["kill", "-9", pid], timeout=10, capture_output=True)
    _clear_crash_flag()
    return not fusion_pids(FUSION_ALL)


def restart_fusion(reason):
    """Recycle Fusion. The cure for both the leak and the wedge.

    Documents are never saved by this pipeline - every design is a throwaway
    import of a committed F3D - so a restart loses nothing.
    """
    _say("        recycling Fusion (%s)" % reason)
    quit_fusion()
    time.sleep(6)
    return ensure_fusion()


def fusion_alive():
    try:
        return bool(subprocess.run(
            ["pgrep", "-f", "Autodesk Fusion.app/Contents/MacOS"],
            capture_output=True, text=True, timeout=10).stdout.strip())
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def ensure_fusion(boot_timeout=240):
    """Get Fusion running with a reachable MCP server, launching it if needed.

    Fusion crashes under this workload - repeatedly. Rather than failing the run,
    bring it back and carry on. Returns the MCP URL, or None if it will not come
    up. Note that a relaunched Fusion often binds a DIFFERENT port, which is why
    the URL is rediscovered every time rather than cached.
    """
    if not fusion_alive():
        print("  Fusion is not running; launching it", flush=True)
        try:
            subprocess.run(["open", "-a", "Autodesk Fusion"], timeout=30,
                           capture_output=True)
        except (FileNotFoundError, subprocess.SubprocessError) as exc:
            print("  could not launch Fusion: %s" % exc, file=sys.stderr)
            return None
    started = time.time()
    while time.time() - started < boot_timeout:
        url = discover_mcp_url()
        if _answers(url):
            return url
        time.sleep(10)
    return None


PROBE_SCRIPT = """
def run(_context: str):
    import adsk.core
    app = adsk.core.Application.get()
    print("BN_PROBE_OK docs=%d" % app.documents.count)
"""


def can_execute(url, timeout=120):
    """Can Fusion actually RUN a script, not merely answer a handshake?

    This is the check that was missing, and it is the one that matters. Fusion
    does not only crash - it WEDGES. After the crash on 2026-08-26 it relaunched,
    bound its MCP port, completed the initialize handshake perfectly, and then
    never executed anything: 0.6% CPU, resident memory flat, every script call
    hanging until it timed out. A modal dialog on the main thread does that, and
    crash-recovery prompts are modal.

    An initialize handshake cannot tell a working Fusion from a wedged one. Only
    running a trivial script can.
    """
    probe = HERE / ".probe.py"
    probe.write_text(PROBE_SCRIPT)
    try:
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), "--url", url, "--exec-file", str(probe)],
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    finally:
        probe.unlink(missing_ok=True)
    return "BN_PROBE_OK" in proc.stdout


def fusion_cpu():
    pids = fusion_pids()
    if not pids:
        return 0.0
    try:
        out = subprocess.run(["ps", "-o", "%cpu=", "-p", pids[0]],
                             capture_output=True, text=True, timeout=10).stdout
        return float(out.strip() or 0.0)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        return 0.0


def wait_until_settled(min_age=75, quiet_cpu=6.0, quiet_samples=4, timeout=300):
    """Wait for Fusion to finish starting up before asking it to do real work.

    THIS is the fix for the wedge, and it took a step-trace to find. The trace
    stopped at "import:start" with nothing after it, on a Fusion that was 49
    seconds old and still burning 10% CPU. The identical import into an instance
    that had been up for a few minutes completed in 10 seconds, every time.

    An MCP handshake, and even a trivial script, succeed long before Fusion is
    actually ready - they need almost nothing. importToNewDocument needs the
    whole application, and calling it too early wedges the process permanently.

    So: require a minimum age AND several consecutive quiet CPU samples before
    the first real call.
    """
    started = time.time()
    quiet = 0
    while time.time() - started < timeout:
        age = time.time() - started
        cpu = fusion_cpu()
        if cpu <= quiet_cpu:
            quiet += 1
        else:
            quiet = 0
        if age >= min_age and quiet >= quiet_samples:
            _say("        Fusion settled (%.0fs, cpu %.1f%%)" % (age, cpu))
            return True
        time.sleep(8)
    _say("        Fusion never settled; proceeding anyway", err=True)
    return False


def healthy_fusion(attempts=3):
    """Return a URL to a Fusion that is up AND executing, recycling if it is not."""
    for attempt in range(1, attempts + 1):
        url = ensure_fusion()
        if url:
            wait_until_settled()
        if url and can_execute(url):
            return url
        if url is None:
            _say("        Fusion did not come up (attempt %d)" % attempt, err=True)
        else:
            _say("        Fusion answers MCP but will not execute - wedged, "
                 "recycling (attempt %d)" % attempt, err=True)
        restart_fusion("wedged or unreachable")
    return None


def load_progress():
    if PROGRESS_PATH.is_file():
        try:
            return json.loads(PROGRESS_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return {"done": {}}


def save_progress(progress):
    PROGRESS_PATH.write_text(json.dumps(progress, indent=2) + "\n")


def render_one(entries, url, timeout):
    """Fire one module's renders in a single bridge call, wait for the files.

    All of a module's views go in one call so the F3D is imported once, not once
    per view. The import is the operation that wedges Fusion, so halving the
    number of them halves the exposure.
    """
    if isinstance(entries, dict):
        entries = [entries]
    job = build_job(entries)
    JOB_PATH.write_text(json.dumps(job, indent=2) + "\n")
    if RESULT_PATH.exists():
        RESULT_PATH.unlink()
    targets = [str(RENDER_DIR / (e["name"] + ".png")) for e in entries]
    # Inject this machine's job path into the script before sending it. The
    # bridge transmits contents, not a path, so the Fusion side cannot work out
    # where it lives on its own.
    prepared = HERE / ".fusion_render.prepared.py"
    prepared.write_text(
        FUSION_SCRIPT.read_text().replace("__BN_JOB_PATH__", str(JOB_PATH)))
    try:
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), "--url", url,
             "--exec-file", str(prepared)],
            capture_output=True, text=True, timeout=BRIDGE_TIMEOUT)
    except subprocess.TimeoutExpired:
        # The script only FIRES the render and returns; it never waits for the
        # image. A call that takes longer than this is not slow, it is wedged.
        return False, "bridge call wedged (>%ds)" % BRIDGE_TIMEOUT
    if "RENDER_JOB_DONE" not in proc.stdout:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
        return False, "Fusion did not accept the job: %s" % tail[0][:160]
    done, missing = wait_for(targets, timeout=timeout, poll=5)
    if missing:
        return False, "did not produce %s" % ", ".join(p.name for p in missing)
    return True, "%d image(s), %d bytes" % (
        len(done), sum(done.values()))


def _say(message, err=False):
    """Print and flush. Python buffers stdout when it is not a tty, so an
    unattended run writes nothing to its log for an hour and looks hung."""
    print(message, file=sys.stderr if err else sys.stdout, flush=True)


def render_supervised(entries, timeout, attempts=3):
    """Render entries one at a time, and keep Fusion healthy while doing it.

    Three things keep it alive, in order of how much they matter:

    1. One document open at a time (enforced in fusion_render.py). Caching ten
       imported designs is what crashed the material-library service.
    2. Proactive recycling. Fusion's resident memory climbs across renders and
       does not come back down; restarting it every RECYCLE_AFTER_RENDERS renders,
       or whenever it passes RECYCLE_ABOVE_RSS_GB, retires the leak before it
       becomes a crash. Nothing is ever saved, so a restart costs only startup
       time.
    3. A headroom guard and a cool-down, so a render never starts into a machine
       that is already under memory pressure.

    Every render's before/after health is written to render-telemetry.json, which
    is what makes the leak visible instead of theoretical.
    """
    progress = load_progress()
    telemetry = []
    rendered, failed = [], []
    since_recycle = 0

    # Group by module: one import per module, all its views from that import.
    by_module = {}
    for entry in entries:
        by_module.setdefault(entry["module"], []).append(entry)
    groups = list(by_module.items())

    for index, (module_id, group) in enumerate(groups, 1):
        name = module_id
        outstanding = [e for e in group
                       if not (progress["done"].get(e["name"])
                               and (RENDER_DIR / (e["name"] + ".png")).is_file())]
        if not outstanding:
            _say("[%d/%d] %s already rendered, skipping" % (index, len(groups), name))
            rendered.append(name)
            continue

        for attempt in range(1, attempts + 1):
            before = health()
            if (since_recycle >= RECYCLE_AFTER_RENDERS
                    or before["fusion_rss_gb"] >= RECYCLE_ABOVE_RSS_GB):
                restart_fusion("%d renders done, rss %.2f GB"
                               % (since_recycle, before["fusion_rss_gb"]))
                since_recycle = 0
                before = health()
            url = healthy_fusion()
            if url is None:
                failed.append((name, "Fusion would not come up"))
                break
            if not wait_for_headroom():
                failed.append((name, "never got memory headroom"))
                break

            _say("[%d/%d] %s x%d views attempt %d  rss=%.2f GB free=%s%% port=%s"
                 % (index, len(groups), name, len(outstanding), attempt,
                    before["fusion_rss_gb"], before["free_percent"],
                    url.rsplit(":", 1)[-1].split("/")[0]))
            ok, note = render_one(outstanding, url, timeout)
            after = health()
            telemetry.append({"name": name, "attempt": attempt, "ok": ok,
                              "note": note, "before": before, "after": after,
                              "renders_since_recycle": since_recycle})
            TELEMETRY_PATH.write_text(json.dumps(telemetry, indent=2) + "\n")

            if ok:
                since_recycle += 1
                _say("        ok, %s  rss %.2f -> %.2f GB (%+.2f)"
                     % (note, before["fusion_rss_gb"], after["fusion_rss_gb"],
                        after["fusion_rss_gb"] - before["fusion_rss_gb"]))
                for e in outstanding:
                    path = RENDER_DIR / (e["name"] + ".png")
                    if path.is_file():
                        progress["done"][e["name"]] = {"bytes": path.stat().st_size}
                save_progress(progress)
                rendered.append(name)
                time.sleep(COOLDOWN_SECONDS)
                break

            _say("        failed: %s" % note, err=True)
            if not fusion_alive():
                _say("        Fusion died on this module", err=True)
                since_recycle = 0
            else:
                restart_fusion("recovering from a failed render")
                since_recycle = 0
            time.sleep(COOLDOWN_SECONDS)
        else:
            failed.append((name, "exhausted %d attempts" % attempts))

    return rendered, failed


def build_job(entries):
    return {
        "exports_root": str(EXPORTS_ROOT),
        "output_dir": str(RENDER_DIR),
        "renders": entries,
    }


def scene_overrides():
    """Scene deltas handed down by run_visual_cycles.py via BN_SCENE_OVERRIDES.

    Without this the iteration loop computes an adjustment every cycle and the
    renderer quietly ignores it, so the sweep runs to completion having changed
    nothing at all.
    """
    path = os.environ.get("BN_SCENE_OVERRIDES")
    if not path or not pathlib.Path(path).is_file():
        return {}
    return json.loads(pathlib.Path(path).read_text())


def entries_for(module_id, views, overrides=None):
    entries = []
    handed_down = scene_overrides()
    for view in views:
        entry = dict(BASE_SCENE)
        entry.update(handed_down)
        entry.update(VIEW_OUTPUT.get(view, {}))
        if overrides:
            entry.update(overrides)
        entry.update({
            "name": "%s-%s" % (module_id, view),
            "module": module_id,
            "view": "hero" if view == "alpha" else view,
        })
        entries.append(entry)
    return entries


def fire(job, timeout=600):
    JOB_PATH.write_text(json.dumps(job, indent=2) + "\n")
    if RESULT_PATH.exists():
        RESULT_PATH.unlink()
    proc = subprocess.run(
        [sys.executable, str(BRIDGE), "--url", discover_mcp_url(),
         "--exec-file", str(FUSION_SCRIPT)],
        capture_output=True, text=True, timeout=timeout)
    if "RENDER_JOB_DONE" not in proc.stdout:
        # Fusion can close the MCP socket as soon as its local renderer takes
        # ownership of the UI thread. In that case the render continues inside
        # Fusion, but urllib reports RemoteDisconnected and the bridge exits
        # before returning the script's acknowledgement. Treat only that known
        # signature as provisional acceptance; wait_for() remains the source of
        # truth and will time out if Fusion did not actually create the image.
        combined = proc.stdout + "\n" + proc.stderr
        response_lost = ("RemoteDisconnected" in combined or
                         "TimeoutError: timed out" in combined or
                         "timed out" in combined.lower())
        if response_lost and len(job.get("renders", [])) == 1:
            entry = job["renders"][0]
            target = pathlib.Path(job["output_dir"]) / (entry["name"] + ".png")
            print("  MCP response closed during render; waiting for %s"
                  % target.name, flush=True)
            return {"results": [{"name": entry["name"], "started": True,
                                  "target": str(target),
                                  "provisional": True}]}
        print(proc.stdout[-3000:], file=sys.stderr)
        print(proc.stderr[-2000:], file=sys.stderr)
        raise SystemExit("Fusion did not accept the render job")
    return json.loads(RESULT_PATH.read_text())


def wait_for(paths, timeout=3600, poll=5):
    """A render is done when its file exists and has stopped growing."""
    pending = {pathlib.Path(p): None for p in paths}
    done, started = {}, time.time()
    while pending and time.time() - started < timeout:
        for path in list(pending):
            if not path.exists():
                continue
            size = path.stat().st_size
            if pending[path] == size and size > 1024:
                done[path] = size
                del pending[path]
                print("  rendered %s (%d bytes, %.0fs)"
                      % (path.name, size, time.time() - started))
            else:
                pending[path] = size
        if pending:
            time.sleep(poll)
    for path in pending:
        print("  TIMEOUT %s" % path.name, file=sys.stderr)
    return done, list(pending)


def derive_matte(alpha_path, hero_path):
    """visual_quality.py needs an object matte to measure the contact shadow.

    The alpha variant is rendered for web compositing anyway, and its alpha
    channel IS the object matte, so this costs no extra render time.
    """
    from PIL import Image
    import numpy as np
    alpha = np.asarray(Image.open(alpha_path).convert("RGBA"))[..., 3]
    matte = (alpha > 200).astype(np.uint8) * 255
    out = pathlib.Path(hero_path)
    out = out.with_name(out.stem + "-matte.png")
    Image.fromarray(matte).save(out)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--module", action="append", dest="modules")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--views", nargs="+",
                        default=["hero", "front", "detail", "alpha"])
    parser.add_argument("--no-auto-alpha", action="store_true",
                        help="skip the alpha pass even when a hero is requested")
    parser.add_argument("--sweep", type=pathlib.Path,
                        help="JSON list of scene-override dicts, each with a 'suffix'")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args()

    modules = MODULE_IDS if args.all else (args.modules or ["BN-M01"])
    # The alpha pass is not optional in practice: its alpha channel is the object
    # matte, and without a matte visual_quality.py falls back to a heuristic mask
    # that counts the lit ground as subject. That inflates coverage and makes the
    # contact-shadow metric unmeasurable, so two scenes cannot be compared.
    views = list(args.views)
    if "hero" in views and "alpha" not in views and not args.no_auto_alpha:
        views.append("alpha")
    args.views = views
    entries = []
    if args.sweep:
        variants = json.loads(args.sweep.read_text())
        for module_id in modules:
            for variant in variants:
                suffix = variant.pop("suffix")
                for entry in entries_for(module_id, args.views, variant):
                    entry["name"] = "%s-%s" % (entry["name"], suffix)
                    entries.append(entry)
                variant["suffix"] = suffix
    else:
        for module_id in modules:
            entries.extend(entries_for(module_id, args.views))

    print("rendering %d image(s) for %s, one at a time with crash recovery"
          % (len(entries), ", ".join(modules)))
    lock = RenderLock()
    lock.__enter__()
    try:
        # Fusion crashes under this workload, repeatedly, and a relaunched Fusion
        # often binds a different MCP port. render_supervised submits exactly one
        # render per bridge call, rediscovers the port every time, relaunches
        # Fusion when it dies, and records finished outputs so a resume skips them
        # instead of re-rendering an hour of work.
        rendered, failed = render_supervised(entries, timeout=args.timeout)
    finally:
        lock.__exit__()

    for hero in sorted(RENDER_DIR.glob("*-hero*.png")):
        if hero.stem.endswith("-matte"):
            continue
        alpha = hero.with_name(hero.name.replace("-hero", "-alpha"))
        if alpha.exists() and alpha.stat().st_mtime >= hero.stat().st_mtime - 1:
            print("  matte %s" % derive_matte(alpha, hero).name)

    print("\n%d rendered, %d failed" % (len(rendered), len(failed)))
    for name, reason in failed:
        print("  FAILED %s: %s" % (name, reason), file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
