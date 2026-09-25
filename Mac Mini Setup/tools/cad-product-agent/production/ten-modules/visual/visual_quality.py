#!/usr/bin/env python3
"""Deterministic marketing-quality gate for Bear Necessities module renders.

No model, no tokens. Measures the signals that separate a lit product render from
a flat CAD viewport capture, per VISUAL-MARKETING-BRIEF.md.

    python3 visual_quality.py --baseline     score the legacy renders, write baseline
    python3 visual_quality.py --all          score the current marketing renders
    python3 visual_quality.py --images a.png b.png
    python3 visual_quality.py --demo         self-check

Exit status is 0 only when every scored image passes every gate.
"""

import argparse
import hashlib
import json
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
STUDY = HERE.parent
LEGACY_EXPORTS = STUDY / "fusion-native" / "exports"
MARKETING_EXPORTS = HERE / "renders"
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]

THRESHOLDS_PATH = HERE / "visual-quality-thresholds.json"

# Defaults are written to disk on first run so tuning is data, not a code edit.
DEFAULT_THRESHOLDS = {
    "_source": "VISUAL-MARKETING-BRIEF.md, 2026-08-26",
    "tonal_p99_min": 215.0,
    "specular_fraction_min": 0.0008,
    "metal_modulation_min": 22.0,
    "panel_modulation_min": 14.0,
    "edge_richness_min": 50.0,
    "subject_coverage_min": 0.25,
    "subject_coverage_max": 0.75,
    "subject_centering_max": 0.08,
    "background_variation_min": 2.0,
    "contact_shadow_ratio_max": 0.90,
    "resolution": {
        "hero": [2400, 1800],
        "front": [1600, 1200],
        "detail": [1600, 1200],
        "alpha": [2400, 1800],
        "iso": [1600, 1200],
    },
}

# Luminance cutoffs. SPECULAR_LUM is deliberately above anything a flat viewport
# capture produces (measured peak 180 across nine of ten legacy renders).
SPECULAR_LUM = 235.0
METAL_LUM_SPLIT = 110.0
NEUTRAL_SAT_MAX = 30.0
OPAQUE_ALPHA = 200
EDGE_GRADIENT = 12.0


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def load_thresholds(path=THRESHOLDS_PATH):
    if path.is_file():
        merged = dict(DEFAULT_THRESHOLDS)
        merged.update(json.loads(path.read_text()))
        return merged
    path.write_text(json.dumps(DEFAULT_THRESHOLDS, indent=2) + "\n")
    return dict(DEFAULT_THRESHOLDS)


def view_of(path):
    """Derive the view label from BN-M01-hero.png -> 'hero'."""
    stem = pathlib.Path(path).stem
    for label in ("hero", "front", "detail", "iso", "alpha"):
        if stem.endswith("-" + label):
            return label
    return "unknown"


def _row_background(luminance, margin_fraction=0.03):
    """Per-row background luminance, sampled from the left and right margins.

    A studio backdrop is usually a vertical gradient, so a single scalar
    background level misclassifies the top or bottom of the frame as subject.
    Sampling per row handles flat and gradient backdrops alike. The brief caps
    subject coverage at 0.75 and centres it, so the margins stay clear of it.
    """
    width = luminance.shape[1]
    margin = max(8, int(width * margin_fraction))
    edges = np.concatenate([luminance[:, :margin], luminance[:, -margin:]], axis=1)
    return np.median(edges, axis=1)[:, None]


def _load_matte(path):
    """Object matte written beside an opaque render as <name>-matte.png.

    A contact shadow cannot be separated from the object by luminance alone: the
    shadow is itself a departure from the backdrop, so any threshold that finds
    the object also swallows the shadow, and the metric can never fire. The
    renderer already knows which pixels are the object, so it writes that mask
    out. One extra file beats a segmentation heuristic that is wrong on exactly
    the images that matter.
    """
    path = pathlib.Path(path)
    matte_path = path.with_name(path.stem + "-matte.png")
    if not matte_path.is_file():
        return None
    # A matte older than the render it describes is a matte of a DIFFERENT
    # framing. Silently using one makes every coverage and contact-shadow number
    # wrong while looking perfectly plausible - it cost four render cycles on
    # 2026-08-26 before the identical coverage across four framings gave it away.
    if matte_path.stat().st_mtime < path.stat().st_mtime - 1.0:
        return "STALE"
    matte = np.asarray(Image.open(matte_path).convert("L")).astype(np.float32)
    return matte > 127


