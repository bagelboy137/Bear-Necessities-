#!/usr/bin/env python3
"""
run_queue.py — execute queued CAD jobs against the local model.

Run this when LM Studio is up. It walks the queue, SKIPS anything gated on
missing measurements, and generates the rest via cq_loop.py.

    python3 bridge/run_queue.py --dry-run     # show the plan, call nothing
    python3 bridge/run_queue.py               # execute READY jobs
    python3 bridge/run_queue.py --model qwen/qwen2.5-coder-14b

The gate is the point: a bracket whose hole spacing was invented does not fit
the vehicle. Jobs marked BLOCKED_NEEDS_MEASUREMENT stay blocked until a human
supplies real numbers.
"""
import argparse, json, pathlib, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT.parent / "Bear Necessities" / "product" / "custom-parts" / "C-02-vehicle-queue.json"
SPECS = QUEUE.parent


def server_up():
    try:
        urllib.request.urlopen("http://localhost:1234/v1/models", timeout=5)
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default=str(QUEUE))
    ap.add_argument("--model", default="qwen2.5-coder-7b-instruct")
    ap.add_argument("--max-attempts", type=int, default=10)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    q = json.loads(pathlib.Path(a.queue).read_text())
    jobs = sorted(q["jobs"], key=lambda j: j["rank"])
    ready = [j for j in jobs if j["status"] == "READY"]
    blocked = [j for j in jobs if j["status"] == "BLOCKED_NEEDS_MEASUREMENT"]
    done = [j for j in jobs if j["status"] == "DONE"]

    print(f"QUEUE: {a.queue}")
    print(f"  {len(ready)} ready | {len(blocked)} blocked | {len(done)} done\n")

    if blocked:
        print("BLOCKED — will not run until measurements exist:")
        for j in blocked:
            print(f"  [{j['rank']:>2}] {j['vehicle']}")
            for n in j.get("needs", []):
                print(f"        - {n}")
        print()

    if not ready:
        print("Nothing ready to build.")
        return 0

    print("READY to build:")
    for j in ready:
        print(f"  [{j['rank']:>2}] {j['vehicle']}  spec={j.get('spec')}")
    print()

    if a.dry_run:
        print("DRY RUN — no model calls made.")
        return 0

    if not server_up():
        print("ERROR: LM Studio is not reachable at http://localhost:1234")
        print("Start it, then re-run. (`lms server status` wakes the service.)")
        return 1

    failures = 0
    for j in ready:
        spec = SPECS / j["spec"]
        name = j["vehicle"].split("(")[0].strip().replace(" ", "-").replace("/", "-")
        print(f"\n{'='*66}\nBUILDING {j['vehicle']}\n{'='*66}")
        cmd = [sys.executable, str(ROOT / "bridge" / "cq_loop.py"),
               "--spec", str(spec), "--model", a.model,
               "--out-name", f"C-02-{name}", "--max-attempts", str(a.max_attempts)]
        if j.get("validator"):
            cmd += ["--validator", j["validator"]]
        rc = subprocess.run(cmd).returncode
        if rc != 0:
            failures += 1
            print(f"  -> FAILED: {j['vehicle']}")
        else:
            print(f"  -> OK: {j['vehicle']}")

    print(f"\n{len(ready)-failures}/{len(ready)} built.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
