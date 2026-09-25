#!/usr/bin/env python3
"""Deterministic release gate for the ten separate native Fusion modules."""

import argparse
import hashlib
import json
import pathlib
import struct
import sys


MODULE_REQUIREMENTS = {
    "BN-M01": ("PULL_OUT_STOVE_TRAY", "BURNER_OUTER", "STOVE_CONTROL_KNOB",
               "WIND_GUARD_BACK", "UPPER_PREP_SURFACE", "COOKWARE_DRAWER_CASE"),
    "BN-M02": ("PANTRY_DRAWER_1_CASE", "PANTRY_DRAWER_2_CASE",
               "PANTRY_DRAWER_3_BOTTOM", "PANTRY_DIVIDER_LONG",
               "PANTRY_DRAWER_3_HANDLE_GRIP"),
    "BN-M03": ("FRIDGE_BODY", "FRIDGE_LID", "FRIDGE_CARRY_HANDLE_GRIP",
               "COMPRESSOR_SLOT", "RESTRAINT_STRAP", "FRIDGE_SLIDE_TRAY"),
    "BN-M04": ("BASIN_FLOOR", "BASIN_WALL_LEFT", "FAUCET_RISER",
               "BASIN_DRAIN", "GREY_WATER_TANK", "WATER_PUMP", "SINK_HOSE_SEG"),
    "BN-M05": ("WATER_TANK", "TANK_MOLDED_RIB", "FILL_CAP", "SPIGOT",
               "TANK_RESTRAINT_STRAP", "SERVICE_PUMP", "DELIVERY_HOSE_SEG"),
    "BN-M06": ("SEALED_TOOL_DRAWER_CASE", "UPPER_ADJUSTABLE_SHELF",
               "MOLLE_PANEL", "MOLLE_SLOT", "RECOVERY_ROPE_SEG", "SHACKLE_PIN"),
    "BN-M07": ("POWER_STATION_ENCLOSURE", "POWER_DISPLAY", "AC_OUTLET",
               "DC_PORT", "USB_PORT", "POWER_VENT_SLOT", "CABLE_DRAWER_CASE"),
    "BN-M08": ("HEATER_BODY", "HEATER_DISPLAY", "HEATER_KNOB",
               "HEATER_VENT_SLOT", "SHOWER_HOSE_SEG", "SHOWER_HEAD",
               "QUICK_CONNECT", "WET_STORAGE_TRAY"),
    "BN-M09": ("RUGGED_CASE", "CASE_LID_RIB", "CASE_LATCH",
               "DEPLOYED_WORKTOP", "LAPTOP_SCREEN", "KEY", "ACCESSORY_DRAWER_CASE"),
    "BN-M10": ("FOLDED_FURNITURE_1", "FURNITURE_HINGE",
               "ROLLED_SOFT_GOOD_1", "COMPRESSION_STRAP", "CARGO_NET_UP",
               "NET_ANCHOR"),
}

# Every per-module check this gate applies. A report missing any of these was
# produced by an older validator and must not be read as a current pass.
CHECK_NAMES = (
    "local_qwen_revision_evidence",
    "ots_catalog_traceability",
    "bbox_24x20x18_within_0.01in",
    "twelve_separate_frame_members",
    "native_named_components",
    "required_visible_parts_named",
    "iso.png_1600x1200",
    "front.png_1600x1200",
    "material_capable_obj",
)

MIN_BYTES = {
    ".f3d": 100_000,
    ".step": 100_000,
    ".stl": 50_000,
    ".obj": 100_000,
    ".mtl": 100,
    ".png": 10_000,
}


def png_dimensions(path):
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    return struct.unpack(">II", data[16:24])


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validator_fingerprint():
    """Stamp the gate's own identity into its report.

    Without this a report produced by an older, looser validator is
    indistinguishable from a current pass, and a tightened gate can sit next to
    a stale green report indefinitely.
    """
    path = pathlib.Path(__file__).resolve()
    return {"validator": path.name, "validator_sha256": sha256(path)}


