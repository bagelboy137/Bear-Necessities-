#!/usr/bin/env python3
"""Local iteration loop for Bear Necessities marketing renders.

Ten or more cycles across ten modules, entirely on local models plus a model-free
deterministic gate. No Claude usage.

Three graded opinions, in order of authority:

  1. visual_quality.py       deterministic, free, runs on every image. THE gate.
  2. local vision model      fixed yes/no checklist, one image per request.
                             A second opinion, never the sole judge.
  3. local text model        reads the NUMBERS (never an image) and picks the next
                             scene delta from a fixed vocabulary.

Why it is built this way: LM-STUDIO-SAFE-PROFILES.md records this 16 GB laptop
kernel-panicking twice on the 14B MLX worker on 2026-08-25, and every capable VLM
being over budget. The deterministic gate is what makes the loop useful without a
capable local VLM; the 3B vision model is a bonus, not a dependency.

    python3 run_visual_cycles.py --cycles 10
    python3 run_visual_cycles.py --cycles 10 --no-vlm    # deterministic + text only
    python3 run_visual_cycles.py --demo
"""

import argparse
import base64
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
RENDER_DIR = HERE / "renders"
RUNS_DIR = HERE / "runs"
LEDGER_PATH = HERE / "visual-iteration-ledger.json"
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]

# Fixed vocabulary. The text model may only pick from these; it cannot invent a
# parameter, and it cannot touch geometry. Each entry is (key, delta, floor, ceil).
ADJUSTMENTS = {
    "brighter":        ("exposure", -0.3, 6.5, 10.5),
    "darker":          ("exposure", +0.3, 6.5, 10.5),
    "more_light":      ("brightness", +200.0, 400.0, 2000.0),
    "less_light":      ("brightness", -200.0, 400.0, 2000.0),
    "closer":          ("distance_factor", -0.06, 0.55, 3.00),
    "further":         ("distance_factor", +0.06, 0.55, 3.00),
    "rotate_light_cw": ("light_angle", +0.6, -6.3, 6.3),
    "rotate_light_ccw":("light_angle", -0.6, -6.3, 6.3),
    "longer_lens":     ("focal_length", +15.0, 35.0, 200.0),
    "shorter_lens":    ("focal_length", -15.0, 35.0, 200.0),
    "shift_right":     ("_target_x", +2.0, -18.0, 18.0),
    "shift_left":      ("_target_x", -2.0, -18.0, 18.0),
    "shift_up":        ("_target_z", +2.0, -14.0, 14.0),
    "shift_down":      ("_target_z", -2.0, -14.0, 14.0),
    "hold":            (None, 0.0, 0.0, 0.0),
}

# Which adjustment a given failing metric argues for. The text model gets this as
# context; the mapping is also the fallback when the model is unavailable or its
# answer is unusable, so the loop still converges with no model at all.
METRIC_HINT = {
    "subject_coverage_low": "closer",
    "subject_coverage_high": "further",
    "subject_centering": "shift_right",
    "tonal_p99": "brighter",
    "specular_fraction": "brighter",
    "metal_modulation": "rotate_light_cw",
    "panel_modulation": "rotate_light_ccw",
    "edge_richness": "darker",
    "contact_shadow": "rotate_light_ccw",
    "background_variation": "hold",
}


def extract_json(text):
    """Copied from fusion_native/review_native_family.py - same fence handling."""
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    candidate = (match.group(1) if match else text).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            return json.loads(candidate[start:end + 1])
        raise


def memory_free_percent():
    """Copied from fusion_native/review_native_family.py."""
    try:
        result = subprocess.run(["memory_pressure", "-Q"], capture_output=True,
                                text=True, timeout=10, check=False)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", result.stdout)
    return int(match.group(1)) if match else None


def wait_for_resources(max_load, min_free_percent, poll_seconds=15, timeout=3600):
    """Copied from fusion_native/review_native_family.py."""
    started = time.monotonic()
    announced = False
    while True:
        load = os.getloadavg()[0]
        free = memory_free_percent()
        if load <= max_load and (free is None or free >= min_free_percent):
            if announced:
                print("  RESOURCE_GUARD_PASS load=%.2f free=%s%%"
                      % (load, "unknown" if free is None else free), flush=True)
            return
        if not announced:
            print("  RESOURCE_GUARD_WAIT load=%.2f/%s free=%s/%s%%"
                  % (load, max_load, "unknown" if free is None else free,
                     min_free_percent), flush=True)
            announced = True
        if time.monotonic() - started >= timeout:
            raise RuntimeError("resource guard timed out")
        time.sleep(poll_seconds)