def measure(path, matte=None):
    """Every deterministic signal for one image. Pure measurement, no verdicts."""
    image = Image.open(path)
    width, height = image.size
    array = np.asarray(image.convert("RGBA")).astype(np.float32)
    alpha, rgb = array[..., 3], array[..., :3]
    luminance = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    saturation = rgb.max(axis=2) - rgb.min(axis=2)

    row_bg = _row_background(luminance)
    transparent = alpha < 10
    has_alpha_matte = bool(transparent.mean() > 0.001)
    stale_matte = False
    if matte is None:
        matte = _load_matte(path)
    if isinstance(matte, str) and matte == "STALE":
        stale_matte, matte = True, None
    if matte is not None and getattr(matte, "shape", None) != luminance.shape:
        matte = None

    if has_alpha_matte:
        subject, source = alpha > OPAQUE_ALPHA, "alpha"
    elif matte is not None:
        subject, source = matte, "matte"
    else:
        # Ad-hoc opaque image with no matte: fall back to departure from the
        # fitted backdrop. Good enough to score framing and tone; not good enough
        # to judge a contact shadow, which is why that metric goes unmeasured.
        subject, source = (np.abs(luminance - row_bg) > 12.0) | (
            saturation > NEUTRAL_SAT_MAX), "heuristic"

    stats = {
        "width": width,
        "height": height,
        "view": view_of(path),
        "subject_coverage": float(subject.mean()),
        "subject_mask_source": source,
        "has_alpha_matte": has_alpha_matte,
        "stale_matte": stale_matte,
    }
    if subject.sum() < 512:
        stats["error"] = "subject mask is empty or negligible"
        return stats

    fg = luminance[subject]
    stats["tonal_p01"] = float(np.percentile(fg, 1))
    stats["tonal_p99"] = float(np.percentile(fg, 99))
    stats["tonal_peak"] = float(fg.max())
    stats["specular_fraction"] = float((fg > SPECULAR_LUM).mean())

    neutral = subject & (saturation < NEUTRAL_SAT_MAX)
    metal = neutral & (luminance > METAL_LUM_SPLIT)
    panel = neutral & (luminance <= METAL_LUM_SPLIT)
    stats["metal_fraction"] = float(metal.mean())
    stats["metal_modulation"] = float(luminance[metal].std()) if metal.sum() > 512 else 0.0
    stats["panel_modulation"] = float(luminance[panel].std()) if panel.sum() > 512 else 0.0
    stats["colored_fraction"] = float((saturation[subject] > 25).mean())

    gy, gx = np.gradient(luminance)
    edges = (np.hypot(gx, gy) > EDGE_GRADIENT) & subject
    stats["edge_density"] = float(edges.sum() / subject.sum())
    # edge_density is edge PIXELS over subject AREA, so it falls as the subject
    # gets bigger in frame - edges grow like a perimeter, area grows like a
    # square. That makes it useless as a fixed floor across framings: the same
    # module, equally detailed, scored 0.093 far away and 0.055 close up.
    # Dividing by sqrt(area) instead gives a scale-invariant "edge richness".
    stats["edge_richness"] = float(edges.sum() / np.sqrt(subject.sum()))

    ys, xs = np.where(subject)
    cx, cy = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0
    stats["subject_centering"] = float(max(
        abs(cx - width / 2.0) / width, abs(cy - height / 2.0) / height))
    stats["subject_bbox"] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    stats["distinct_alpha_values"] = int(len(np.unique(alpha)))

    if has_alpha_matte:
        stats["background_class"] = "transparent"
        stats["background_variation"] = 0.0
    else:
        variation = float(row_bg.std())
        stats["background_variation"] = variation
        stats["background_class"] = "gradient" if variation >= 2.0 else "flat"

    if has_alpha_matte or source != "matte":
        stats["contact_shadow_ratio"] = None
    else:
        stats["contact_shadow_ratio"] = _contact_shadow_ratio(
            luminance, row_bg, subject, int(ys.max()), int(xs.min()), int(xs.max()),
            height)
    return stats