def validate(root, expected_reviews=300):
    failures = []
    results = []
    f3d_hashes = set()
    for module_id, required_parts in MODULE_REQUIREMENTS.items():
        folder = root / module_id
        report_path = folder / (module_id + "-build.json")
        module_result = {"module_id": module_id, "checks": {}}
        if not report_path.is_file():
            failures.append("%s missing build report" % module_id)
            results.append(module_result)
            continue
        report = json.loads(report_path.read_text())
        names = report.get("part_names", [])

        revision = report.get("local_model_revision_evidence", {})
        allowed_models = set(revision.get("allowed_models", []))
        module_models = set(revision.get("module_models", []))
        revision_ok = (
            int(revision.get("family_review_count", -1)) == expected_reviews and
            int(revision.get("module_review_count", -1)) == expected_reviews // 10 and
            revision.get("required_model") == "qwen/qwen2.5-coder-14b" and
            module_models <= allowed_models <= {
                "qwen/qwen2.5-coder-14b", "qwen2.5-coder-7b-instruct"
            }
        )
        module_result["checks"]["local_qwen_revision_evidence"] = revision_ok
        if not revision_ok:
            failures.append("%s revision evidence does not match %d family reviews" %
                            (module_id, expected_reviews))

        ots_ids = report.get("represented_ots_catalog_ids", [])
        ots_ok = len(ots_ids) >= 10 and all(isinstance(item, str) for item in ots_ids)
        module_result["checks"]["ots_catalog_traceability"] = ots_ok
        if not ots_ok:
            failures.append("%s lacks OTS catalog traceability" % module_id)

        bbox = report.get("measured_bbox", {})
        expected_bbox = {"width_in": 24.0, "depth_in": 20.0, "height_in": 18.0}
        bbox_ok = all(abs(float(bbox.get(k, -999)) - v) <= 0.01
                      for k, v in expected_bbox.items())
        module_result["checks"]["bbox_24x20x18_within_0.01in"] = bbox_ok
        if not bbox_ok:
            failures.append("%s bbox failed: %s" % (module_id, bbox))

        frame_names = [n for n in names if n.startswith("FRAME_POST_") or
                       n.startswith("FRAME_WIDTH_RAIL_") or
                       n.startswith("FRAME_DEPTH_RAIL_")]
        frame_ok = len(frame_names) == 12
        module_result["checks"]["twelve_separate_frame_members"] = frame_ok
        if not frame_ok:
            failures.append("%s has %d named frame members" %
                            (module_id, len(frame_names)))

        component_count = int(report.get("component_count", 0))
        component_ok = component_count >= 50 and component_count == len(names)
        module_result["checks"]["native_named_components"] = component_ok
        module_result["component_count"] = component_count
        if not component_ok:
            failures.append("%s component registry mismatch" % module_id)

        missing_parts = [token for token in required_parts
                         if not any(name.startswith(token) for name in names)]
        features_ok = not missing_parts
        module_result["checks"]["required_visible_parts_named"] = features_ok
        module_result["missing_required_parts"] = missing_parts
        if missing_parts:
            failures.append("%s missing required parts: %s" %
                            (module_id, ", ".join(missing_parts)))

        files = [
            folder / (module_id + ext) for ext in (".f3d", ".step", ".stl", ".obj", ".mtl")
        ] + [folder / (module_id + suffix) for suffix in ("-iso.png", "-front.png")]
        file_checks = {}
        for path in files:
            limit = MIN_BYTES[path.suffix.lower()]
            ok = path.is_file() and path.stat().st_size >= limit
            file_checks[path.name] = {"ok": ok,
                                      "bytes": path.stat().st_size if path.is_file() else 0}
            if not ok:
                failures.append("%s missing/undersized %s" % (module_id, path.name))
        module_result["files"] = file_checks

        for suffix in ("-iso.png", "-front.png"):
            png = folder / (module_id + suffix)
            try:
                dims = png_dimensions(png)
                ok = dims == (1600, 1200)
            except Exception:
                dims, ok = None, False
            module_result["checks"][suffix[1:] + "_1600x1200"] = ok
            if not ok:
                failures.append("%s %s dimensions are %s" % (module_id, suffix, dims))

        mtl = (folder / (module_id + ".mtl")).read_text()
        required_materials = ("BN_ALUMINUM", "BN_BLACK", "BN_CHARCOAL")
        materials_ok = all(name in mtl for name in required_materials)
        module_result["checks"]["material_capable_obj"] = materials_ok
        if not materials_ok:
            failures.append("%s OBJ material set incomplete" % module_id)

        f3d_hash = sha256(folder / (module_id + ".f3d"))
        f3d_hashes.add(f3d_hash)
        module_result["f3d_sha256"] = f3d_hash
        results.append(module_result)

    separate_ok = len(f3d_hashes) == len(MODULE_REQUIREMENTS)
    if not separate_ok:
        failures.append("native F3D archives are not ten distinct files")
    output = {
        "result": "PASS" if not failures else "FAIL",
        "expected_module_reviews": expected_reviews,
        "checks_applied": sorted(CHECK_NAMES),
        "module_count": len(results),
        "distinct_f3d_archives": len(f3d_hashes),
        "checks": {
            "ten_module_directories": len(results) == 10,
            "ten_distinct_native_f3d_archives": separate_ok,
        },
        "failures": failures,
        "modules": results,
    }
    output.update(validator_fingerprint())
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=pathlib.Path(__file__).resolve().parents[1] / "fusion-native" / "exports",
        type=pathlib.Path,
    )
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--expected-reviews", type=int, default=300)
    args = parser.parse_args()
    result = validate(args.root, args.expected_reviews)
    output = args.output or args.root / "native-validation-report.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("NATIVE_FAMILY_%s modules=%d distinct_f3d=%d report=%s" %
          (result["result"], result["module_count"],
           result["distinct_f3d_archives"], output))
    for failure in result["failures"]:
        print("- " + failure)
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
