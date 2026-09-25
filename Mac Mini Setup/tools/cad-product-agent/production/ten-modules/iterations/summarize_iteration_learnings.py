#!/usr/bin/env python3
"""Render the validated iteration ledger into the local-model retrieval note."""

import argparse
import collections
import json
import pathlib


HERE = pathlib.Path(__file__).resolve().parent
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=pathlib.Path,
                        default=HERE / "runs" / "iteration-ledger.json")
    parser.add_argument("--output", type=pathlib.Path,
                        default=HERE / "LOCAL-MODEL-ITERATION-LEARNINGS.md")
    args = parser.parse_args()
    ledger = json.loads(args.ledger.read_text())
    records = ledger.get("records", [])
    lines = [
        "# Local-model iteration learnings",
        "",
        "> Retrieval artifact for LM Studio prompts. It does not modify model weights and does not release engineering.",
        "",
        "- Required proposer: `%s`" % ledger.get("required_model"),
        "- Approved/used proposer counts: `%s`" % json.dumps(
            ledger.get("model_counts", {}), sort_keys=True
        ),
        "- Model policy: `%s`" % ledger.get("model_policy", {}).get("mode", "unknown"),
        "- Validated family cycles: %d / 30" % ledger.get("cycle_count", 0),
        "- Validated module reviews: %d / 300" % ledger.get("module_review_count", 0),
        "- Adopted prototype requirements: %d" % ledger.get("counts", {}).get("revisions_adopted", 0),
        "- Retained validated baselines: %d" % ledger.get("counts", {}).get("baseline_retained", 0),
        "",
        "## Durable framework rules",
        "",
        "- Use only catalog IDs from `ots-components.json`; never invent supplier facts.",
        "- Keep the 24 × 20 × 18 inch outer envelope and the 22 × 18 × 16 inch clear component envelope.",
        "- Keep exactly twelve separate 1-inch 10-Series frame members: eight 18-inch and four 22-inch cuts.",
        "- Treat local-model design findings as prototype requirements, not measurements, safety evidence, or fabrication release.",
        "- Preserve sold-out, rejected, dealer-order, and engineering-hold dispositions in the BOM.",
        "- Require current deterministic CAD validation and current-image visual review after a rebuild.",
        "",
    ]
    by_module = collections.defaultdict(list)
    for record in records:
        if record.get("gate_decision") == "ADOPT_AS_PROTOTYPE_REQUIREMENT":
            by_module[record["module_id"]].append(record)
    for module_id in MODULE_IDS:
        lines.extend(["## %s adopted requirements" % module_id, ""])
        values = by_module[module_id]
        if not values:
            lines.append("- No revision was adopted; all reviewed criteria retained the validated baseline.")
        else:
            for item in values:
                lines.append("- **%s / %s:** %s (evidence: `%s`; check: %s)" % (
                    item["stage"], item["criterion"], item["proposal"],
                    "`, `".join(item["evidence_ids"]), item["acceptance_check"]
                ))
        lines.append("")
    lines.extend([
        "## Remaining release boundary",
        "",
        "Dynamic frame and vehicle-anchor loads, panel tolerances, slide and latch suffixes, plumbing and wiring schematics, heat clearances, physical fit, motion, leak, thermal, vibration, and road tests require qualified human review before fabrication, installation, sale, or purchase of production quantities.",
        ""
    ])
    args.output.write_text("\n".join(lines))
    print("ITERATION_LEARNINGS_WRITTEN records=%d path=%s" % (len(records), args.output))


if __name__ == "__main__":
    main()
