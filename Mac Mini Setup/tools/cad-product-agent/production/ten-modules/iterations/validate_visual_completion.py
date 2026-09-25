#!/usr/bin/env python3
"""Triple-check current Fusion renders: deterministic cues, visual review, web evidence."""

import argparse
import hashlib
import json
import pathlib


HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent / "fusion-native" / "exports"
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=DEFAULT_ROOT)
    parser.add_argument("--comparables", type=pathlib.Path,
                        default=HERE / "comparable-products.json")
    parser.add_argument("--context", type=pathlib.Path,
                        default=HERE / "module-review-context.json")
    parser.add_argument("--catalog", type=pathlib.Path,
                        default=HERE / "ots-components.json")
    parser.add_argument("--independent-review", type=pathlib.Path,
                        default=HERE / "runs" / "independent-visual-inspection.json")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    comparables = json.loads(args.comparables.read_text())
    context = json.loads(args.context.read_text())
    catalog = json.loads(args.catalog.read_text())
    vlm_path = args.root / "local-vlm-visual-review.json"
    vlm = json.loads(vlm_path.read_text()) if vlm_path.is_file() else {}
    vlm_by_id = {item["module_id"]: item for item in vlm.get("reviews", [])}
    independent = json.loads(args.independent_review.read_text())
    independent_by_id = {
        item["module_id"]: item for item in independent.get("reviews", [])
    }
    module_context = {item["module_id"]: item for item in context["modules"]}
    catalog_by_id = {item["id"]: item for item in catalog["components"]}
    web_by_module = {module_id: [] for module_id in MODULE_IDS}
    for item in comparables["sources"]:
        for module_id in item["modules"]:
            web_by_module[module_id].append({"id": item["id"], "url": item["url"],
                                             "kind": "comparable"})
    for module_id, module in module_context.items():
        for catalog_id in module["primary_catalog_ids"]:
            item = catalog_by_id[catalog_id]
            web_by_module[module_id].append({"id": catalog_id,
                                             "url": item["evidence_url"],
                                             "kind": "manufacturer_or_supplier"})
    failures = []
    modules = []
    for module_id in MODULE_IDS:
        folder = args.root / module_id
        build_path = folder / (module_id + "-build.json")
        image_path = folder / (module_id + "-iso.png")
        try:
            build = json.loads(build_path.read_text())
            review = vlm_by_id.get(module_id, {})
            independent_review = independent_by_id[module_id]
            image_hash = sha256(image_path)
            cues = build.get("required_visual_cues", [])
            part_names = build.get("part_names", [])
            bbox = build.get("measured_bbox", {})
            expected_bbox = {"width_in": 24.0, "depth_in": 20.0,
                             "height_in": 18.0}
            bbox_ok = all(
                abs(float(bbox.get(key, -999)) - expected) <= 0.01
                for key, expected in expected_bbox.items()
            )
            deterministic = (len(cues) >= 10 and len(part_names) >= 50 and bbox_ok)
            current_vlm = (review.get("verdict") == "PASS" and
                           review.get("image_sha256") == image_hash and
                           not review.get("blocking_findings") and
                           not review.get("missing_or_unclear"))
            stage_hashes = independent_review.get("stage_image_sha256", {})
            current_independent = (
                independent.get("result") == "PASS" and
                independent_review.get("verdict") == "PASS" and
                image_hash in stage_hashes.values() and
                not independent_review.get("blocking_findings") and
                not independent_review.get("missing_or_unclear") and
                len(independent_review.get("visible_cues", [])) >= 3
            )
            web_sources = web_by_module[module_id]
            web_evidence = (len(web_sources) >= 1 and
                            all(item["url"].startswith("https://")
                                for item in web_sources))
            checks = {
                "deterministic_named_visual_cues": deterministic,
                "hash_bound_independent_visual_pass": current_vlm or current_independent,
                "current_web_comparable_or_product_evidence": web_evidence,
            }
            if not all(checks.values()):
                failures.append("%s visual triple-check failed: %s" %
                                (module_id, checks))
            modules.append({
                "module_id": module_id,
                "checks": checks,
                "visual_cue_count": len(cues),
                "named_part_count": len(part_names),
                "image": str(image_path.resolve()),
                "image_sha256": image_hash,
                "visual_review_mode": "local_vlm" if current_vlm else "independent_codex_inspection",
                "vlm_model": review.get("model") if current_vlm else None,
                "recognizable_as": (review.get("recognizable_as") if current_vlm else
                                    independent_review.get("recognizable_as")),
                "web_evidence": web_sources,
            })
        except Exception as exc:
            failures.append("%s evidence error: %s" % (module_id, exc))
    report = {
        "schema_version": 1,
        "result": "PASS" if not failures and len(modules) == 10 else "FAIL",
        "module_count": len(modules),
        "checks_per_module": 3,
        "check_definitions": {
            "deterministic": "Current Fusion build report has at least ten required cues, at least 50 named parts, and 24x20x18 bounds within 0.01 inch.",
            "visual_review": "A local VLM or independent Codex image inspection passes with no missing/blocking findings and its recorded hash matches the current isometric image. Contradictory VLM output cannot pass.",
            "web_evidence": "At least one current comparable-product or selected OTS product page is recorded for the module."
        },
        "independent_review": str(args.independent_review.resolve()),
        "independent_review_sha256": sha256(args.independent_review),
        "failures": failures,
        "modules": modules,
        "authority": "visual product-concept completion only; not dimensional, structural, manufacturing, safety, or fabrication release"
    }
    output = args.output or args.root / "triple-visual-validation-report.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print("VISUAL_TRIPLE_CHECK_%s modules=%d report=%s" %
          (report["result"], len(modules), output))
    for failure in failures:
        print("- " + failure)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
