#!/usr/bin/env python3
"""Deterministic six-face packaging clearance evidence."""
import argparse
import json
import pathlib

FACES = ("x_min", "x_max", "y_min", "y_max", "z_min", "z_max")
OUTSIDE = (24.0, 20.0, 18.0)
INNER_MIN = (1.0, 1.0, 1.0)
INNER_MAX = (23.0, 19.0, 17.0)


def evaluate(manifest, minimum):
    family = json.loads(pathlib.Path(manifest).read_text())
    results=[]; failures=[]
    for module in family["modules"]:
        for item in module["internal_layout"]:
            origin=item["origin"]; high=[origin[i]+item["size"][i] for i in range(3)]
            margins=[origin[0]-1,23-high[0],origin[1]-1,19-high[1],origin[2]-1,17-high[2]]
            allowed=set(item.get("allowed_contacts", []))
            face_results={face:round(margin,4) for face,margin in zip(FACES,margins)}
            bad=[face for face,margin in zip(FACES,margins)
                 if face not in allowed and margin < minimum]
            record={"module_id":module["id"],"item":item["label"],
                    "margins_in":face_results,"allowed_contacts":sorted(allowed),
                    "minimum_free_clearance_in":minimum,"pass":not bad,
                    "failed_faces":bad}
            results.append(record)
            if bad: failures.append(record)
    return {"pass":not failures,"outside_in":OUTSIDE,"inner_region_in":[INNER_MIN,INNER_MAX],
            "results":results,"failures":failures}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--minimum",type=float,default=0.125)
    args=parser.parse_args()
    report=evaluate(args.manifest,args.minimum)
    pathlib.Path(args.output).write_text(json.dumps(report,indent=2)+"\n")
    if not report["pass"]:
        for failure in report["failures"]:
            print(f"FAIL {failure['module_id']}/{failure['item']}: {failure['failed_faces']}")
        return 1
    print(f"PASS: {len(report['results'])} component envelopes meet six-face clearance policy")
    return 0


if __name__ == "__main__": raise SystemExit(main())
