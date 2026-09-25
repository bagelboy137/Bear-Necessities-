#!/usr/bin/env python3
"""Generate order-linked prototype BOMs for each module from the curated catalog."""

import argparse
import csv
import datetime as dt
import hashlib
import json
import pathlib


HERE = pathlib.Path(__file__).resolve().parent
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]
COMMON = [
    ("TNUTZ-EX1010-18", 8, "pc", "Exact 18-inch cut; no machining for bracket prototype"),
    ("TNUTZ-EX1010-22", 4, "pc", "Exact 22-inch cut; no machining for bracket prototype"),
    ("8020-4132", 24, "pc", "Prototype quantity only; joint release requires dynamic test"),
    ("8020-3393", 48, "pc", "Two compatible assemblies per 4132 bracket"),
    ("TNUTZ-HAN015AL", 2, "pc", "Carry handles are not authorized for a loaded lift until tested"),
    ("TNUTZ-GAS010A", 20, "ft", "Allowance including trim; replace with drawing-derived length"),
    ("TNUTZ-BUM010TS", 8, "ft", "Allowance for lower perimeter"),
    ("TAP-HYPACT-PANEL", 1, "cut-panel lot", "Order only from released DXF/panel drawings")
]

MODULE_SPECIFIC = {
    "BN-M01": [("JETBOIL-GENESIS", 1, "pc", "Primary appliance"),
                ("ACCURIDE-3832-C16", 1, "pair", "Stove tray"),
                ("SOUTHCO-E3-57-25", 2, "pc", "Stove tray and cookware drawer")],
    "BN-M02": [("RUBBERMAID-FG350700WHT", 3, "pc", "Shallow pantry bins; matching lids also required from dealer"),
                ("ACCURIDE-3832-C16", 3, "pair", "Three drawers"),
                ("SOUTHCO-E3-57-25", 3, "pc", "One per drawer")],
    "BN-M03": [("ENGEL-MD14", 0, "pc", "Rejected from buy-ready BOM because manufacturer shows sold out"),
                ("ENGEL-MHD13-ALT", 1, "pc", "Procurement alternate; verify dimensions and intended use"),
                ("ACCURIDE-3832-C16", 1, "pair", "Fridge slide tray"),
                ("NRS-HD-STRAP", 2, "pc", "Select field-fit length after restraint test")],
    "BN-M04": [("DOMETIC-VA8005", 1, "pc", "Sink and siphon"),
                ("SHURFLO-4008", 1, "pc", "Demand pump; install accessories remain schematic-dependent"),
                ("RELIANCE-AQUATAINER-4G", 1, "pc", "Dedicated and permanently labeled grey-water container"),
                ("NRS-HD-STRAP", 2, "pc", "Grey tank restraint")],
    "BN-M05": [("RELIANCE-AQUATAINER-7G", 1, "pc", "Potable-water container"),
                ("SHURFLO-4008", 1, "pc", "Demand pump; install accessories remain schematic-dependent"),
                ("NRS-HD-STRAP", 2, "pc", "Full-tank restraint")],
    "BN-M06": [("PELICAN-1450", 1, "pc", "Recovery/tool case"),
                ("ACCURIDE-3832-C16", 1, "pair", "Case drawer tray"),
                ("NRS-HD-STRAP", 2, "pc", "Soft recovery-gear retention")],
    "BN-M07": [("ECOFLOW-RIVER3-PLUS", 1, "pc", "Primary power station"),
                ("SOUTHCO-E3-57-25", 1, "pc", "Cable drawer")],
    "BN-M08": [("JOOLCA-HOTTAP-V2", 1, "kit", "Essentials kit; transport only inside module"),
                ("NRS-HD-STRAP", 2, "pc", "Heater and wet-hose restraint"),
                ("SOUTHCO-E3-57-25", 1, "pc", "Wet-storage tray")],
    "BN-M09": [("PELICAN-1485", 1, "pc", "Field-office/camera case"),
                ("ACCURIDE-3832-C16", 1, "pair", "Accessory drawer"),
                ("SOUTHCO-E3-57-25", 2, "pc", "Worktop and accessory drawer")],
    "BN-M10": [("HELINOX-CHAIR-ONE", 2, "pc", "Two packed chairs"),
                ("HELINOX-TABLE-ONE", 1, "pc", "One packed table"),
                ("NRS-HD-STRAP", 4, "pc", "Individual furniture and soft-goods retention")]
}

