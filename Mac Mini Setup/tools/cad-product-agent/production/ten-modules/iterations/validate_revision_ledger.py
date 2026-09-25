#!/usr/bin/env python3
"""Independent deterministic gate for a complete 30-cycle/300-review ledger."""

import argparse
import hashlib
import json
import pathlib
import sys


MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]
STAGES = ("design", "manufacturing", "combined")
PRIMARY_MODEL = "qwen/qwen2.5-coder-14b"
LOW_MEMORY_MODEL = "qwen2.5-coder-7b-instruct"
APPROVED_MODELS = {PRIMARY_MODEL, LOW_MEMORY_MODEL}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text())
    records = ledger.get("records", [])
    failures = []
    allowed_models = set(ledger.get("allowed_models", [ledger.get("required_model")]))
    ids = [item.get("record_id") for item in records]
    expected_cycles = {"%s-%02d" % (stage, cycle)
                       for stage in STAGES for cycle in range(1, 11)}
    if len(records) != 300:
        failures.append("expected 300 module reviews, found %d" % len(records))
    if len(set(ids)) != len(ids):
        failures.append("record IDs are not unique")
    if {item.get("cycle_id") for item in records} != expected_cycles:
        failures.append("cycle coverage is not exactly 10 design + 10 manufacturing + 10 combined")
    for cycle_id in sorted(expected_cycles):
        covered = sorted(item.get("module_id") for item in records
                         if item.get("cycle_id") == cycle_id)
        if covered != MODULE_IDS:
            failures.append("%s does not cover all ten modules once" % cycle_id)
    if (not allowed_models or not allowed_models <= APPROVED_MODELS or
            ledger.get("required_model") != PRIMARY_MODEL):
        failures.append("ledger model policy is not an approved 14B/7B local-coder policy")
    if any(item.get("model") not in allowed_models for item in records):
        failures.append("one or more records fall outside the ledger model policy")
    expected_model_counts = {
        model: sum(item.get("model") == model for item in records)
        for model in sorted(allowed_models)
    }
    if ledger.get("model_counts") != expected_model_counts:
        failures.append("ledger model counts do not match record provenance")
    if len([count for count in expected_model_counts.values() if count]) > 1:
        policy = ledger.get("model_policy", {})
        if (policy.get("mode") != "documented_low_memory_continuation" or
                "IOGPUFamily" not in policy.get("reason", "")):
            failures.append("mixed-model continuation lacks the required kernel-panic rationale")
    allowed_decisions = {"ADOPT_AS_PROTOTYPE_REQUIREMENT", "RETAIN_VALIDATED_BASELINE"}
    if any(item.get("gate_decision") not in allowed_decisions for item in records):
        failures.append("one or more records lack a valid gate decision")
    if any(not item.get("evidence_ids") for item in records):
        failures.append("one or more records lack provenance IDs")
    report = {
        "result": "PASS" if not failures else "FAIL",
        "ledger": str(args.ledger.resolve()),
        "ledger_sha256": hashlib.sha256(args.ledger.read_bytes()).hexdigest(),
        "cycle_count": len({item.get("cycle_id") for item in records}),
        "module_review_count": len(records),
        "model_counts": expected_model_counts,
        "module_counts": {module_id: sum(item.get("module_id") == module_id
                                          for item in records)
                          for module_id in MODULE_IDS},
        "stage_counts": {stage: sum(item.get("stage") == stage for item in records)
                         for stage in STAGES},
        "failures": failures,
        "release_authority": "evidence completeness only; not an engineering release"
    }
    output = args.output or args.ledger.with_name("iteration-validation-report.json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("ITERATION_VALIDATION_%s cycles=%d reviews=%d report=%s" %
          (report["result"], report["cycle_count"],
           report["module_review_count"], output))
    for failure in failures:
        print("- " + failure)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
