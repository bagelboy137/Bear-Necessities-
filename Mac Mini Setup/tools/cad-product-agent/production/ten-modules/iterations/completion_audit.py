#!/usr/bin/env python3
"""Requirement-by-requirement completion audit for the 30-cycle CAD objective."""

import csv
import hashlib
import json
import os
import pathlib


HERE = pathlib.Path(__file__).resolve().parent
TEN = HERE.parent
FINAL = TEN / "fusion-native" / "exports"
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]


def read_json(path):
    return json.loads(path.read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(condition, requirement, evidence, failures, results, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append({"requirement": requirement, "status": status,
                    "evidence": str(evidence), "detail": detail})
    if not condition:
        failures.append(requirement + (": " + detail if detail else ""))


def main():
    failures, results = [], []
    ledger_path = HERE / "runs" / "iteration-ledger.json"
    ledger = read_json(ledger_path)
    records = ledger.get("records", [])
    check(ledger.get("result") == "PASS" and ledger.get("cycle_count") == 30 and
          ledger.get("module_review_count") == 300,
          "30 validated family cycles / 300 module reviews",
          ledger_path, failures, results)
    allowed_models = set(ledger.get("allowed_models", []))
    used_models = {item.get("model") for item in records}
    model_policy = ledger.get("model_policy", {})
    check(ledger.get("required_model") == "qwen/qwen2.5-coder-14b" and
          used_models <= allowed_models <= {
              "qwen/qwen2.5-coder-14b", "qwen2.5-coder-7b-instruct"
          } and (len(used_models) == 1 or
                 model_policy.get("mode") == "documented_low_memory_continuation"),
          "Every revision decision has approved local-coder model provenance",
          ledger_path, failures, results,
          "models used: %s" % ", ".join(sorted(used_models)))
    for index, stage in enumerate(("design", "manufacturing", "combined"), 1):
        snapshot_path = HERE / "runs" / (stage + "-ledger.json")
        snapshot = read_json(snapshot_path) if snapshot_path.is_file() else {}
        check(snapshot.get("result") == "PASS" and
              snapshot.get("module_review_count") == index * 100,
              "%s stage ledger is complete" % stage,
              snapshot_path, failures, results,
              "expected %d cumulative reviews" % (index * 100))

    catalog_path = HERE / "ots-components.json"
    catalog = read_json(catalog_path)
    catalog_ids = {item["id"] for item in catalog.get("components", [])}
    check(len(catalog_ids) >= 20 and all(item.get("order_url", "").startswith("https://")
                                        for item in catalog.get("components", [])),
          "Curated OTS catalog has order/evidence links",
          catalog_path, failures, results)
    combined_bom = HERE / "boms" / "all-modules-prototype-bom.csv"
    with combined_bom.open(newline="") as handle:
        bom_rows = list(csv.DictReader(handle))
    check({row["module_id"] for row in bom_rows} == set(MODULE_IDS) and
          all(row["catalog_id"] in catalog_ids and
              row["order_url"].startswith("https://") for row in bom_rows),
          "All ten module BOMs resolve only to curated linked components",
          combined_bom, failures, results, "%d combined BOM rows" % len(bom_rows))
    for module_id in MODULE_IDS:
        rows = [row for row in bom_rows if row["module_id"] == module_id]
        quantities = {row["catalog_id"]: row["quantity"] for row in rows}
        module_bom = HERE / "boms" / (module_id + "-prototype-bom.csv")
        check(module_bom.is_file() and quantities.get("TNUTZ-EX1010-18") == "8" and
              quantities.get("TNUTZ-EX1010-22") == "4" and
              quantities.get("8020-4132") == "24" and
              quantities.get("8020-3393") == "48",
              "%s has a separate BOM and the common extrusion/joint architecture" % module_id,
              module_bom, failures, results)

    stage_roots = {
        "design": HERE / "checkpoints" / "design" / "exports",
        "manufacturing": HERE / "checkpoints" / "manufacturing" / "exports",
        "combined": FINAL,
    }
    for stage, root in stage_roots.items():
        native_path = root / "native-validation-report.json"
        visual_path = root / "triple-visual-validation-report.json"
        pipeline_path = root / "native-pipeline-run.json"
        reports = [read_json(path) if path.is_file() else {} for path in
                   (native_path, visual_path, pipeline_path)]
        check(reports[0].get("result") == "PASS" and
              reports[1].get("result") == "PASS" and
              reports[2].get("result") == "PASS" and
              reports[2].get("gates", {}).get("fusion_build") is True and
              reports[2].get("gates", {}).get("deterministic_validation") is True,
              "%s stage completed Fusion build + deterministic + hash-bound visual + web loop" % stage,
              root, failures, results)

    f3d_paths = [FINAL / module_id / (module_id + ".f3d") for module_id in MODULE_IDS]
    f3d_hashes = {sha256(path) for path in f3d_paths if path.is_file()}
    check(len(f3d_hashes) == 10,
          "Final deliverable contains ten separate native CAD archives",
          FINAL, failures, results)
    for module_id in MODULE_IDS:
        folder = FINAL / module_id
        required = [folder / (module_id + suffix) for suffix in
                    (".f3d", ".step", ".stl", ".obj", ".mtl", "-iso.png",
                     "-front.png", "-build.json")]
        check(all(path.is_file() and path.stat().st_size > 0 for path in required),
              "%s final CAD/export set is complete" % module_id,
              folder, failures, results)

    learning = HERE / "LOCAL-MODEL-ITERATION-LEARNINGS.md"
    learning_text = learning.read_text() if learning.is_file() else ""
    check("Validated module reviews: 300 / 300" in learning_text and
          "does not modify model weights" in learning_text,
          "Validated learnings are portable and accurately persisted for prompt retrieval",
          learning, failures, results)
    replication = HERE / "run_mac_mini_replication.sh"
    check(replication.is_file() and os.access(replication, os.X_OK) and
          "--expected-reviews 100" in replication.read_text() and
          "--expected-reviews 200" in replication.read_text() and
          "--expected-reviews 300" in replication.read_text(),
          "Mac mini replication script covers all three staged build/review loops",
          replication, failures, results)

    report = {
        "schema_version": 1,
        "result": "PASS" if not failures else "FAIL",
        "requirements_checked": len(results),
        "requirements_passed": sum(item["status"] == "PASS" for item in results),
        "failures": failures,
        "results": results,
        "release_boundary": "Objective completion proves the local-model review framework, visual concept CAD, OTS sourcing and prototype BOM. It does not release fabrication, vehicle installation, safety, or production purchase quantities."
    }
    output = HERE / "completion-audit-report.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("COMPLETION_AUDIT_%s passed=%d/%d report=%s" %
          (report["result"], report["requirements_passed"],
           report["requirements_checked"], output))
    for failure in failures:
        print("- " + failure)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
