#!/usr/bin/env python3
"""Auditable overnight orchestrator for the existing Fusion CAD Agent loops."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Optional

ALLOWED_STATES = {
    "DRAFT", "BLOCKED_NEEDS_MEASUREMENT", "READY_PROTOTYPE",
    "READY_RELEASE_CANDIDATE", "AWAITING_HUMAN_REVIEW", "RELEASED",
}
RUNNABLE_STATES = {"READY_PROTOTYPE", "READY_RELEASE_CANDIDATE"}
REQUIRED_INTERFACE_FIELDS = {
    "name", "value", "unit", "tolerance", "source_type", "source_ref",
}


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def shared_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "Fusion CAD Agent").is_dir() and (parent / "Mac Mini Setup").is_dir():
            return parent
    raise SystemExit("Could not discover shared Claude root; pass --fusion-root and --mac-mini-root")


def roots(fusion_override: Optional[str], mini_override: Optional[str]):
    root = None
    if not fusion_override or not mini_override:
        root = shared_root()
    fusion = pathlib.Path(fusion_override).resolve() if fusion_override else root / "Fusion CAD Agent"
    mini = pathlib.Path(mini_override).resolve() if mini_override else root / "Mac Mini Setup"
    return fusion, mini


def safe_relative(root: pathlib.Path, value: str) -> pathlib.Path:
    target = (root / value).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError:
        raise ValueError(f"path escapes Fusion project: {value}")
    return target


def validate_job(job: dict, fusion_root: pathlib.Path, release: bool = False) -> list:
    errors = []
    required = {"schema_version", "job_id", "status", "project", "revision",
                "spec_path", "units", "models", "engineering", "expected",
                "validators", "deliverables"}
    missing = sorted(required - set(job))
    if missing:
        errors.append(f"missing top-level fields: {', '.join(missing)}")
        return errors
    if job["schema_version"] != 1:
        errors.append("schema_version must be 1")
    if job["status"] not in ALLOWED_STATES:
        errors.append(f"invalid status: {job['status']}")
    if job["units"] not in ("inch", "mm"):
        errors.append("units must be inch or mm")
    try:
        spec = safe_relative(fusion_root, job["spec_path"])
        if not spec.is_file():
            errors.append(f"spec does not exist: {spec}")
    except ValueError as exc:
        errors.append(str(exc))
    interfaces = job.get("engineering", {}).get("interfaces", [])
    if not interfaces:
        errors.append("at least one sourced engineering interface is required")
    for index, interface in enumerate(interfaces):
        absent = REQUIRED_INTERFACE_FIELDS - set(interface)
        if absent:
            errors.append(f"interface {index} missing: {', '.join(sorted(absent))}")
        if interface.get("value") in (None, ""):
            errors.append(f"interface {index} has no measured/sourced value")
        if not interface.get("source_ref"):
            errors.append(f"interface {index} has no source reference")
    validators = job.get("validators", {})
    for name in ("cadquery", "drawing"):
        value = validators.get(name)
        if not value:
            errors.append(f"missing {name} validator")
            continue
        try:
            if not safe_relative(fusion_root, value).is_file():
                errors.append(f"{name} validator does not exist: {value}")
        except ValueError as exc:
            errors.append(str(exc))
    if release or job["status"] == "READY_RELEASE_CANDIDATE":
        eng = job["engineering"]
        if not eng.get("load_case"):
            errors.append("release candidate requires an approved load_case")
        if not eng.get("safety_factor_target"):
            errors.append("release candidate requires safety_factor_target")
        if not validators.get("interference_required"):
            errors.append("release candidate must require interference analysis")
        if not validators.get("bom_reconciliation_required"):
            errors.append("release candidate must require BOM reconciliation")
        if not job.get("models", {}).get("vision_model"):
            errors.append("release candidate requires an MLX vision_model for visual QA")
        expected = job.get("expected", {})
        if expected.get("model_kind") != "assembly":
            errors.append("release candidate must be a native assembly, not a geometry proxy")
        if not isinstance(expected.get("component_count"), int) or expected.get("component_count", 0) < 2:
            errors.append("release candidate requires expected.component_count >= 2")
        for gate in ("interference_validator", "bom_reconciliation_validator"):
            value = validators.get(gate)
            if not value:
                errors.append(f"release candidate requires {gate}")
                continue
            try:
                if not safe_relative(fusion_root, value).is_file():
                    errors.append(f"{gate} does not exist: {value}")
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def resolve_model(mini_root: pathlib.Path, role: str) -> str:
    manager = mini_root / "tools" / "local-ai" / "local-ai-manager.py"
    result = subprocess.run([sys.executable, str(manager), "resolve", role],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def run_command(command: list, log_path: pathlib.Path, dry_run: bool) -> int:
    rendered = " ".join(str(part) for part in command)
    with log_path.open("a") as log:
        log.write(f"\n$ {rendered}\n")
    print("$", rendered)
    if dry_run:
        return 0
    with log_path.open("a") as log:
        proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, text=True)
    return proc.returncode


def copy_matching(source: pathlib.Path, destination: pathlib.Path, prefix: str):
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for path in source.glob(prefix + "*"):
        if path.is_file():
            target = destination / path.name
            shutil.copy2(path, target)
            copied.append({"name": target.name, "sha256": sha256(target), "bytes": target.stat().st_size})
    return copied


def run_pipeline(job_path: pathlib.Path, fusion_root: pathlib.Path,
                 mini_root: pathlib.Path, dry_run: bool, skip_fusion: bool,
                 model_override: Optional[str]) -> int:
    job = json.loads(job_path.read_text())
    errors = validate_job(job, fusion_root)
    if errors:
        print("JOB INVALID:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    if job["status"] not in RUNNABLE_STATES:
        print(f"JOB BLOCKED: state {job['status']} is not runnable", file=sys.stderr)
        return 3

    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = fusion_root / "runs" / job["job_id"] / stamp
    if dry_run:
        run_dir = pathlib.Path("<RUN_DIR>")
    else:
        run_dir.mkdir(parents=True, exist_ok=False)
    log_path = run_dir / "pipeline.log" if not dry_run else pathlib.Path(os.devnull)
    spec = safe_relative(fusion_root, job["spec_path"])
    out_name = f"{job['job_id']}-{job['revision']}"

    if model_override:
        builder = model_override
        planner = model_override
    else:
        try:
            builder = resolve_model(mini_root, job["models"]["builder_role"])
            planner = resolve_model(mini_root, job["models"]["reviewer_role"])
        except Exception as exc:
            print(f"MODEL RESOLUTION FAILED: {exc}", file=sys.stderr)
            return 4

    plan_json = run_dir / "design-plan.json"
    augmented_spec = run_dir / "augmented-spec.md"
    commands = [("planning", [
        sys.executable, str(pathlib.Path(__file__).resolve().parent / "cad_plan.py"),
        "--job", str(job_path.resolve()), "--spec", str(spec), "--model", planner,
        "--output", str(plan_json), "--augmented-spec", str(augmented_spec),
    ])]
    cq_validator = pathlib.Path(job["validators"]["cadquery"]).name
    commands.append(("cadquery", [
        sys.executable, str(fusion_root / "bridge" / "cq_loop.py"),
        "--spec", str(augmented_spec), "--model", builder, "--out-name", out_name,
        "--validator", cq_validator, "--max-attempts", "15",
    ]))
    bbox = job.get("expected", {}).get("bbox")
    fusion_cmd = [
        sys.executable, str(fusion_root / "bridge" / "fusion_loop.py"),
        "--spec", str(augmented_spec), "--model", builder, "--out-name", out_name,
        "--max-attempts", "10",
    ]
    if bbox:
        fusion_cmd += ["--expect-bbox", ",".join(str(value) for value in bbox)]
    if job.get("expected", {}).get("volume") is not None:
        fusion_cmd += ["--expect-volume", str(job["expected"]["volume"])]
    if not skip_fusion:
        commands.append(("fusion", fusion_cmd))
    commands.append(("drawing", [
        sys.executable, str(pathlib.Path(__file__).resolve().parent / "professional_drawing_loop.py"),
        "--job", str(job_path.resolve()), "--fusion-root", str(fusion_root),
        "--spec", str(augmented_spec),
        "--model", builder, "--out-name", out_name, "--max-attempts", "12",
    ]))
    if not skip_fusion and job["models"].get("vision_model"):
        commands.append(("vision_review", [
            sys.executable, str(pathlib.Path(__file__).resolve().parent / "vision_review.py"),
            "--job", str(job_path.resolve()),
            "--image", str(fusion_root / "exports" / f"{out_name}-fusion.png"),
            "--model", job["models"]["vision_model"],
            "--output", str(fusion_root / "exports" / f"{out_name}-vision.json"),
        ]))
    if job["status"] == "READY_RELEASE_CANDIDATE":
        for phase, key in (("interference", "interference_validator"),
                           ("bom_reconciliation", "bom_reconciliation_validator")):
            commands.append((phase, [
                sys.executable, str(safe_relative(fusion_root, job["validators"][key])),
                "--job", str(job_path.resolve()), "--fusion-root", str(fusion_root),
                "--out-name", out_name,
            ]))

    if dry_run:
        print(f"JOB {job['job_id']} revision {job['revision']} planner={planner} builder={builder}")
        print(f"RUN DIRECTORY: {run_dir}")
    else:
        (run_dir / "job.json").write_text(json.dumps(job, indent=2) + "\n")
        shutil.copy2(spec, run_dir / "spec.md")

    phases = []
    for phase, command in commands:
        started = time.time()
        rc = run_command(command, log_path, dry_run)
        phases.append({"phase": phase, "returncode": rc,
                       "elapsed_seconds": round(time.time() - started, 2)})
        if rc:
            break

    if dry_run:
        print("DRY RUN: no model, Fusion, or filesystem mutations performed")
        return 0

    artifacts = copy_matching(fusion_root / "exports", run_dir / "artifacts", out_name)
    scripts = copy_matching(fusion_root / "scripts", run_dir / "scripts", out_name)
    supporting = []
    common_root = fusion_root.parent.resolve()
    for kind, relative in job.get("supporting_files", {}).items():
        source = (common_root / relative).resolve()
        try:
            source.relative_to(common_root)
        except ValueError:
            print(f"SUPPORTING FILE ESCAPES SHARED ROOT: {relative}", file=sys.stderr)
            continue
        if source.is_file():
            target = run_dir / "supporting" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            supporting.append({"type": kind, "name": target.name,
                               "sha256": sha256(target), "bytes": target.stat().st_size})

    delivered = {pathlib.Path(item["name"]).suffix.lstrip(".").lower() for item in artifacts}
    if any(item["name"].endswith("-vision.json") for item in artifacts):
        delivered.add("vision_report")
    delivered.update(item["type"] for item in supporting)
    if plan_json.is_file():
        delivered.add("design_plan")
    delivered.update(("validation_report", "revision_manifest"))
    missing_deliverables = sorted(set(job["deliverables"]) - delivered)
    automated_ok = (bool(phases) and all(p["returncode"] == 0 for p in phases)
                    and not missing_deliverables)
    report = {
        "job_id": job["job_id"], "revision": job["revision"], "created_at": stamp,
        "job_sha256": sha256(run_dir / "job.json"), "spec_sha256": sha256(run_dir / "spec.md"),
        "planner_model": planner, "builder_model": builder, "phases": phases,
        "design_plan": ({"name": plan_json.name, "sha256": sha256(plan_json)}
                        if plan_json.is_file() else None), "artifacts": artifacts,
        "scripts": scripts, "supporting_files": supporting,
        "delivered_types": sorted(delivered), "missing_deliverables": missing_deliverables,
        "automated_gates_passed": automated_ok,
        "release_status": "AWAITING_HUMAN_REVIEW" if automated_ok else "FAILED",
        "human_review_required": True,
    }
    (run_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"REPORT: {run_dir / 'report.json'}")
    return 0 if automated_ok else 1


def release_check(run_dir: pathlib.Path) -> int:
    report_path = run_dir / "report.json"
    if not report_path.is_file():
        print("FAIL: report.json missing", file=sys.stderr)
        return 1
    report = json.loads(report_path.read_text())
    failures = []
    if not report.get("automated_gates_passed"):
        failures.append("automated phases did not all pass")
    if not report.get("artifacts"):
        failures.append("no archived artifacts")
    if not report.get("scripts"):
        failures.append("no archived generator scripts")
    if report.get("missing_deliverables"):
        failures.append("missing deliverables: " + ", ".join(report["missing_deliverables"]))
    if not report.get("human_review_required"):
        failures.append("human-review invariant missing")
    if report.get("release_status") == "RELEASED":
        failures.append("runner must never set RELEASED automatically")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("PASS: automated candidate is complete and awaiting human review")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fusion-root")
    parser.add_argument("--mac-mini-root")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("job")
    run = sub.add_parser("run")
    run.add_argument("job")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--skip-fusion", action="store_true",
                     help="run headless CadQuery/drawing phases only")
    run.add_argument("--model", help="explicit model ID; useful for pre-mini dry runs")
    release = sub.add_parser("release-check")
    release.add_argument("run_dir")
    args = parser.parse_args()
    fusion_root, mini_root = roots(args.fusion_root, args.mac_mini_root)
    if args.command == "validate":
        job = json.loads(pathlib.Path(args.job).read_text())
        errors = validate_job(job, fusion_root)
        if errors:
            for error in errors:
                print(f"FAIL: {error}")
            return 1
        print("PASS: job is valid for its current state")
        if job["status"] == "READY_PROTOTYPE" and not job["engineering"].get("load_case"):
            print("NOTE: prototype only; release remains blocked on load case")
        return 0
    if args.command == "run":
        return run_pipeline(pathlib.Path(args.job), fusion_root, mini_root,
                            args.dry_run, args.skip_fusion, args.model)
    return release_check(pathlib.Path(args.run_dir))


if __name__ == "__main__":
    raise SystemExit(main())
