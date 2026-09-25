#!/usr/bin/env python3
"""Gate the visual iteration ledger, in the shape of validate_revision_ledger.py.

    python3 validate_visual_ledger.py [--ledger PATH] [--min-cycles 10]

Checks that the sweep actually happened, that every record names the model that
produced it, that no adopted change violated a frame invariant, and that the
image hashes in the ledger still match the images on disk.
"""

import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_LEDGER = HERE / "visual-iteration-ledger.json"
RENDER_DIR = HERE / "renders"
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]

# The scene may only carry keys the renderer understands. Anything else means a
# model invented a parameter, which is the failure mode this gate exists for.
ALLOWED_SCENE_KEYS = {
    "environment", "background_solid", "ground", "ground_flattened",
    "ground_position", "ground_offset", "ground_reflections", "ground_roughness",
    "brightness", "exposure", "focal_length", "light_angle", "quality",
    "distance_factor", "target_offset_in", "depth_of_field", "dof_blur",
    "width", "height",
    "transparent", "name", "module", "view",
}


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=pathlib.Path, default=DEFAULT_LEDGER)
    parser.add_argument("--min-cycles", type=int, default=10)
    parser.add_argument("--min-reviews", type=int, default=100)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    if not args.ledger.is_file():
        print("VISUAL_LEDGER_FAIL no ledger at %s" % args.ledger, file=sys.stderr)
        return 1
    ledger = json.loads(args.ledger.read_text())
    failures = []
    cycles = ledger.get("cycles", [])

    if len(cycles) < args.min_cycles:
        failures.append("only %d cycle(s); %d required"
                        % (len(cycles), args.min_cycles))

    reviews = 0
    for cycle in cycles:
        seen = set()
        for record in cycle.get("modules", []):
            reviews += 1
            module_id = record.get("module_id")
            seen.add(module_id)
            if module_id not in MODULE_IDS:
                failures.append("cycle %s: unknown module %r"
                                % (cycle.get("cycle"), module_id))
            if not record.get("proposed_by"):
                failures.append("cycle %s %s: no model attribution"
                                % (cycle.get("cycle"), module_id))
            vlm = record.get("vlm")
            if vlm:
                if not vlm.get("_model"):
                    failures.append("cycle %s %s: VLM record has no model id"
                                    % (cycle.get("cycle"), module_id))
                if vlm.get("verdict") == "PASS" and vlm.get("blocking_findings"):
                    failures.append(
                        "cycle %s %s: self-contradictory VLM verdict survived into "
                        "the ledger" % (cycle.get("cycle"), module_id))
        missing = set(MODULE_IDS) - seen
        if missing:
            failures.append("cycle %s: missing %s"
                            % (cycle.get("cycle"), ", ".join(sorted(missing))))
        for key in ("scene_before", "scene_after"):
            unknown = set(cycle.get(key, {})) - ALLOWED_SCENE_KEYS
            if unknown:
                failures.append("cycle %s: %s has invented key(s) %s"
                                % (cycle.get("cycle"), key, ", ".join(sorted(unknown))))

    if reviews < args.min_reviews:
        failures.append("only %d module review(s); %d required"
                        % (reviews, args.min_reviews))

    # Every hash in the final cycle must still match what is on disk, or the
    # ledger is describing images that no longer exist.
    if cycles:
        for record in cycles[-1].get("modules", []):
            recorded = record.get("sha256")
            path = RENDER_DIR / ("%s-hero.png" % record.get("module_id"))
            if not recorded:
                continue
            if not path.is_file():
                failures.append("%s: ledger hash but no image on disk" % path.name)
            elif sha256(path) != recorded:
                failures.append("%s: image on disk does not match the ledger hash"
                                % path.name)

    document = {
        "gate": "visual_iteration_ledger",
        "gate_sha256": sha256(pathlib.Path(__file__)),
        "cycles": len(cycles),
        "module_reviews": reviews,
        "text_model": ledger.get("text_model"),
        "vision_model": ledger.get("vision_model"),
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
    }
    if args.output:
        args.output.write_text(json.dumps(document, indent=2) + "\n")
    if failures:
        print("VISUAL_LEDGER_FAIL %d failure(s)" % len(failures))
        for failure in failures[:20]:
            print("  - %s" % failure)
        return 1
    print("VISUAL_LEDGER_PASS cycles=%d reviews=%d text=%s vision=%s"
          % (len(cycles), reviews, document["text_model"], document["vision_model"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