def _contact_shadow_ratio(luminance, row_bg, subject, subject_bottom, left, right,
                          height):
    """Ground luminance directly beneath the object over the ground beside it.

    The reference is deliberately LOCAL - the same rows, in a strip immediately
    left and right of the object - not the far margins. A studio cyclorama falls
    off toward the edges of frame, so a far-margin reference makes the lit floor
    under the product read as BRIGHTER than background (measured 1.41 on BN-M01)
    and the metric never fires. Comparing against the floor right next to the
    object is what actually isolates the shadow.

    Below 1.0 means the ground darkens under the module: a contact shadow.
    """
    band_height = max(8, int(height * 0.05))
    top = min(subject_bottom - band_height // 2, height - 1)
    bottom = min(subject_bottom + band_height, height)
    if bottom - top < 4 or right <= left:
        return None

    span = right - left
    flank = max(12, int(span * 0.35))
    ref_left = max(0, left - flank)
    ref_right = min(luminance.shape[1], right + flank)

    under = ~subject[top:bottom, left:right + 1]
    if under.sum() < 256:
        return None
    under_lum = luminance[top:bottom, left:right + 1][under]

    beside = []
    for slice_ in (slice(ref_left, left), slice(right + 1, ref_right)):
        if slice_.stop <= slice_.start:
            continue
        mask = ~subject[top:bottom, slice_]
        if mask.sum():
            beside.append(luminance[top:bottom, slice_][mask])
    if not beside:
        return None
    beside_lum = np.concatenate(beside)
    if beside_lum.size < 256 or beside_lum.mean() <= 1.0:
        return None
    return float(under_lum.mean() / beside_lum.mean())


def grade(stats, thresholds):
    """Turn measurements into pass/fail. Alpha cut-outs skip the ground gates."""
    failures = []
    if "error" in stats:
        return [stats["error"]]
    view = stats["view"]
    is_alpha = view == "alpha"

    required = thresholds["resolution"].get(view)
    if required and (stats["width"] < required[0] or stats["height"] < required[1]):
        failures.append("resolution %dx%d below %dx%d for view '%s'" % (
            stats["width"], stats["height"], required[0], required[1], view))

    def below(key, limit_key, label):
        limit = thresholds[limit_key]
        if stats.get(key, 0.0) < limit:
            failures.append("%s %.4f below %.4f" % (label, stats.get(key, 0.0), limit))

    below("tonal_p99", "tonal_p99_min", "tonal_p99")
    below("specular_fraction", "specular_fraction_min", "specular_fraction")
    below("metal_modulation", "metal_modulation_min", "metal_modulation")
    below("panel_modulation", "panel_modulation_min", "panel_modulation")
    below("edge_richness", "edge_richness_min", "edge_richness")

    coverage = stats["subject_coverage"]
    if not (thresholds["subject_coverage_min"] <= coverage
            <= thresholds["subject_coverage_max"]):
        failures.append("subject_coverage %.3f outside %.2f-%.2f" % (
            coverage, thresholds["subject_coverage_min"],
            thresholds["subject_coverage_max"]))
    if stats["subject_centering"] > thresholds["subject_centering_max"]:
        failures.append("subject_centering %.3f above %.3f" % (
            stats["subject_centering"], thresholds["subject_centering_max"]))

    if not is_alpha:
        if stats["background_class"] == "transparent":
            failures.append("background is transparent; hero views need a ground")
        elif stats["background_variation"] < thresholds["background_variation_min"]:
            failures.append("background_variation %.2f below %.2f (flat backdrop)" % (
                stats["background_variation"], thresholds["background_variation_min"]))
        ratio = stats["contact_shadow_ratio"]
        if stats.get("stale_matte"):
            failures.append(
                "object matte is OLDER than this render - it describes a different "
                "framing. Re-render the alpha pass; every coverage and shadow "
                "number here is unreliable until you do.")
        elif ratio is None:
            failures.append(
                "contact shadow unverifiable: no object matte beside this render "
                "(expected <name>-matte.png)")
        elif ratio > thresholds["contact_shadow_ratio_max"]:
            failures.append("contact_shadow_ratio %.3f above %.3f (module floats)" % (
                ratio, thresholds["contact_shadow_ratio_max"]))
    return failures


def score_images(paths, thresholds):
    results = []
    for path in paths:
        path = pathlib.Path(path)
        stats = measure(path)
        failures = grade(stats, thresholds)
        results.append({
            "path": str(path),
            "name": path.name,
            "sha256": sha256(path),
            "metrics": stats,
            "failures": failures,
            "result": "PASS" if not failures else "FAIL",
        })
    return results


def report(results, thresholds, label, missing=None):
    missing = list(missing or [])
    passed = sum(1 for item in results if item["result"] == "PASS")
    return {
        "gate": "visual_quality",
        "gate_sha256": sha256(pathlib.Path(__file__)),
        "label": label,
        "thresholds": thresholds,
        "images": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "missing": missing,
        "result": "PASS" if (passed == len(results) and results
                               and not missing) else "FAIL",
        "results": results,
    }


def legacy_paths():
    found = []
    for module_id in MODULE_IDS:
        for view in ("iso", "front"):
            path = LEGACY_EXPORTS / module_id / ("%s-%s.png" % (module_id, view))
            if path.is_file():
                found.append(path)
    return found


def marketing_paths():
    """Only canonical deliverables, never exploratory scene-sweep images."""
    return [MARKETING_EXPORTS / ("%s-%s.png" % (module_id, view))
            for module_id in MODULE_IDS
            for view in ("hero", "front", "detail", "alpha")
            if (MARKETING_EXPORTS / ("%s-%s.png" % (module_id, view))).is_file()]


def missing_marketing_names(paths):
    present = {pathlib.Path(path).name for path in paths}
    expected = {"%s-%s.png" % (module_id, view)
                for module_id in MODULE_IDS
                for view in ("hero", "front", "detail", "alpha")}
    return sorted(expected - present)


def print_table(results):
    header = ("%-22s %-8s %6s %8s %8s %8s %6s  %s"
              % ("image", "view", "p99", "specular", "metal", "edge", "cover", "result"))
    print(header)
    print("-" * len(header))
    for item in results:
        m = item["metrics"]
        print("%-22s %-8s %6.1f %8.4f %8.2f %8.4f %6.3f  %s" % (
            item["name"], m.get("view", "?"), m.get("tonal_p99", 0.0),
            m.get("specular_fraction", 0.0), m.get("metal_modulation", 0.0),
            m.get("edge_density", 0.0), m.get("subject_coverage", 0.0),
            item["result"]))
        for failure in item["failures"]:
            print("      - %s" % failure)


def demo():
    """Self-check: a flat capture must fail, a lit render on a ground must pass."""
    import tempfile

    rng = np.random.default_rng(0)
    tmp = pathlib.Path(tempfile.mkdtemp())

    # Flat capture: uniform grey subject, transparent background, no highlight.
    flat = np.zeros((1200, 1600, 4), dtype=np.uint8)
    flat[300:900, 400:1200, :3] = 150
    flat[300:900, 400:1200, 3] = 255
    flat[400:800, 500:1100, :3] = 70
    flat_path = tmp / "BN-M01-iso.png"
    Image.fromarray(flat).save(flat_path)

    # Lit render: gradient ground, contact shadow, modulated metal, specular hits.
    height, width = 1800, 2400
    top, bottom, left, right = 450, 1350, 500, 1900
    ground = np.linspace(120, 190, height, dtype=np.float32)[:, None] * np.ones(width)
    lit = np.dstack([ground, ground, ground]).astype(np.float32)

    ys = np.linspace(0, 1, bottom - top, dtype=np.float32)[:, None]
    xs = np.linspace(0, 1, right - left, dtype=np.float32)[None, :]
    metal = 120 + 110 * np.clip(np.sin(6 * xs + 2 * ys), 0, 1) ** 3 + 18 * ys
    lit[top:bottom, left:right] = np.dstack([metal, metal, metal])
    panel = 30 + 90 * xs[:, :1000] + 45 * ys[:700]
    lit[600:1300, 700:1700] = np.dstack([panel, panel, panel])

    # Slot lines and fasteners. A real module carries ~113 components; a smooth
    # synthetic slab would clear the tonal gates while failing edge_density, so
    # the fixture has to have detail for the pass case to mean anything.
    for x in range(left + 40, right - 40, 46):
        lit[top + 20:bottom - 20, x:x + 4] *= 0.35
    for y in range(top + 60, bottom - 60, 120):
        for x in range(left + 70, right - 70, 150):
            lit[y:y + 9, x:x + 9] *= 0.3

    # Contact shadow: below the object, fading with distance from it.
    for offset in range(0, 90):
        row = bottom + offset
        lit[row, left - 20:right + 20] *= 0.45 + 0.55 * (offset / 90.0)
    lit += rng.normal(0, 1.5, lit.shape)

    lit_rgb = np.clip(lit, 0, 255).astype(np.uint8)
    lit_rgba = np.dstack([lit_rgb, np.full((height, width, 1), 255, np.uint8)])
    lit_path = tmp / "BN-M01-hero.png"
    Image.fromarray(lit_rgba).save(lit_path)

    matte = np.zeros((height, width), dtype=np.uint8)
    matte[top:bottom, left:right] = 255
    Image.fromarray(matte).save(tmp / "BN-M01-hero-matte.png")

    thresholds = dict(DEFAULT_THRESHOLDS)
    flat_result = score_images([flat_path], thresholds)[0]
    lit_result = score_images([lit_path], thresholds)[0]

    assert flat_result["result"] == "FAIL", "flat CAD capture must fail the gate"
    reasons = " ".join(flat_result["failures"])
    assert "specular_fraction" in reasons, reasons
    assert "transparent" in reasons, reasons

    lit_metrics = lit_result["metrics"]
    assert lit_metrics["subject_mask_source"] == "matte", lit_metrics
    assert lit_metrics["specular_fraction"] > 0, "lit render has no highlight"
    assert lit_metrics["contact_shadow_ratio"] is not None, "shadow not measured"
    assert lit_metrics["contact_shadow_ratio"] < 0.9, (
        "shadow band not detected: %.3f" % lit_metrics["contact_shadow_ratio"])
    assert lit_metrics["background_class"] == "gradient", lit_metrics
    assert lit_result["result"] == "PASS", lit_result["failures"]

    # A render identical but for the shadow must fail, or the metric is decorative.
    no_shadow = np.dstack([ground, ground, ground]).astype(np.float32)
    no_shadow[top:bottom, left:right] = np.dstack([metal, metal, metal])
    no_shadow[600:1300, 700:1700] = np.dstack([panel, panel, panel])
    no_shadow += rng.normal(0, 1.5, no_shadow.shape)
    floating = np.dstack([np.clip(no_shadow, 0, 255).astype(np.uint8),
                          np.full((height, width, 1), 255, np.uint8)])
    float_path = tmp / "BN-M02-hero.png"
    Image.fromarray(floating).save(float_path)
    Image.fromarray(matte).save(tmp / "BN-M02-hero-matte.png")
    float_result = score_images([float_path], thresholds)[0]
    assert float_result["result"] == "FAIL", "a floating module must fail"
    assert any("floats" in f for f in float_result["failures"]), float_result["failures"]

    print("demo ok: flat capture fails (%d gates), lit render passes, "
          "shadowless render fails on contact shadow" % len(flat_result["failures"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--baseline", action="store_true",
                       help="score the legacy Fusion captures and write the baseline")
    group.add_argument("--all", action="store_true",
                       help="score every PNG under visual/renders/")
    group.add_argument("--images", nargs="+", help="score specific files")
    group.add_argument("--demo", action="store_true", help="run the self-check")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    if args.demo:
        demo()
        return 0

    thresholds = load_thresholds()
    if args.baseline:
        paths, label = legacy_paths(), "legacy-fusion-viewport-capture"
        output = args.output or HERE / "visual-quality-baseline.json"
        missing = []
    elif args.all:
        paths, label = marketing_paths(), "marketing-renders"
        output = args.output or HERE / "visual-quality-report.json"
        missing = missing_marketing_names(paths)
    else:
        paths, label = [pathlib.Path(p) for p in args.images], "ad-hoc"
        output = args.output
        missing = []

    if not paths:
        print("no images found for %s" % label, file=sys.stderr)
        return 2

    results = score_images(paths, thresholds)
    document = report(results, thresholds, label, missing=missing)
    print_table(results)
    print("\n%s: %d/%d passed" % (document["result"], document["passed"],
                                  document["images"]))
    if missing:
        print("missing %d canonical deliverable(s): %s" %
              (len(missing), ", ".join(missing)))
    if output:
        output.write_text(json.dumps(document, indent=2) + "\n")
        print("wrote %s" % output)
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