def loaded_instances(endpoint, model):
    """Guard against LM Studio silently spawning a second parallel instance.

    On 2026-08-25 the qwen2.5-vl-3b canary did exactly this and free memory fell
    from 74% to 32% without any error being raised. Counting the roster after each
    call is the cheapest way to notice.
    """
    url = endpoint.rstrip("/").replace("/chat/completions", "") + "/models"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            data = json.load(response)
    except Exception:
        return None
    return sum(1 for item in data.get("data", []) if item.get("id") == model)


def call_model(endpoint, model, prompt, image_path=None, max_tokens=1200,
               timeout=900):
    headers = {"Content-Type": "application/json"}
    content = [{"type": "text", "text": prompt}]
    if image_path is not None:
        encoded = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode()
        content.append({"type": "image_url",
                        "image_url": {"url": "data:image/png;base64," + encoded}})
    payload = {"model": model, "temperature": 0, "max_tokens": max_tokens,
               "messages": [{"role": "user", "content": content}]}
    request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(),
                                     headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.load(response)
    message = body["choices"][0]["message"]
    return (message.get("content") or message.get("reasoning_content") or ""), \
        body.get("usage", {})


def vlm_checklist(endpoint, model, image_path, module_id, cues, guards):
    """Fixed yes/no checklist. Never an open-ended 'is this good?'."""
    prompt = (
        "You are a product-photography QA checker. Look at this single rendered "
        "image of overland camp module {mid}. Answer ONLY about what is visible.\n"
        "Required visible content for this module:\n- {cues}\n\n"
        "Return JSON only, no prose, every field required:\n"
        '{{"module_id":"{mid}",'
        '"reads_as_product_photo":true or false,'
        '"metal_looks_like_metal":true or false,'
        '"sits_on_a_surface":true or false,'
        '"all_required_content_visible":true or false,'
        '"missing":["..."],'
        '"verdict":"PASS" or "FLAGGED",'
        '"blocking_findings":["..."]}}\n'
        "Rules: verdict must be FLAGGED if blocking_findings is non-empty. "
        "Keep every string under 120 characters."
    ).format(mid=module_id, cues="\n- ".join(cues))
    wait_for_resources(guards["max_load"], guards["min_free_percent"])
    raw, usage = call_model(endpoint, model, prompt, image_path,
                            max_tokens=guards["max_tokens"])
    instances = loaded_instances(endpoint, model)
    if instances is not None and instances > 1:
        raise RuntimeError(
            "LM Studio has %d instances of %s resident; aborting before it eats "
            "the machine (see LM-STUDIO-SAFE-PROFILES.md, 2026-08-25)"
            % (instances, model))
    result = extract_json(raw)
    # The 2026-08-25 contradiction bug: PASS with populated blocking findings.
    # That is a failed attempt, not a pass.
    if result.get("verdict") == "PASS" and result.get("blocking_findings"):
        raise ValueError(
            "self-contradictory verdict: PASS with %d blocking finding(s)"
            % len(result["blocking_findings"]))
    result["_usage"] = usage
    result["_model"] = model
    return result


def choose_adjustment(endpoint, model, module_id, metrics, failures, hint, guards):
    """The text model sees numbers only. It never sees an image."""
    prompt = (
        "You are tuning a 3D product render. You cannot see the image; you get "
        "measurements only.\n\n"
        "Module: {mid}\n"
        "Failing checks:\n- {failures}\n\n"
        "Measurements: {metrics}\n\n"
        "Choose EXACTLY ONE adjustment from this list and nothing else:\n{options}\n\n"
        "A reasonable default for these failures is '{hint}'.\n"
        'Return JSON only: {{"adjustment":"<one option>","reason":"<under 120 '
        'characters>"}}\n'
        "The adjustment MUST be one of the listed strings. The reason MUST be "
        "under 120 characters - count them."
    ).format(mid=module_id, failures="\n- ".join(failures) or "none",
             metrics=json.dumps(metrics), options=", ".join(sorted(ADJUSTMENTS)),
             hint=hint)
    wait_for_resources(guards["max_load"], guards["min_free_percent"])
    raw, usage = call_model(endpoint, model, prompt, max_tokens=guards["max_tokens"])
    result = extract_json(raw)
    choice = result.get("adjustment")
    if choice not in ADJUSTMENTS:
        raise ValueError("adjustment %r is not in the allowed vocabulary" % choice)
    reason = result.get("reason", "")
    if len(reason) > 120:
        # The 2026-08-25 bug that killed a 30-cycle run: the failure message said
        # only "length/type invalid", so the model resampled instead of shortening
        # and came back longer. State the measurement and the delta.
        raise ValueError("reason is %d characters, %d over the 120 limit - shorten "
                         "it, do not rewrite it" % (len(reason), len(reason) - 120))
    return {"adjustment": choice, "reason": reason, "_usage": usage, "_model": model}


