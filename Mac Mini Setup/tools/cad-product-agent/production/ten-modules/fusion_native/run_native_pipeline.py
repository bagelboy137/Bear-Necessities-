#!/usr/bin/env python3
"""One command: probe APIs, build in Fusion, validate, then review locally."""

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

from fusion_api_client import FusionAPIError, FusionMCPClient


HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_EXPORTS = HERE.parents[0] / "fusion-native" / "exports"
DEFAULT_BUILDER = HERE / "build_native_modules.py"
DEFAULT_LM_URL = "http://127.0.0.1:1234/v1"
DEFAULT_ITERATIONS = HERE.parents[0] / "iterations"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lm_models(base_url):
    request = urllib.request.Request(base_url.rstrip("/") + "/models")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return [item["id"] for item in json.load(response).get("data", [])]
    except urllib.error.URLError as exc:
        raise RuntimeError("Cannot reach LM Studio at %s: %s" % (base_url, exc)) from None


def native_chat_endpoint(base_url):
    value = base_url.rstrip("/")
    if value.endswith("/v1"):
        value = value[:-3]
    return value + "/api/v1/chat"


def run_checked(command):
    print("+ " + " ".join(str(item) for item in command), flush=True)
    return subprocess.run(command, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fusion-url", default="http://127.0.0.1:27182/mcp")
    parser.add_argument("--lm-url", default=DEFAULT_LM_URL)
    parser.add_argument("--vision-model", default="google/gemma-4-e4b")
    parser.add_argument("--builder", type=pathlib.Path, default=DEFAULT_BUILDER)
    parser.add_argument("--output-root", type=pathlib.Path, default=DEFAULT_EXPORTS)
    parser.add_argument("--revision-ledger", type=pathlib.Path,
                        default=DEFAULT_ITERATIONS / "runs" / "iteration-ledger.json")
    parser.add_argument("--ots-catalog", type=pathlib.Path,
                        default=DEFAULT_ITERATIONS / "ots-components.json")
    parser.add_argument("--expected-reviews", type=int, default=300)
    parser.add_argument("--vision-max-tokens", type=int,
                        default=int(os.environ.get("BN_VISION_MAX_TOKENS", "900")))
    parser.add_argument("--vision-retry-max-tokens", type=int,
                        default=int(os.environ.get("BN_VISION_RETRY_MAX_TOKENS", "1400")))
    parser.add_argument("--vision-context-length", type=int,
                        default=int(os.environ.get("BN_VISION_CONTEXT_LENGTH", "3072")))
    parser.add_argument("--vision-reasoning", choices=("auto", "off"),
                        default=os.environ.get("BN_VISION_REASONING", "auto"))
    parser.add_argument("--vision-cooldown-seconds", type=float,
                        default=float(os.environ.get("BN_VISION_COOLDOWN_SECONDS", "20")))
    parser.add_argument("--vision-max-load", type=float,
                        default=float(os.environ.get("BN_VISION_MAX_LOAD", "20")))
    parser.add_argument("--vision-min-free-percent", type=int,
                        default=int(os.environ.get("BN_VISION_MIN_FREE_PERCENT", "25")))
    parser.add_argument("--probe", action="store_true",
                        help="check both APIs and required models/tools, then exit")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-vision", action="store_true")
    args = parser.parse_args()

    models = lm_models(args.lm_url)
    if args.vision_model not in models:
        raise RuntimeError("Vision model %r is not installed in LM Studio" %
                           args.vision_model)
    fusion = FusionMCPClient(args.fusion_url)
    info = fusion.connect()
    tools = {item["name"] for item in fusion.list_tools()}
    required_tools = {"fusion_mcp_execute", "fusion_mcp_read", "fusion_mcp_update"}
    missing_tools = sorted(required_tools - tools)
    if missing_tools:
        raise RuntimeError("Fusion MCP is missing required tools: %s" %
                           ", ".join(missing_tools))
    print("Fusion=%s LM Studio models=%d vision=%s" %
          (info.get("serverInfo", {}).get("name", "connected"),
           len(models), args.vision_model), flush=True)
    if args.probe:
        print("NATIVE_PIPELINE_PROBE_PASS")
        return 0

    args.output_root.mkdir(parents=True, exist_ok=True)
    report_path = args.output_root / "native-pipeline-run.json"
    previous_report = {}
    if report_path.is_file():
        try:
            previous_report = json.loads(report_path.read_text())
        except (ValueError, OSError):
            previous_report = {}
    started = datetime.datetime.now(datetime.timezone.utc)
    if not args.skip_build:
        source = args.builder.read_text()
        replacement = "OUT_ROOT = " + json.dumps(str(args.output_root.resolve()))
        source, count = re.subn(r"^OUT_ROOT\s*=.*$", replacement,
                                source, count=1, flags=re.M)
        if count != 1:
            raise RuntimeError("Builder does not expose a single-line OUT_ROOT")
        substitutions = {
            "REVISION_LEDGER_PATH": str(args.revision_ledger.resolve()),
            "OTS_CATALOG_PATH": str(args.ots_catalog.resolve()),
        }
        for variable, value in substitutions.items():
            source, count = re.subn(
                r"^%s\s*=.*$" % variable,
                variable + " = " + json.dumps(value),
                source, count=1, flags=re.M
            )
            if count != 1:
                raise RuntimeError("Builder does not expose %s" % variable)
        output, is_error = fusion.execute_script(source)
        try:
            fusion_result = json.loads(output)
        except json.JSONDecodeError:
            fusion_result = {"success": not is_error, "message": output}
        if is_error or not fusion_result.get("success", False):
            raise FusionAPIError(fusion_result.get("error", output))
        print(fusion_result.get("message", "Fusion build complete"), flush=True)

    validator = HERE / "validate_native_family.py"
    run_checked([sys.executable, str(validator), "--root", str(args.output_root),
                 "--expected-reviews", str(args.expected_reviews)])
    if not args.skip_vision:
        reviewer = HERE / "review_native_family.py"
        run_checked([sys.executable, str(reviewer), "--root", str(args.output_root),
                     "--model", args.vision_model,
                     "--endpoint", native_chat_endpoint(args.lm_url),
                     "--max-tokens", str(args.vision_max_tokens),
                     "--retry-max-tokens", str(args.vision_retry_max_tokens),
                     "--context-length", str(args.vision_context_length),
                     "--reasoning", args.vision_reasoning,
                     "--cooldown-seconds", str(args.vision_cooldown_seconds),
                     "--max-load", str(args.vision_max_load),
                     "--min-free-percent", str(args.vision_min_free_percent)])
        visual_validator = DEFAULT_ITERATIONS / "validate_visual_completion.py"
        run_checked([sys.executable, str(visual_validator),
                     "--root", str(args.output_root)])

    prior_build_evidence = (
        previous_report.get("result") == "PASS" and
        previous_report.get("gates", {}).get("fusion_build") is True and
        previous_report.get("builder_sha256") == sha256(args.builder) and
        previous_report.get("revision_ledger_sha256") == sha256(args.revision_ledger) and
        previous_report.get("ots_catalog_sha256") == sha256(args.ots_catalog)
    )
    report = {
        "result": "PASS",
        "started_at": started.isoformat(),
        "completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "fusion_url": args.fusion_url,
        "fusion_server": info.get("serverInfo", {}),
        "lm_studio_url": args.lm_url,
        "vision_model": args.vision_model,
        "vision_runtime_profile": {
            "max_tokens": args.vision_max_tokens,
            "retry_max_tokens": args.vision_retry_max_tokens,
            "context_length": args.vision_context_length,
            "reasoning": args.vision_reasoning,
            "cooldown_seconds": args.vision_cooldown_seconds,
            "max_load": args.vision_max_load,
            "min_free_percent": args.vision_min_free_percent,
        },
        "builder": str(args.builder.resolve()),
        "builder_sha256": sha256(args.builder),
        "output_root": str(args.output_root.resolve()),
        "revision_ledger": str(args.revision_ledger.resolve()),
        "revision_ledger_sha256": sha256(args.revision_ledger),
        "ots_catalog": str(args.ots_catalog.resolve()),
        "ots_catalog_sha256": sha256(args.ots_catalog),
        "expected_module_reviews": args.expected_reviews,
        "gates": {"fusion_build": not args.skip_build or prior_build_evidence,
                  "fusion_build_executed_this_run": not args.skip_build,
                  "deterministic_validation": True,
                  "local_vision_review": not args.skip_vision,
                  "web_comparable_visual_traceability": not args.skip_vision},
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print("NATIVE_PIPELINE_PASS report=%s" % report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
