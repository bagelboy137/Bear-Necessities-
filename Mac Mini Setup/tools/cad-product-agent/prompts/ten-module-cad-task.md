Write one complete standalone Python 3.12 script using CadQuery 2.8 that exports
ten prototype component-envelope models as STEP and STL plus one combined STEP.
Return only a single Python code block. The script receives its output directory
from `sys.argv[1]`, creates it, and never accesses the network.

All dimensions below are inches. CadQuery dimensions must be millimetres using
`IN = 25.4`. Each module uses the identical 24W x 20D x 18H outer frame. Model
the frame as twelve separate 1 x 1 rectangular extrusion-envelope solids:

```
def frame_members():
    W,D,H,P = 24*IN,20*IN,18*IN,1*IN
    members=[]
    for x in (0,W-P):
        for y in (0,D-P): members.append(cq.Workplane("XY").box(P,P,H,centered=False).translate((x,y,0)))
    for y in (0,D-P):
        for z in (0,H-P): members.append(cq.Workplane("XY").box(W-2*P,P,P,centered=False).translate((P,y,z)))
    for x in (0,W-P):
        for z in (0,H-P): members.append(cq.Workplane("XY").box(P,D-2*P,P,centered=False).translate((x,P,z)))
    return members
```

Add each internal component as a simple box envelope using these records
`(id, label, [(name, size_xyz_inches, origin_xyz_inches), ...])`:

```
BN-M01 Cook Station: packed_stove (10.75,10.75,6.25) at (1,1,1); worktop (21.5,17.5,.25) at (1.25,1.25,9)
BN-M02 Dry Pantry: pantry_box (21.5,16,11) at (1.25,2,1)
BN-M03 Fridge Freezer: fridge (17.5,11.3,15.8) at (3.25,4.35,1)
BN-M04 Sink Wash: sink (16.5,14.6,6) at (3.75,2.7,10.5); grey_tank (11.5,11.25,8) at (6.25,4.4,1)
BN-M05 Fresh Water: water_tank (11.5,11.25,15.75) at (1,4.4,1); pump_bay (7.5,11.25,6) at (14,4.4,1)
BN-M06 Recovery Utility: tool_box (21.5,16,6.5) at (1.25,2,1); shelf (21.5,17.5,.25) at (1.25,1.25,9)
BN-M07 Power Hub: power_station (9.21,9.13,5.75) at (1,1,1); cable_case (10,9.13,5.75) at (12,1,1); shelf (21.5,17.5,.25) at (1.25,1.25,9)
BN-M08 Hot Water Shower: heater (17.7,11.4,6.6) at (3.15,4.3,1); hose_bay (17.7,11.4,5) at (3.15,4.3,9)
BN-M09 Field Office Camera: equipment_case (21.96,13.97,8.98) at (1.02,3,1); worktop (21.5,17.5,.25) at (1.25,1.25,12)
BN-M10 Camp Furniture Soft Goods: soft_gear_bay (21.5,17.5,15.5) at (1.25,1.25,1)
```

For every module:
- Keep the 12 frame members as separate solids in a `cq.Compound` along with
  component boxes. Do not fuse them.
- Verify each component box is wholly inside 0..24, 0..20, 0..18 inches before
  export; raise with the module ID and component name if not.
- Verify exactly 12 frame members and total solids = 12 + component count.
- Export `<ID>.step` and `<ID>.stl`; use a filesystem-safe ID.
- Write `<ID>.json` containing ID, label, outside bbox, frame member count,
  component count, and component records.

Create a combined family STEP by translating each complete module 30 inches
along X in ID order. Write `family-summary.json` with all ten verification
records. Add comments that geometry is a packaging prototype, not structural
analysis or manufacturer CAD.
