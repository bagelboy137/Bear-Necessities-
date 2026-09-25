# Bear Necessities — Modular Overland Frame · Build Plans (v1 draft)

A downloadable build pack for the Bear Necessities frame: a bolt-together
24 × 20 × 18 in aluminium-extrusion module that slides into a vehicle cargo bay.
This pack lets you order the parts and assemble the frame from catalog components.

**Draft status:** this is a v1 draft assembled from the project's CAD and BOM on
2026-09-08. It has **not** been through a customer, an editor, or a build. Read
`00-status-and-limitations.md` before doing anything else — it is not boilerplate.

---

## What's in this pack

| File | What it gives you |
|---|---|
| `00-status-and-limitations.md` | **Read first.** What is verified, what is not, what is deliberately left out, and how to think about buying this. |
| `01-frame-cut-list-and-bom.md` | The two-cut-length cut list and the frame bill of materials, with real vendor part numbers and where to buy. Prices are blank on purpose — you get a live quote. |
| `02-frame-assembly-guide.md` | Step-by-step assembly of the bare frame from the parts in file 01. |
| `03-anchor-plate-C-01.md` | The one custom part — a flat laser-cut plate — with its dimensioned drawing and how to get it cut. |
| `04-module-concepts.md` | The ten module concepts (cook, fridge, water, power, …): what each is built around, the off-the-shelf appliance it uses, and what each one still needs before it's a finished build. Reference material, not step-by-step instructions. |
| `05-off-the-shelf-parts-catalog.md` | Every catalog component referenced across the ten modules, with vendor, part number, source URL and buy-status. |
| `06-configurations.md` | Six trip-kit combinations of modules and which vehicles each fits. |
| `drawings/` | `C-01-anchor-plate-FLAT.dxf` + `.png` + `.step`, and `base-frame-ots.step` / `.stl` / `-ISO.svg` for the frame. |

## What this pack is NOT

- **Not a vehicle-mounting guide.** The bracket that anchors a module to the
  vehicle floor (part "C-02") is **not in this pack**. It is not designed yet —
  see `00-status-and-limitations.md` §3. Do not attach a loaded module to a
  moving vehicle using anything in here.
- **Not load-rated.** No part in this pack carries a tested load rating, safety
  factor, or fastener torque spec. The frame joint design is a concept, not a
  tested joint.
- **Not a finished product.** No prototype of this frame has ever been built.
  You would be the first.
- **Not panel/skin drawings.** The side and back panels are called out as
  "cut-to-size from sheet," but the actual panel dimensions and hole patterns
  are not drawn yet.

## Who this is for

Someone who builds with 80/20-style aluminium extrusion, wants a proven-on-paper
starting geometry and parts list for a vehicle camp module, and is comfortable
doing their own engineering for anything load-bearing — especially the vehicle
attachment. If you want a turnkey, tested, bolt-in product, this isn't that yet.

## Units

All dimensions are in **inches** unless stated otherwise. Note the units caveat
on the CAD files in `03-anchor-plate-C-01.md` and `00-status-and-limitations.md`
§5 — the STEP/DXF files carry a millimetre unit tag that does not match their
inch geometry, and must be imported with units forced to inches.

## Licence / terms (placeholder — decide before selling)

To be set by Bear Necessities before this pack is sold. Suggested shape: personal
single-build licence, no resale or redistribution of the files, no warranty, and
an explicit "you are responsible for engineering the vehicle attachment and any
load-bearing joint" acknowledgement at purchase. See
`00-status-and-limitations.md` §7.
