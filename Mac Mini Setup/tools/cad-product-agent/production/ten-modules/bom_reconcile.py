#!/usr/bin/env python3
"""Reconcile family extrusion demand to procurement BOM quantities."""
import argparse
import csv
import json
import pathlib


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True)
    parser.add_argument("--bom",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    family=json.loads(pathlib.Path(args.manifest).read_text())
    module_count=len(family["modules"])
    expected={float(item["length"]):item["quantity"]*module_count
              for item in family["common_frame"]["cut_list"]}
    with pathlib.Path(args.bom).open(newline="") as stream:
        rows=list(csv.DictReader(stream))
    actual={}
    for row in rows:
        if row["level"]=="family" and row["part_number"]=="EX-1010" and row["status"]=="ORDERABLE":
            actual[float(row["order_length_in"])]=actual.get(float(row["order_length_in"]),0)+int(row["qty"])
    checks=[]
    for length,quantity in expected.items():
        checks.append({"part":"EX-1010","length_in":length,"expected_quantity":quantity,
                       "bom_quantity":actual.get(length,0),"pass":actual.get(length,0)==quantity})
    rejected=[row for row in rows if row["status"].startswith("REJECTED")]
    rejected_ok=all(int(row["qty"])==0 for row in rejected)
    report={"pass":all(c["pass"] for c in checks) and rejected_ok,
            "module_count":module_count,"extrusion_checks":checks,
            "total_extrusion_in":sum(c["length_in"]*c["expected_quantity"] for c in checks),
            "rejected_zero_quantity_pass":rejected_ok,"rejected_rows":len(rejected)}
    pathlib.Path(args.output).write_text(json.dumps(report,indent=2)+"\n")
    if not report["pass"]:
        print("FAIL: BOM does not reconcile to family manifest")
        return 1
    print(f"PASS: EX-1010 quantities reconcile for {module_count} modules; rejected rows remain zero")
    return 0


if __name__ == "__main__": raise SystemExit(main())
