#!/usr/bin/env python3
"""Evidence audit for plans/01-marketing-visuals-and-ots-bom.md.

This does not run expensive renders or models. It answers whether their current,
hash-bound evidence exists and covers the plan's full scope.
"""

import csv
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]


def root():
    for parent in HERE.parents:
        if (parent / "Mac Mini Setup").is_dir() and (parent / "Fusion CAD Agent").is_dir():
            return parent
    raise SystemExit("cannot discover shared Claude root")


ROOT = root()
STUDY = (ROOT / "Mac Mini Setup" / "tools" / "cad-product-agent" /
         "production" / "ten-modules")
VISUAL = STUDY / "visual"
CONFIG = STUDY / "configurations"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path, failures):
    if not path.is_file():
        failures.append("missing %s" % path)
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        failures.append("invalid JSON %s: %s" % (path, exc))
        return {}


def main():
    failures = []

    for path in (VISUAL / "VISUAL-MARKETING-BRIEF.md",
                 VISUAL / "visual_quality.py",
                 VISUAL / "fusion_render.py",
                 VISUAL / "render_module.py",
                 VISUAL / "run_visual_cycles.py",
                 VISUAL / "validate_visual_ledger.py",
                 VISUAL / "make_contact_sheet.py",
                 CONFIG / "CONFIGURATIONS.md",
                 CONFIG / "render_configurations.py",
                 PROJECT / "product" / "bom" / "OTS-AUDIT.md"):
        if not path.is_file():
            failures.append("missing deliverable %s" % path)

    baseline = load(VISUAL / "visual-quality-baseline.json", failures)
    if baseline and not (baseline.get("result") == "FAIL"
                         and baseline.get("images") == 20):
        failures.append("baseline must document 0/20-style legacy failure")

    quality = load(VISUAL / "visual-quality-report.json", failures)
    if quality and not (quality.get("result") == "PASS"
                        and quality.get("images") == 40
                        and not quality.get("missing")):
        failures.append("visual quality must PASS all 40 canonical images")

    ledger = load(VISUAL / "visual-iteration-ledger.json", failures)
    cycles = ledger.get("cycles", []) if ledger else []
    reviews = sum(len(item.get("modules", [])) for item in cycles)
    if len(cycles) < 10 or reviews < 100:
        failures.append("visual ledger has %d cycles/%d reviews; need 10/100"
                        % (len(cycles), reviews))
    for cycle in cycles:
        if len(cycle.get("modules", [])) != 10:
            failures.append("visual cycle %s does not cover 10 modules"
                            % cycle.get("cycle"))

    sheet = load(VISUAL / "marketing-contact-sheet.json", failures)
    if sheet:
        image_path = pathlib.Path(sheet.get("contact_sheet", ""))
        if not image_path.is_file() or digest(image_path) != sheet.get("contact_sheet_sha256"):
            failures.append("contact-sheet image/hash mismatch")
        if len(sheet.get("images", [])) != 20:
            failures.append("contact sheet does not cover 10 heroes + 10 fronts")

    confirmation = load(VISUAL / "CLAUDE-VISUAL-CONFIRMATION.json", failures)
    if confirmation:
        if confirmation.get("result") != "PASS":
            failures.append("final marketing confirmation is not PASS")
        if len(confirmation.get("modules", [])) != 10:
            failures.append("final confirmation does not cover 10 modules")
        if sheet and confirmation.get("contact_sheet_sha256") != sheet.get("contact_sheet_sha256"):
            failures.append("confirmation is bound to a stale contact sheet")
    if not (VISUAL / "CLAUDE-VISUAL-CONFIRMATION.md").is_file():
        failures.append("missing human-readable final confirmation")

    config_validation = load(CONFIG / "configuration-validation.json", failures)
    if config_validation and not (config_validation.get("result") == "PASS"
                                  and len(config_validation.get("configurations", [])) == 6):
        failures.append("configuration solver does not PASS all six layouts")
    config_renders = load(CONFIG / "renders" / "configuration-render-report.json",
                          failures)
    if config_renders and not (config_renders.get("result") == "PASS"
                               and len(config_renders.get("renders", [])) == 6):
        failures.append("configuration visual report does not PASS six layouts")

    bom_path = PROJECT / "product" / "bom" / "modules" / "all-modules-prototype-bom.csv"
    if bom_path.is_file():
        rows = list(csv.DictReader(bom_path.open()))
        if not rows or any(not row.get("ots_class") for row in rows):
            failures.append("BOM has rows without ots_class")
        if any(row.get("ots_class") == "CUSTOM_OTHER" for row in rows):
            failures.append("BOM contains CUSTOM_OTHER")
    else:
        failures.append("missing all-modules BOM")

    native = load(STUDY / "fusion-native" / "exports" /
                  "native-validation-report.json", failures)
    if native and native.get("result") != "PASS":
        failures.append("native family gate is not PASS")
    mesh = load(STUDY / "mesh-integrity-report.json", failures)
    if mesh and not (mesh.get("result") == "PASS" or mesh.get("pass") is True):
        failures.append("mesh integrity gate is not PASS")

    published = load(PROJECT / "website" / "public" / "modules" /
                     "marketing-render-manifest.json", failures)
    if published and not (published.get("result") == "PASS"
                          and len(published.get("published", [])) == 10):
        failures.append("website does not contain the gated 10-module render set")
    for item in published.get("published", []) if published else []:
        path = PROJECT / "website" / "public" / "modules" / (item["module_id"] + ".png")
        if not path.is_file() or digest(path) != item.get("sha256"):
            failures.append("website image/hash mismatch for %s" % item["module_id"])

    build_text = (HERE / "build.sh").read_text()
    if "visuals)" not in build_text or "run_visuals" not in build_text:
        failures.append("build front door has no visuals stage")

    report = {"gate": "plan_01_completion_audit",
              "result": "PASS" if not failures else "FAIL",
              "visual_cycles": len(cycles), "visual_reviews": reviews,
              "failures": failures}
    output = (PROJECT / "product" / "cad" / "evidence" /
              "plan-01-completion-audit.json")
    output.write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        print("PLAN_01_AUDIT_FAIL %d failure(s)" % len(failures))
        for failure in failures:
            print("  - %s" % failure)
        return 1
    print("PLAN_01_AUDIT_PASS cycles=%d reviews=%d" % (len(cycles), reviews))
    return 0


if __name__ == "__main__":
    sys.exit(main())
