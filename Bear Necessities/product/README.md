# Modular Overland Camp System — Off-The-Shelf Build Package

Everything here targets one goal: **drop-ship from an aluminium extrusion supplier with as close to zero custom fabrication as possible.**

## What's here
| Path | What |
|---|---|
| `bom/catalog.json` | Hand-verified off-the-shelf parts. Real part numbers. |
| `bom/make_bom.py` | Generates the BOM. `--csv` for supplier quotes. |
| `bom/bom-single-module.csv` | BOM for one module frame |
| `drawings/base-frame-ots.step` | The frame, built from catalog extrusion |
| `drawings/C-01-anchor-plate-FLAT.dxf` | The one custom part, laser-ready |
| `custom-parts/` | Custom part specs and the rationale for keeping the list short |

## The headline result: two cut lengths

A 24 × 20 × 18" outside cube in 1" profile needs only **two distinct cut lengths**:

| Cut | Qty | Role |
|---|---|---|
| **18"** | 8 | 4 vertical posts + 4 depth rails |
| **22"** | 4 | 4 width rails |

Posts and depth rails come out the same length (18" height; 20" depth − two 1" profiles = 18"). One saw setup covers 8 of the 12 pieces. **That is the cheapest order you can place with a cut-to-length supplier**, and it falls straight out of the 24/20/18 proportions on the product sheet — worth preserving in any redesign.

Total extrusion: 232" = 19.33 ft per module frame.

## Bill of Materials — one module frame

| Part | Cut | Description | Vendor | Qty |
|---|---|---|---|---|
| 1010-S | 18" | 1"×1" smooth T-slot profile | 80/20 | 8 |
| 1010-S | 22" | 1"×1" smooth T-slot profile | 80/20 | 4 |
| 4132 | — | 10 Series 2-hole gusseted inside corner bracket | 80/20 | 24 |
| 3395 | — | 10 Series 10-32 anchor fastener | 80/20 | 48 |

Part numbers verified 2026-08-20 against 8020.net. **Prices are deliberately blank — get a live quote.**

### Sourcing note
**TNUTZ EX-1010** is stated 100% compatible with 80/20 1010-S, cuts to length, ~48h turnaround. Most 80/20 distributors don't stock — they drop-ship and take margin, so going direct to a cutting distributor is likely both cheaper and faster.

## Custom parts: exactly one, and it's flat

Everything structural is catalog. The only thing with no off-the-shelf equivalent is the **LOCK** step from your product sheet — and that's also the actual IP.

**C-01 Module Anchor Plate** — 4.000 × 1.500 × 0.250", laser cut from 5052 aluminium, 2 mounting holes + 1 pin hole, 0.25" corner radii. Verified: volume 1.4417 in³ against an analytical target of 1.4417 in³.

Design rule applied throughout: **every custom part must be a flat plate cuttable from sheet.** No bends, no machining, no welds. Flat parts quote instantly from a DXF and dozens of shops can make them. The moment a part needs a bend, cost and lead time jump and drop-ship gets harder.

**The pin is not custom** — use an off-the-shelf 1/4" ball-lock quick-release pin.

## The open question that actually blocks drop-ship

**C-02, the vehicle floor bracket, is vehicle-specific** and I have not designed it. Every vehicle has a different tie-down pattern. Three options, all product decisions rather than CAD ones:
1. Ship undrilled, customer drills — simplest, worst experience
2. Vehicle-specific SKUs — best fit, inventory complexity
3. Universal slotted pattern — one SKU, compromised fit

This is the biggest unresolved issue in the drop-ship model. Everything else is orderable today.

## Also unresolved
- Panels, handles, drawer slides, levelling feet are all listed as "off-the-shelf" but **not yet sourced to specific part numbers** (see `_unverified_still_to_source` in `catalog.json`).
- Material thickness and pin diameter on C-01 are assumptions until a load case is defined. What's the worst case — a loaded fridge module in a hard stop?
