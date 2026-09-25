#!/usr/bin/env python3
import csv
import json
import pathlib
import sys

ALLOWED = {"ORDERABLE", "ORDERABLE_BUT_SOLD_OUT", "SOURCE_REQUIRED",
           "ORDERABLE_ALTERNATE_VERIFY",
           "SOURCE_REQUIRED_DIMENSIONS_NOT_RELEASED", "CUSTOM_REQUIRED",
           "ENGINEERING_HOLD", "REJECTED_DOES_NOT_FIT",
           "REJECTED_DOES_NOT_FIT_22_INNER_WIDTH"}


def main(root):
    root = pathlib.Path(root)
    family = json.loads((root / "module-family.json").read_text())
    errors = []
    modules = family.get("modules", [])
    if len(modules) != 10:
        errors.append(f"expected 10 modules, got {len(modules)}")
    if len({m.get('id') for m in modules}) != 10:
        errors.append("module IDs are not unique")
    cuts = family.get("common_frame", {}).get("cut_list")
    if cuts != [{"length": 18.0, "quantity": 8}, {"length": 22.0, "quantity": 4}]:
        errors.append("common two-length frame cut list changed")
    for module in modules:
        disposition = module.get("primary_component", {}).get("status")
        if disposition not in ALLOWED:
            errors.append(f"{module.get('id')}: invalid disposition {disposition}")
        for item in module.get("internal_layout", []):
            origin, size = item["origin"], item["size"]
            high = [origin[i] + size[i] for i in range(3)]
            if any(origin[i] < 1 or high[i] > (24,20,18)[i]-1 for i in range(3)):
                errors.append(f"{module['id']}/{item['label']}: violates inner clearance")
        for suffix in ("step", "stl", "svg", "json"):
            if not (root / "exports" / f"{module['id']}.{suffix}").is_file():
                errors.append(f"{module['id']}: missing {suffix}")
    with (root / "procurement-bom.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        errors.append("procurement BOM empty")
    if any(row["status"] not in ALLOWED for row in rows):
        errors.append("BOM has invalid disposition")
    rejected = [r for r in rows if r["status"].startswith("REJECTED")]
    if len(rejected) < 2 or any(r["qty"] != "0" for r in rejected):
        errors.append("rejected fit candidates must remain as zero-quantity BOM warnings")
    for name in ("BN-family-10-modules.step", "family-summary.json"):
        if not (root / "exports" / name).is_file():
            errors.append(f"missing family artifact {name}")
    for name in ("clearance-report.json", "bom-reconciliation-report.json"):
        evidence = root / name
        if not evidence.is_file():
            errors.append(f"missing deterministic evidence {name}")
        elif not json.loads(evidence.read_text()).get("pass"):
            errors.append(f"deterministic evidence failed: {name}")
    jobs = sorted((root / "jobs").glob("BN-M*.job.json"))
    if len(jobs) != 10:
        errors.append(f"expected 10 production jobs, got {len(jobs)}")
    if errors:
        print("FAMILY VALIDATION FAILED:", *errors, sep="\n- ", file=sys.stderr)
        return 1
    print(f"PASS: 10 modules/jobs, {len(rows)} BOM rows, two cut lengths, clearance/BOM/artifact evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent))