FIELDNAMES = ["module_id", "catalog_id", "status", "ots_class", "vendor",
              "part_number",
              "description", "quantity", "unit", "order_url", "evidence_url",
              "module_use", "catalog_notes", "ots_rationale"]


def rows_for(module_id, catalog):
    rows = []
    for catalog_id, quantity, unit, use in COMMON + MODULE_SPECIFIC[module_id]:
        item = catalog[catalog_id]
        rows.append({
            "module_id": module_id,
            "catalog_id": catalog_id,
            "status": item["status"],
            # Independent of status: status is "can I buy it today", ots_class is
            # "is it off the shelf at all".
            "ots_class": item["ots_class"],
            "vendor": item["vendor"],
            "part_number": item["part_number"],
            "description": item["description"],
            "quantity": quantity,
            "unit": unit,
            "order_url": item["order_url"],
            "evidence_url": item["evidence_url"],
            "module_use": use,
            "catalog_notes": item["notes"],
            "ots_rationale": item["ots_rationale"]
        })
    return rows


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=pathlib.Path, default=HERE / "ots-components.json")
    parser.add_argument("--output-dir", type=pathlib.Path, default=HERE / "boms")
    args = parser.parse_args()
    source = json.loads(args.catalog.read_text())
    catalog = {item["id"]: item for item in source["components"]}
    required_ids = ({item[0] for values in MODULE_SPECIFIC.values()
                     for item in values} | {item[0] for item in COMMON})
    missing = sorted(required_ids - set(catalog))
    if missing:
        raise RuntimeError("catalog IDs missing: %s" % ", ".join(missing))
    all_rows = []
    module_counts = {}
    for module_id in MODULE_IDS:
        rows = rows_for(module_id, catalog)
        all_rows.extend(rows)
        module_counts[module_id] = len(rows)
        write_csv(args.output_dir / (module_id + "-prototype-bom.csv"), rows)
    write_csv(args.output_dir / "all-modules-prototype-bom.csv", all_rows)
    unresolved = [row for row in all_rows if (row["quantity"] and
                  ("HOLD" in row["status"] or "SOLD_OUT" in row["status"] or
                   "CHECK" in row["status"] or "DEALER" in row["status"] or
                   "VERIFY" in row["status"]))]
    report = {
        "schema_version": 1,
        "result": "PASS_WITH_ENGINEERING_AND_PROCUREMENT_HOLDS",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "catalog": str(args.catalog.resolve()),
        "catalog_sha256": hashlib.sha256(args.catalog.read_bytes()).hexdigest(),
        "module_count": len(module_counts),
        "row_count": len(all_rows),
        "module_row_counts": module_counts,
        "non_buy_ready_row_count": len(unresolved),
        "non_buy_ready_records": [{key: row[key] for key in
                                    ("module_id", "catalog_id", "status", "module_use")}
                                   for row in unresolved],
        "scope": "Order-linked prototype component BOM. Custom-cut panels require released drawings; plumbing, wiring, vehicle anchors, and frame joints remain engineering holds.",
        "purchase_authority": "No purchase is authorized by this file. Recheck stock, suffixes, fit, and specifications before ordering."
    }
    (args.output_dir / "bom-generation-report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print("MODULE_BOMS_PASS modules=%d rows=%d holds=%d output=%s" %
          (len(module_counts), len(all_rows), len(unresolved), args.output_dir))


if __name__ == "__main__":
    main()