def apply_adjustment(scene, name):
    key, delta, floor, ceiling = ADJUSTMENTS[name]
    if key is None:
        return scene, "hold"
    if key in ("_target_x", "_target_z"):
        offset = list(scene.get("target_offset_in", [0.0, 0.0, 0.0]))
        index = 0 if key == "_target_x" else 2
        before = offset[index]
        offset[index] = max(floor, min(ceiling, before + delta))
        scene["target_offset_in"] = offset
        return scene, "%s %.1f -> %.1f" % (key, before, offset[index])
    before = float(scene.get(key, 0.0))
    after = max(floor, min(ceiling, before + delta))
    scene[key] = after
    return scene, "%s %.2f -> %.2f" % (key, before, after)


def failure_keys(failures):
    keys = []
    for failure in failures:
        if "subject_coverage" in failure:
            keys.append("subject_coverage_low" if "outside" in failure
                        and float(failure.split()[1]) < 0.25
                        else "subject_coverage_high")
        elif "contact_shadow" in failure or "floats" in failure:
            keys.append("contact_shadow")
        elif "subject_centering" in failure:
            keys.append("subject_centering")
        else:
            keys.append(failure.split()[0])
    return keys


def demo():
    """Self-check on the parts that do not need a model or a renderer."""
    scene = {"exposure": 8.2, "zoom": 0.18, "brightness": 1200.0}
    scene, note = apply_adjustment(dict(scene), "brighter")
    assert abs(scene["exposure"] - 7.9) < 1e-9, note
    scene, _ = apply_adjustment({"distance_factor": 0.58}, "closer")
    assert scene["distance_factor"] == 0.55, \
        "distance must clamp at its floor, got %s" % scene["distance_factor"]
    scene, note = apply_adjustment({"target_offset_in": [0.0, 0.0, 0.0]}, "shift_right")
    assert scene["target_offset_in"] == [2.0, 0.0, 0.0], scene
    scene, _ = apply_adjustment({"target_offset_in": [17.0, 0.0, 0.0]}, "shift_right")
    assert scene["target_offset_in"][0] == 18.0, "target offset must clamp"
    scene, note = apply_adjustment({"exposure": 8.2}, "hold")
    assert note == "hold" and scene["exposure"] == 8.2

    keys = failure_keys(["subject_coverage 0.099 outside 0.25-0.75",
                         "contact_shadow_ratio 0.967 above 0.900 (module floats)",
                         "subject_centering 0.115 above 0.080",
                         "tonal_p99 151.0 below 215.0"])
    assert keys == ["subject_coverage_low", "contact_shadow", "subject_centering",
                    "tonal_p99"], keys
    assert all(METRIC_HINT[k] in ADJUSTMENTS for k in keys)

    # A self-contradictory verdict must be rejected, not accepted.
    import types
    bad = {"verdict": "PASS", "blocking_findings": ["module floats"]}
    try:
        if bad["verdict"] == "PASS" and bad["blocking_findings"]:
            raise ValueError("self-contradictory")
        raise AssertionError("should have rejected")
    except ValueError:
        pass

    assert extract_json('```json\n{"adjustment":"closer"}\n```')["adjustment"] == "closer"
    assert extract_json('noise {"a":1} tail')["a"] == 1
    print("demo ok: deltas clamp, hints map to real adjustments, contradictory "
          "verdicts rejected, fenced JSON parsed")


LMS = str(pathlib.Path.home() / ".lmstudio" / "bin" / "lms")


