#!/usr/bin/env python3
import csv
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parent


def main():
    family=json.loads((ROOT/"module-family.json").read_text())
    with (ROOT/"procurement-bom.csv").open(newline="") as stream:
        rows=list(csv.DictReader(stream))
    jobs=ROOT/"jobs"; jobs.mkdir(exist_ok=True)
    for module in family["modules"]:
        bom=[row for row in rows if row["module_id"] in (module["id"],"ALL-10")]
        unresolved=sorted({row["status"] for row in bom if row["status"] != "ORDERABLE"})
        status="BLOCKED_SOURCING" if any(s.startswith("SOURCE_REQUIRED") for s in unresolved) else "PROTOTYPE_READY"
        job={
            "schema_version":1,"module_id":module["id"],"name":module["name"],
            "status":status,"geometry_source":"../module-family.json",
            "frame":{"outside_in":[24.0,20.0,18.0],"inner_clear_in":[22.0,18.0,16.0],
                     "profile":"EX-1010 / 1010-S compatible",
                     "cut_list":family["common_frame"]["cut_list"]},
            "components":module["internal_layout"],
            "primary_component":module["primary_component"],
            "bom_dispositions":sorted({row["status"] for row in bom}),
            "validators":{"geometry":"../validate_family.py","clearance":"../clearance_check.py",
                          "bom_reconciliation":"../bom_reconcile.py","human_review":True},
            "release_gates":["approved dynamic load case and safety factor",
                             "native Fusion assembly and interference evidence",
                             "all SOURCE_REQUIRED/CUSTOM_REQUIRED rows resolved",
                             "physical fit/load/vibration and module-specific safety tests",
                             "supplier drop-ship terms accepted","human release signature"],
            "required_evidence":{"supplier":"../SUPPLIER-READINESS.md plus written supplier response",
                                 "physical_tests":"../PHYSICAL-TEST-PLAN.md completed records",
                                 "release_checklist":"../RELEASE-EVIDENCE-CHECKLIST.md completed",
                                 "clearance":"../clearance-report.json",
                                 "bom_reconciliation":"../bom-reconciliation-report.json"},
            "blockers":module["custom_or_unresolved"]
        }
        (jobs/f"{module['id']}.job.json").write_text(json.dumps(job,indent=2)+"\n")
    print(f"PASS: generated {len(family['modules'])} production jobs")


if __name__=="__main__": main()
