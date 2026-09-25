# 03 — Custom part C-01: Module Anchor Plate

The one non-catalog part in the frame. A flat plate, laser or waterjet cut from
sheet — no bends, no machining, no welds. Dozens of shops can make it from the
DXF.

> **What C-01 does — and its limit in v1.** C-01 bolts into a T-slot on the
> underside of a module base rail and presents a pin hole. It is the *module
> half* of the lock. The *vehicle half* (part C-02, a floor bracket the pin
> drops into) **is not in this pack and is not designed** — see
> `00-status-and-limitations.md` §3a. So in v1, C-01 is useful as a
> module-to-module or module-to-your-own-anchor interface. Do not treat the
> C-01 pin hole as a vehicle attachment until Bear Necessities publishes C-02
> with a load case.
>
> **Structural numbers are assumptions.** The 0.250 in thickness and the pin
> hole diameter are the project's design assumptions "until a load case is
> defined." They are not tested. Worst case is presumably a fully loaded module
> under hard braking; that number is not established, and it is what sets both
> the plate thickness and the pin size.

---

## Dimensioned drawing (authoritative)

This table is the definition. The CAD files are reference geometry only (see the
units caveat below).

```
                 4.000                          all corners R0.250
       ┌───────────────────────────┐
       │   O           O       o   │   1.500
       └───────────────────────────┘
         │<--2.000-->│       │
       mounting holes         pin hole
       (2x, on centreline)    (1x, on centreline)
```

| Feature | Value | Tolerance | Why it matters |
|---|---|---|---|
| Overall plate | 4.000 × 1.500 × 0.250 in | — | fits along a base rail |
| Material | 5052-H32 aluminium sheet, 0.250 in | sheet tolerance | shear strength (assumption — see note above) |
| Mounting holes | 2 × Ø0.281 in (clearance for 1/4-20), on the plate centreline, **2.000 in apart**, symmetric about plate centre | ±0.010 in on spacing | must land on the 1 in T-slot centres |
| Pin hole | 1 × Ø0.266 in (clearance for a 1/4 in quick-release pin), on the centreline, **1.500 in from plate centre** toward one end | dia +0.005 / −0.000; position ±0.010 in | must accept a 1/4 in pin freely and align with the mating part |
| Corner radius | 0.250 in, all four corners | — | — |

**Free to change:** outline styling beyond the stated radius, lightening
cutouts, edge chamfer, logo etch.

**Quantity:** 2 per module (one each side).

### Geometry verification

The CAD was built in CadQuery and independently re-measured in Autodesk Fusion at
**4.0000 × 1.5000 × 0.2500 in, volume 1.4417 in³** — matching the analytical
target to four decimal places. The hole positions in `drawings/
C-01-anchor-plate-FLAT.dxf` were checked against this table: 4 outline lines,
4 corner arcs, 3 circles at ±1.000 in (mounting) and +1.500 in (pin) on the
centreline. Geometry is correct.

---

## The fasteners and pin (NOT custom — buy these)

| Item | Spec | Notes |
|---|---|---|
| Plate-to-frame bolts | 1/4-20, length to suit your rail + T-nut stack | With slide-in T-nuts sized for the 10 Series slot. Confirm length against your actual assembly. |
| Locking pin | Off-the-shelf **1/4 in** ball-lock or detent quick-release pin | Do not design a pin. Grip length to suit the stack of parts it passes through. |

The project's standing rule: **never design a fastener or a pin that a catalog
part can do.**

---

## How to get it cut

1. Send `drawings/C-01-anchor-plate-FLAT.dxf` to a laser or waterjet shop
   (SendCutSend, OSH Cut, Xometry, or a local shop).
2. **Tell them the units are inches.** The DXF carries a millimetre unit tag that
   does not match its inch geometry (see below) — a shop importing it "as drawn"
   will quote a 4 mm part. Specify: material 5052-H32, thickness 0.250 in,
   overall 4.000 × 1.500 in, quantity as needed.
3. Ask for deburred edges. No finish required for function; anodize if you want
   corrosion resistance.
4. Flat parts quote fast and cheap from a DXF — this is deliberately the only
   custom part in the design.

### CAD file units caveat (important)

`drawings/C-01-anchor-plate-FLAT.dxf` and `.step` were exported before a
unit-handling fix in the project's CAD toolchain. The **geometry is in inch
values but the file declares millimetres**:

- The DXF header sets `$INSUNITS = 4` (mm) and `$MEASUREMENT = 1` (metric), while
  the entities are drawn at inch magnitudes (the plate is "4.0" long).
- The STEP declares `SI_UNIT(.MILLI.,.METRE.)` with points at ±2.0, ±0.75, 0.25
  — inch numbers.

**Fix on import:** set units to inches, or scale by 25.4. The dimensioned table
above is the authoritative source if there is ever any doubt. Producing a clean,
correctly-tagged release DXF is a pre-sale to-do for Bear Necessities
(`00-status-and-limitations.md` §7).

---

## Reference files

- `drawings/C-01-anchor-plate-FLAT.dxf` — the flat profile a shop quotes from.
- `drawings/C-01-anchor-plate-FLAT.png` — visual reference of the flat profile.
- `drawings/C-01-anchor-plate.step` — 3D solid.
