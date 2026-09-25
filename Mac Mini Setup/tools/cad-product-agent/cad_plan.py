#!/usr/bin/env python3
"""Generate and validate a structured spatial/feature plan before CAD coding."""

import argparse
import json
import os
import pathlib
import re
import urllib.request

REQUIRED = {"parameters", "datums", "feature_sequence", "placement_strategy",
            "interfaces", "manufacturing_constraints", "expected_checks", "blockers"}


def extract_json(text):
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return json.loads((match.group(1) if match else text).strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--spec", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--augmented-spec", required=True)
    args = parser.parse_args()
    job_path = pathlib.Path(args.job)
    spec_path = pathlib.Path(args.spec)
    job = json.loads(job_path.read_text())
    system = (pathlib.Path(__file__).resolve().parent / "prompts" / "cad-planner.md").read_text()
    prompt = f"JOB:\n{json.dumps(job, indent=2)}\n\nSPEC:\n{spec_path.read_text()}"
    payload = {"model": args.model, "temperature": 0.1, "max_tokens": 3000,
               "messages": [{"role": "system", "content": system},
                            {"role": "user", "content": prompt}]}
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LM_API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["LM_API_TOKEN"]
    request = urllib.request.Request("http://127.0.0.1:1234/v1/chat/completions",
                                     data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=1800) as response:
            content = json.load(response)["choices"][0]["message"]["content"]
        plan = extract_json(content)
    except Exception as exc:
        print(f"PLAN FAILED: {exc}")
        return 1
    missing = sorted(REQUIRED - set(plan))
    if missing:
        print("PLAN FAILED: missing fields: " + ", ".join(missing))
        return 1
    if plan.get("blockers"):
        print("PLAN BLOCKED: " + json.dumps(plan["blockers"]))
        return 1
    planned_names = {str(item.get("name", "")).lower() for item in plan.get("interfaces", [])}
    required_names = {str(item["name"]).lower() for item in job["engineering"]["interfaces"]}
    if not required_names.issubset(planned_names):
        omitted = sorted(required_names - planned_names)
        print("PLAN FAILED: omitted required interfaces: " + ", ".join(omitted))
        return 1
    pathlib.Path(args.output).write_text(json.dumps(plan, indent=2) + "\n")
    augmented = (spec_path.read_text() + "\n\n## Approved machine-generated build plan\n\n"
                 + "```json\n" + json.dumps(plan, indent=2) + "\n```\n")
    pathlib.Path(args.augmented_spec).write_text(augmented)
    print(f"PLAN PASS: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