def lms(*args, timeout=300):
    """Drive the LM Studio CLI. Returns True on success, False if unavailable."""
    if not pathlib.Path(LMS).exists():
        return False
    try:
        result = subprocess.run([LMS] + list(args), capture_output=True,
                                text=True, timeout=timeout)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def unload_models():
    """Free the GPU before rendering.

    Fusion's local renderer is Metal-based and so is LM Studio with --gpu max.
    With a model resident, renders fire and then never complete: startLocalRender
    returns a future, Fusion sits at 0% CPU, and no image is ever written.
    Measured 2026-08-26 - the same modules that rendered in 120-185s with LM
    Studio stopped produced nothing in 12 minutes with a 3B model loaded.

    This is the render-side half of the rule the local-model framework already
    follows: sequence Fusion and LM Studio, never overlap them.
    """
    if lms("unload", "--all", timeout=120):
        time.sleep(10)
        return True
    return False


def load_vision(model, context=3072):
    """Bring the vision model back for the review phase only."""
    return lms("load", model, "--context-length", str(context),
               "--parallel", "1", "--gpu", "max", "-y", timeout=300)


def render(module_ids, scene_overrides, timeout):
    """Drive render_module.py; it fires Fusion and polls for the files."""
    command = [sys.executable, str(HERE / "render_module.py"), "--views", "hero",
               "--timeout", str(timeout)]
    for module_id in module_ids:
        command += ["--module", module_id]
    overrides_path = HERE / "cycle-overrides.json"
    overrides_path.write_text(json.dumps(scene_overrides, indent=2) + "\n")
    env = dict(os.environ, BN_SCENE_OVERRIDES=str(overrides_path))
    # Stream the driver's output instead of capturing it. A ten-cycle sweep is a
    # multi-hour job; swallowing the one component that reports per-module
    # progress, Fusion health and recycles makes a stall indistinguishable from
    # slow work, which is exactly the hole this fell into.
    lines = []
    proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, env=env,
                            bufsize=1)
    for line in proc.stdout:
        line = line.rstrip()
        lines.append(line)
        print("    | %s" % line, flush=True)
    proc.wait()
    return proc.returncode == 0, "\n".join(lines)


