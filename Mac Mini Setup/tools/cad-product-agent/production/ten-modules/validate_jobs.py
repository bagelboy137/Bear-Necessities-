#!/usr/bin/env python3
import json
import pathlib
import sys

ALLOWED={"PROTOTYPE_READY","BLOCKED_SOURCING","BLOCKED_ENGINEERING","AWAITING_HUMAN_REVIEW","RELEASED"}


def main(root):
    root=pathlib.Path(root); files=sorted((root/"jobs").glob("BN-M*.job.json")); errors=[]
    if len(files)!=10: errors.append(f"expected 10 jobs, got {len(files)}")
    seen=set()
    for path in files:
        job=json.loads(path.read_text()); module_id=job.get("module_id"); seen.add(module_id)
        if job.get("schema_version")!=1: errors.append(f"{path.name}: schema version")
        if job.get("status") not in ALLOWED: errors.append(f"{path.name}: status")
        if job.get("frame",{}).get("outside_in") != [24.0,20.0,18.0]: errors.append(f"{path.name}: outside")
        if job.get("frame",{}).get("inner_clear_in") != [22.0,18.0,16.0]: errors.append(f"{path.name}: inner")
        if job.get("frame",{}).get("cut_list") != [{"length":18.0,"quantity":8},{"length":22.0,"quantity":4}]: errors.append(f"{path.name}: cuts")
        if not job.get("components"): errors.append(f"{path.name}: components")
        if not job.get("validators",{}).get("human_review"): errors.append(f"{path.name}: human gate")
        if set(job.get("required_evidence",{})) != {"supplier","physical_tests","release_checklist","clearance","bom_reconciliation"}:
            errors.append(f"{path.name}: required evidence map")
        if job.get("status")=="RELEASED": errors.append(f"{path.name}: generated jobs cannot be RELEASED")
    if len(seen)!=10: errors.append("job IDs not unique")
    if errors:
        print("JOB VALIDATION FAILED:",*errors,sep="\n- ",file=sys.stderr); return 1
    print("PASS: 10 unique jobs preserve frame/cut/component/release invariants"); return 0


if __name__=="__main__": raise SystemExit(main(sys.argv[1] if len(sys.argv)>1 else pathlib.Path(__file__).parent))
