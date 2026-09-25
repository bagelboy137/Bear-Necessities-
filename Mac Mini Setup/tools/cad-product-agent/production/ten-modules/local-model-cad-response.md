```python
import sys
import os
import json
import cadquery as cq

IN = 25.4

def frame_members():
    W, D, H, P = 24 * IN, 20 * IN, 18 * IN, 1 * IN
    members = []
    for x in (0, W - P):
        for y in (0, D - P):
            members.append(cq.Workplane("XY").box(P, P, H, centered=False).translate((x, y, 0)))
    for y in (0, D - P):
        for z in (0, H - P):
            members.append(cq.Workplane("XY").box(W - 2 * P, P, P, centered=False).translate((P, y, z)))
    for x in (0, W - P):
        for z in (0, H - P):
            members.append(cq.Workplane("XY").box(P, D - 2 * P, P, centered=False).translate((x, P, z)))
    return members

def create_module(id, label, components):
    W, D, H = 24 * IN, 20 * IN, 18 * IN
    frame = cq.Compound.makeCompound(frame_members())
    
    component_solids = []
    for name, size_xyz_inches, origin_xyz_inches in components:
        size_xyz_mm = [dim * IN for dim in size_xyz_inches]
        origin_xyz_mm = [dim * IN for dim in origin_xyz_inches]
        
        if any(x < 0 or x > W for x in (origin_xyz_mm[0], origin_xyz_mm[0] + size_xyz_mm[0])) or \
           any(y < 0 or y > D for y in (origin_xyz_mm[1], origin_xyz_mm[1] + size_xyz_mm[1])) or \
           any(z < 0 or z > H for z in (origin_xyz_mm[2], origin_xyz_mm[2] + size_xyz_mm[2])):
            raise ValueError(f"Component {name} in module {id} is out of bounds.")
        
        component = cq.Workplane("XY").box(*size_xyz_mm, centered=False).translate(origin_xyz_mm)
        component_solids.append(component)
    
    total_solids = cq.Compound.makeCompound([frame] + component_solids)
    
    if len(total_solids.Solids()) != 12 + len(component_solids):
        raise ValueError(f"Module {id} does not have the correct number of solids.")
    
    return total_solids, component_solids

def export_module(output_dir, id, label, components):
    module_id = id.replace('-', '_').replace(' ', '_')
    total_solids, component_solids = create_module(id, label, components)
    
    step_file = os.path.join(output_dir, f"{module_id}.step")
    stl_file = os.path.join(output_dir, f"{module_id}.stl")
    
    total_solids.exportSTEP(step_file)
    total_solids.exportSTL(stl_file)
    
    module_info = {
        "id": id,
        "label": label,
        "outside_bbox": [24 * IN, 20 * IN, 18 * IN],
        "frame_member_count": 12,
        "component_count": len(component_solids),
        "components": components
    }
    
    json_file = os.path.join(output_dir, f"{module_id}.json")
    with open(json_file, 'w') as f:
        json.dump(module_info, f, indent=4)

def create_family(output_dir):
    modules = [
        ("BN-M01", "Cook Station", [("packed_stove", (10.75, 10.75, 6.25), (1, 1, 1)), ("worktop", (21.5, 17.5, .25), (1.25, 1.25, 9))]),
        ("BN-M02", "Dry Pantry", [("pantry_box", (22.1, 16.2, 11.1), (.95, 1.9, 1))]),
        ("BN-M03", "Fridge Freezer", [("fridge", (17.5, 11.3, 15.8), (3.25, 4.35, 1))]),
        ("BN-M04", "Sink Wash", [("sink", (16.5, 14.6, 6), (3.75, 2.7, 10.5)), ("grey_tank", (11.5, 11.25, 8), (6.25, 4.4, 1))]),
        ("BN-M05", "Fresh Water", [("water_tank", (11.5, 11.25, 15.75), (1, 4.4, 1)), ("pump_bay", (7.5, 11.25, 6), (14, 4.4, 1))]),
        ("BN-M06", "Recovery Utility", [("tool_box", (22.1, 16.2, 6.5), (.95, 1.9, 1)), ("shelf", (21.5, 17.5, .25), (1.25, 1.25, 9))]),
        ("BN-M07", "Power Hub", [("power_station", (9.21, 9.13, 5.75), (1, 1, 1)), ("cable_case", (10, 9.13, 5.75), (12, 1, 1)), ("shelf", (21.5, 17.5, .25), (1.25, 1.25, 9))]),
        ("BN-M08", "Hot Water Shower", [("heater", (17.7, 11.4, 6.6), (3.15, 4.3, 1)), ("hose_bay", (17.7, 11.4, 5), (3.15, 4.3, 9))]),
        ("BN-M09", "Field Office Camera", [("equipment_case", (21.96, 13.97, 8.98), (1.02, 3, 1)), ("worktop", (21.5, 17.5, .25), (1.25, 1.25, 12))]),
        ("BN-M10", "Camp Furniture Soft Goods", [("soft_gear_bay", (21.5, 17.5, 15.5), (1.25, 1.25, 1))])
    ]
    
    family_solids = []
    for i, (id, label, components) in enumerate(modules):
        module_id = id.replace('-', '_').replace(' ', '_')
        total_solids, _ = create_module(id, label, components)
        family_solids.append(total_solids.translate((i * 30 * IN, 0, 0)))
    
    family_compound = cq.Compound.makeCompound(family_solids)
    family_step_file = os.path.join(output_dir, "family.step")
    family_compound.exportSTEP(family_step_file)
    
    family_summary = {
        "modules": [module[0] for module in modules]
    }
    
    json_file = os.path.join(output_dir, "family-summary.json")
    with open(json_file, 'w') as f:
        json.dump(family_summary, f, indent=4)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <output_directory>")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    os.makedirs(output_dir, exist_ok=True)
    
    for id, label, components in [
        ("BN-M01", "Cook Station", [("packed_stove", (10.75, 10.75, 6.25), (1, 1, 1)), ("worktop", (21.5, 17.5, .25), (1.25, 1.25, 9))]),
        ("BN-M02", "Dry Pantry", [("pantry_box", (22.1, 16.2, 11.1), (.95, 1.9, 1))]),
        ("BN-M03", "Fridge Freezer", [("fridge", (17.5, 11.3, 15.8), (3.25, 4.35, 1))]),
        ("BN-M04", "Sink Wash", [("sink", (16.5, 14.6, 6), (3.75, 2.7, 10.5)), ("grey_tank", (11.5, 11.25, 8), (6.25, 4.4, 1))]),
        ("BN-M05", "Fresh Water", [("water_tank", (11.5, 11.25, 15.75), (1, 4.4, 1)), ("pump_bay", (7.5, 11.25, 6), (14, 4.4, 1))]),
        ("BN-M06", "Recovery Utility", [("tool_box", (22.1, 16.2, 6.5), (.95, 1.9, 1)), ("shelf", (21.5, 17.5, .25), (1.25, 1.25, 9))]),
        ("BN-M07", "Power Hub", [("power_station", (9.21, 9.13, 5.75), (1, 1, 1)), ("cable_case", (10, 9.13, 5.75), (12, 1, 1)), ("shelf", (21.5, 17.5, .25), (1.25, 1.25, 9))]),
        ("BN-M08", "Hot Water Shower", [("heater", (17.7, 11.4, 6.6), (3.15, 4.3, 1)), ("hose_bay", (17.7, 11.4, 5), (3.15, 4.3, 9))]),
        ("BN-M09", "Field Office Camera", [("equipment_case", (21.96, 13.97, 8.98), (1.02, 3, 1)), ("worktop", (21.5, 17.5, .25), (1.25, 1.25, 12))]),
        ("BN-M10", "Camp Furniture Soft Goods", [("soft_gear_bay", (21.5, 17.5, 15.5), (1.25, 1.25, 1))])
    ]:
        export_module(output_dir, id, label, components)
    
    create_family(output_dir)
```