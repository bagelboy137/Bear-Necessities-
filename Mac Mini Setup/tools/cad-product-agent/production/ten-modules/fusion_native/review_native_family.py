#!/usr/bin/env python3
"""Run an independent local vision-model review over all ten Fusion renders."""

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.request


def extract_json(text):
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
    try:
        result = subprocess.run(
            ["memory_pressure", "-Q"], capture_output=True, text=True,
            timeout=10, check=False
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None
    match = re.search(r"System-wide memory free percentage:\s*(\d+)%", result.stdout)
    return int(match.group(1)) if match else None


def wait_for_resources(max_load, min_free_percent, poll_seconds=15, timeout=3600):
    started = time.monotonic()
    announced = False
    while True:
        load = os.getloadavg()[0]
        free = memory_free_percent()
        if (load <= max_load and
                (free is None or free >= min_free_percent)):
            if announced:
                print("VISION_RESOURCE_GUARD_PASS load=%.2f free=%s%%" %
                      (load, "unknown" if free is None else free), flush=True)
            return
        if not announced:
            print("VISION_RESOURCE_GUARD_WAIT load=%.2f/%s free=%s/%s%%" % (
                load, max_load, "unknown" if free is None else free,
                min_free_percent
            ), flush=True)
            announced = True
        if time.monotonic() - started >= timeout:
            raise RuntimeError("vision resource guard timed out")
        time.sleep(poll_seconds)


def review(image_path, build, model, endpoint, token_limits, context_length,
           max_load, min_free_percent, retry_cooldown, reasoning):
    cues = build["required_visual_cues"]
    prompt = """You are the independent visual QA reviewer for an overland-module CAD family.
Inspect this single transparent-background Autodesk Fusion isometric image. The expected module
is {module_id} ({title}). Its intended visible cues are:
- {cues}

Judge only what is visible. A cue can pass when represented by clear concept-CAD geometry; do
not require photorealism. Flag anonymous box-only geometry, a blocked/unusable camera, a module
whose intended function is not recognizable, visibly missing key equipment, obvious impossible
intersections, or inconsistent silver-extrusion/dark-panel family styling. Do not infer dimensions,
loads, tolerances, certifications, or fabrication readiness. Return JSON only:
{{"module_id":"{module_id}","verdict":"PASS" or "FLAGGED","recognizable_as":"short phrase",
"visible_cues":["..."],"missing_or_unclear":["..."],"blocking_findings":["..."],
"warnings":["..."],"limitations":["visual concept review only"]}}""".format(
        module_id=build["module_id"], title=build["title"], cues="\n- ".join(cues)
    )
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    data_url = "data:image/png;base64," + encoded
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LM_API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["LM_API_TOKEN"]
    failures = []
    result = None
    usage = {}
    for attempt, token_limit in enumerate(token_limits, 1):
        wait_for_resources(max_load, min_free_percent)
        native_api = endpoint.rstrip("/").endswith("/api/v1/chat")
        if native_api:
            payload = {
                "model": model,
                "input": [
                    {"type": "text", "content": prompt},
                    {"type": "image", "data_url": data_url},
                ],
                "temperature": 0,
                "max_output_tokens": token_limit,
                "context_length": context_length,
                "store": False,
            }
            if reasoning != "auto":
                payload["reasoning"] = reasoning
        else:
            payload = {
                "model": model,
                "temperature": 0,
                "max_tokens": token_limit,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]}],
            }
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(),
                                         headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=1800) as response:
                body = json.load(response)
                if native_api:
                    content = next(
                        (item.get("content", "") for item in body.get("output", [])
                         if item.get("type") == "message"), ""
                    )
                    usage = body.get("stats", {})
                else:
                    message = body["choices"][0]["message"]
                    content = message.get("content") or message.get("reasoning_content") or ""
                    usage = body.get("usage", {})
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError("LM Studio HTTP %s: %s" % (exc.code, detail)) from None
        try:
            result = extract_json(content)
            break
        except Exception as exc:
            failures.append("attempt %d: %s; raw=%r" % (attempt, exc, content[:200]))
            if retry_cooldown > 0 and attempt < len(token_limits):
                print("VISION_RETRY_COOLDOWN %.1fs" % retry_cooldown, flush=True)
                time.sleep(retry_cooldown)
    if result is None:
        raise ValueError("; ".join(failures))
    if result.get("module_id") != build["module_id"]:
        raise ValueError("review returned wrong module_id")
    if (result.get("verdict") == "PASS" and
            (result.get("blocking_findings") or result.get("missing_or_unclear"))):
        result["verdict"] = "FLAGGED"
        result["consistency_error"] = (
            "A PASS verdict cannot contain blocking or missing findings."
        )
    result["model"] = model
    result["image"] = str(image_path)
    result["image_sha256"] = hashlib.sha256(image_path.read_bytes()).hexdigest()
    result["usage"] = usage
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[1] /
                        "fusion-native" / "exports")
    parser.add_argument("--model", default="google/gemma-4-e4b")
    parser.add_argument("--endpoint", default="http://127.0.0.1:1234/api/v1/chat")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--max-tokens", type=int,
                        default=int(os.environ.get("BN_VISION_MAX_TOKENS", "900")))
    parser.add_argument("--retry-max-tokens", type=int,
                        default=int(os.environ.get("BN_VISION_RETRY_MAX_TOKENS", "1400")))
    parser.add_argument("--context-length", type=int,
                        default=int(os.environ.get("BN_VISION_CONTEXT_LENGTH", "3072")))
    parser.add_argument("--reasoning", choices=("auto", "off"),
                        default=os.environ.get("BN_VISION_REASONING", "auto"),
                        help="native API reasoning mode; auto omits the setting for non-reasoning models")
    parser.add_argument("--cooldown-seconds", type=float,
                        default=float(os.environ.get("BN_VISION_COOLDOWN_SECONDS", "20")))
    parser.add_argument("--max-load", type=float,
                        default=float(os.environ.get("BN_VISION_MAX_LOAD", "20")))
    parser.add_argument("--min-free-percent", type=int,
                        default=int(os.environ.get("BN_VISION_MIN_FREE_PERCENT", "25")))
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    if args.max_tokens < 256 or args.retry_max_tokens < args.max_tokens:
        parser.error("vision token limits are invalid")
    if args.start < 1 or args.count < 1 or args.start + args.count - 1 > 10:
        parser.error("--start/--count must select modules within 1..10")
    reviews = []
    errors = []
    for idx in range(args.start, args.start + args.count):
        module_id = "BN-M%02d" % idx
        folder = args.root / module_id
        try:
            build = json.loads((folder / (module_id + "-build.json")).read_text())
            result = review(folder / (module_id + "-iso.png"), build,
                            args.model, args.endpoint,
                            (args.max_tokens, args.retry_max_tokens),
                            args.context_length,
                            args.max_load, args.min_free_percent,
                            args.cooldown_seconds, args.reasoning)
            reviews.append(result)
            print("%s %s recognizable_as=%s" %
                  (module_id, result.get("verdict"), result.get("recognizable_as")), flush=True)
            if args.cooldown_seconds > 0 and idx < args.start + args.count - 1:
                print("%s VISION_COOLDOWN %.1fs" %
                      (module_id, args.cooldown_seconds), flush=True)
                time.sleep(args.cooldown_seconds)
        except Exception as exc:
            errors.append({"module_id": module_id, "error": str(exc)})
            print("%s REVIEW_ERROR %s" % (module_id, exc), flush=True)
    flagged = [r["module_id"] for r in reviews if r.get("verdict") != "PASS"]
    output = {
        "result": "PASS" if len(reviews) == args.count and not flagged and not errors else "FLAGGED",
        "model": args.model,
        "review_count": len(reviews),
        "flagged_modules": flagged,
        "errors": errors,
        "reviews": reviews,
        "runtime_profile": {
            "max_tokens": args.max_tokens,
            "retry_max_tokens": args.retry_max_tokens,
            "context_length": args.context_length,
            "reasoning": args.reasoning if args.endpoint.rstrip("/").endswith("/api/v1/chat") else "endpoint default",
            "cooldown_seconds": args.cooldown_seconds,
            "max_load": args.max_load,
            "min_free_percent": args.min_free_percent,
        },
        "module_range": {"start": args.start, "count": args.count},
        "authority": "advisory visual review; cannot establish engineering or fabrication readiness",
    }
    path = args.output or args.root / "local-vlm-visual-review.json"
    path.write_text(json.dumps(output, indent=2) + "\n")
    print("LOCAL_VLM_%s report=%s" % (output["result"], path))
    return 0 if output["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
