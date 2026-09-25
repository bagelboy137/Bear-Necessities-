#!/usr/bin/env python3
"""Validator-repaired output from the local Qwen2.5-Coder-14B CAD pass.

Packaging envelopes only: not structural analysis or manufacturer CAD.
"""
import json
import pathlib
import sys

import cadquery as cq
from cadquery import exporters

IN = 25.4
OUTSIDE = (24.0, 20.0, 18.0)

def load_modules(manifest_path):
    family = json.loads(pathlib.Path(manifest_path).read_text())
    modules = []
    for module in family["modules"]:
        components = [(item["label"], tuple(item["size"]), tuple(item["origin"]))
                      for item in module["internal_layout"]]
        modules.append((module["id"], module["name"], components))
    return modules


def box(size, origin):
    return cq.Workplane("XY").box(*(value*IN for value in size), centered=False).translate(tuple(value*IN for value in origin)).val()


def frame_members():
    w,d,h,p = (24*IN,20*IN,18*IN,1*IN)
    members=[]
    for x in (0,w-p):
        for y in (0,d-p): members.append(cq.Workplane("XY").box(p,p,h,centered=False).translate((x,y,0)).val())
    for y in (0,d-p):
        for z in (0,h-p): members.append(cq.Workplane("XY").box(w-2*p,p,p,centered=False).translate((p,y,z)).val())
    for x in (0,w-p):
        for z in (0,h-p): members.append(cq.Workplane("XY").box(p,d-2*p,p,centered=False).translate((x,p,z)).val())
    assert len(members) == 12
    return members


def build(module_id, label, components):
    solids = frame_members()
    records=[]
    for name,size,origin in components:
        high=tuple(origin[i]+size[i] for i in range(3))
        if any(origin[i] < 0 or high[i] > OUTSIDE[i] for i in range(3)):
            raise ValueError(f"{module_id}/{name} outside frame: {origin}..{high}")
        # Internal payloads must not intersect the 1-inch outer structural zone.
        if any(origin[i] < 1 or high[i] > OUTSIDE[i]-1 for i in range(3)):
            raise ValueError(f"{module_id}/{name} violates 1-inch frame clearance: {origin}..{high}")
        solids.append(box(size,origin))
        records.append({"name":name,"size_in":size,"origin_in":origin,"high_in":high})
    compound=cq.Compound.makeCompound(solids)
    if len(compound.Solids()) != 12+len(components):
        raise ValueError(f"{module_id}: expected {12+len(components)} solids, got {len(compound.Solids())}")
    bb=compound.BoundingBox()
    bbox=tuple(round(v/IN,4) for v in (bb.xlen,bb.ylen,bb.zlen))
    if bbox != OUTSIDE:
        raise ValueError(f"{module_id}: bbox {bbox} != {OUTSIDE}")
    return compound,{"id":module_id,"label":label,"outside_bbox_in":bbox,"frame_member_count":12,"component_count":len(components),"solid_count":len(compound.Solids()),"components":records,"status":"PROTOTYPE_COMPONENT_ENVELOPE"}


def main(out_dir, manifest_path=None):
    out=pathlib.Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    manifest_path = manifest_path or pathlib.Path(__file__).with_name("module-family.json")
    modules = load_modules(manifest_path)
    summary=[]; family=[]
    for index,(module_id,label,components) in enumerate(modules):
        compound,record=build(module_id,label,components)
        exporters.export(compound,str(out/f"{module_id}.step"))
        exporters.export(compound,str(out/f"{module_id}.stl"),tolerance=0.2,angularTolerance=0.2)
        exporters.export(compound,str(out/f"{module_id}.svg"),opt={"showAxes":False,"projectionDir":(1,-1,0.75)})
        (out/f"{module_id}.json").write_text(json.dumps(record,indent=2)+"\n")
        summary.append(record)
        family.extend(s.moved(cq.Location(cq.Vector(index*30*IN,0,0))) for s in compound.Solids())
    exporters.export(cq.Compound.makeCompound(family),str(out/"BN-family-10-modules.step"))
    (out/"family-summary.json").write_text(json.dumps({"modules":summary},indent=2)+"\n")
    print(f"PASS: exported {len(summary)} modules; all bbox/clearance/solid-count gates passed")


if __name__ == "__main__":
    if len(sys.argv) not in (2,3): raise SystemExit(f"usage: {sys.argv[0]} OUTPUT_DIR [MANIFEST]")
    main(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)