def score(module_ids):
    sys.path.insert(0, str(HERE))
    import visual_quality as vq
    thresholds = vq.load_thresholds()
    results = {}
    for module_id in module_ids:
        path = RENDER_DIR / ("%s-hero.png" % module_id)
        if not path.is_file():
            results[module_id] = {"failures": ["render missing"], "metrics": {}}
            continue
        metrics = vq.measure(path)
        results[module_id] = {"metrics": metrics,
                              "failures": vq.grade(metrics, thresholds),
                              "sha256": vq.sha256(path)}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cycles", type=int, default=10)
    parser.add_argument("--modules", nargs="+", default=MODULE_IDS)
    parser.add_argument("--endpoint", default="http://127.0.0.1:1234/v1/chat/completions")
    parser.add_argument("--text-model", default="qwen2.5-coder-7b-instruct")
    parser.add_argument("--vision-model", default="qwen2.5-vl-3b-instruct")
    parser.add_argument("--no-vlm", action="store_true")
    parser.add_argument("--render-timeout", type=int, default=3600)
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()

    if args.demo:
        demo()
        return 0

    # Laptop profile from LM-STUDIO-SAFE-PROFILES.md.
    guards = {"max_load": 20.0, "min_free_percent": 30, "max_tokens": 1800,
              "cooldown": 30}

    RUNS_DIR.mkdir(exist_ok=True)
    brief_cues = json.loads((HERE / "module-cues.json").read_text()) \
        if (HERE / "module-cues.json").is_file() else {}

    sys.path.insert(0, str(HERE))
    import render_module
    scene = dict(render_module.BASE_SCENE)

    ledger = {"schema_version": 1, "started": None, "cycles": [],
              "text_model": args.text_model,
              "vision_model": None if args.no_vlm else args.vision_model,
              "policy": "laptop_profile_deterministic_primary"}
    if LEDGER_PATH.is_file():
        ledger = json.loads(LEDGER_PATH.read_text())

    completed = {entry["cycle"] for entry in ledger["cycles"]}
    for cycle in range(1, args.cycles + 1):
        cycle_file = RUNS_DIR / ("visual-%02d.validated.json" % cycle)
        if cycle in completed and cycle_file.is_file():
            print("cycle %02d already validated, reusing" % cycle)
            scene = json.loads(cycle_file.read_text())["scene_after"]
            continue

        print("\n=== cycle %02d ===" % cycle, flush=True)
        if unload_models():
            print("  LM Studio models unloaded; GPU is free for Fusion", flush=True)
        ok, output = render(args.modules, scene, args.render_timeout)
        if not ok:
            print(output[-2000:], file=sys.stderr)
        scored = score(args.modules)
        passed = [m for m, r in scored.items() if not r["failures"]]
        print("  deterministic: %d/%d pass" % (len(passed), len(args.modules)))

        # A missing render has no failing METRIC, so the hint lookup returns
        # "hold" and the loop votes to change nothing - it would run all ten
        # cycles doing nothing while looking like it was working. Rendering being
        # broken is not a tuning signal; stop and say so.
        missing = [m for m, r in scored.items() if "render missing" in r["failures"]]
        if missing:
            print("  ABORT: %d of %d renders missing (%s). Rendering is broken, "
                  "not the scene. Check that Fusion is running and its MCP server "
                  "is responding, then re-run - completed cycles are reused."
                  % (len(missing), len(args.modules), ", ".join(missing[:4])),
                  file=sys.stderr)
            if output:
                print(output[-1500:], file=sys.stderr)
            return 2

        records = []
        vision_ready = [False]
        for module_id in args.modules:
            result = scored[module_id]
            record = {"module_id": module_id, "sha256": result.get("sha256"),
                      "failures": result["failures"],
                      "metrics": {k: v for k, v in result["metrics"].items()
                                  if isinstance(v, (int, float, str, bool))}}
            if result["failures"]:
                keys = failure_keys(result["failures"])
                hint = METRIC_HINT.get(keys[0], "hold")
                try:
                    choice = choose_adjustment(
                        args.endpoint, args.text_model, module_id,
                        record["metrics"], result["failures"], hint, guards)
                    record["proposed"] = choice["adjustment"]
                    record["reason"] = choice["reason"]
                    record["proposed_by"] = choice["_model"]
                except Exception as exc:
                    record["proposed"] = hint
                    record["reason"] = "fallback to deterministic hint: %s" % exc
                    record["proposed_by"] = "deterministic_hint"
            else:
                record["proposed"] = "hold"
                record["proposed_by"] = "deterministic_gate"
            if not args.no_vlm and not vision_ready[0]:
                vision_ready[0] = load_vision(args.vision_model)
                print("  vision model loaded for review: %s" % vision_ready[0],
                      flush=True)
            if not args.no_vlm and (RENDER_DIR / ("%s-hero.png" % module_id)).is_file():
                cues = brief_cues.get(module_id, ["module frame and equipment"])
                try:
                    record["vlm"] = vlm_checklist(
                        args.endpoint, args.vision_model,
                        RENDER_DIR / ("%s-hero.png" % module_id),
                        module_id, cues, guards)
                except Exception as exc:
                    record["vlm_error"] = str(exc)
                time.sleep(guards["cooldown"])
            records.append(record)

        # One global scene delta per cycle: the scene is shared, so the majority
        # vote across modules is the honest aggregate.
        votes = {}
        for record in records:
            votes[record["proposed"]] = votes.get(record["proposed"], 0) + 1
        winner = max(votes, key=votes.get)
        scene_before = dict(scene)
        scene, note = apply_adjustment(scene, winner)
        print("  adjustment: %s (%d/%d votes) -> %s"
              % (winner, votes[winner], len(records), note))

        entry = {"cycle": cycle, "modules": records, "adjustment": winner,
                 "adjustment_note": note, "votes": votes,
                 "scene_before": scene_before, "scene_after": dict(scene),
                 "passed": len(passed)}
        cycle_file.write_text(json.dumps(entry, indent=2) + "\n")
        ledger["cycles"] = [c for c in ledger["cycles"] if c["cycle"] != cycle]
        ledger["cycles"].append(entry)
        ledger["cycles"].sort(key=lambda c: c["cycle"])
        LEDGER_PATH.write_text(json.dumps(ledger, indent=2) + "\n")

        if len(passed) == len(args.modules):
            print("  all modules pass the deterministic gate; stopping early")
            break

    reviews = sum(len(c["modules"]) for c in ledger["cycles"])
    print("\n%d cycle(s), %d module reviews, ledger at %s"
          % (len(ledger["cycles"]), reviews, LEDGER_PATH))
    return 0


if __name__ == "__main__":
    sys.exit(main())
