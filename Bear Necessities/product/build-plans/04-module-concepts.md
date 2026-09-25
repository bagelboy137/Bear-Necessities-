# 04 — The ten module concepts

Ten ways to use the frame. **This file is design reference, not build
instructions.** Every module is a concept CAD assembly with an off-the-shelf
appliance chosen for it and an internal layout modelled for clearance — but every
one also has unresolved custom parts, missing SKUs, or engineering holds. Treat
these as "here's the idea and the direction," not "here's a kit you can order
complete."

Sources: the ten native Fusion concept assemblies, `module-family.json`
(envelopes, clearance, open items), and the per-module prototype BOMs. Where the
CAD provenance file and the prototype BOM disagree on the appliance pick, both
are noted.

---

## What every module shares

Beyond the frame (`01-frame-cut-list-and-bom.md`), each module concept also
carries these off-the-shelf items. Quantities are prototype allowances — trim to
your actual design.

| Item | Vendor / part | Qty per module | Status |
|---|---|---|---|
| Carry handle | TNUTZ `HAN-015-AL` (black aluminium, with 10 Series mounting hardware) | 2 | Orderable — **check stock**; handle is **not authorized for a loaded lift until tested** |
| Panel gasket | TNUTZ `GAS-010-A` (for ~3/16 in panels) | ~20 ft (allowance) | Orderable; final length from panel drawings that don't exist yet |
| Anti-skid tread | TNUTZ `BUM-010-TS` (rubber tread strip) | ~8 ft (allowance) | Orderable; verify vehicle-floor compatibility |
| Side/back panels | TAP Plastics King Hy-Pact, cut to size | 1 "cut-panel lot" | **Order only from released DXF panel drawings — those don't exist yet** |

Full details and URLs in `05-off-the-shelf-parts-catalog.md`.

---

## Deployment classes (from the project's fit work)

- **BN-M03** and **BN-M09** are **van / truck class**. Their top openings need
  ~14 in of clearance above the 18 in frame; neither measured 4Runner cargo bay
  has it.
- **BN-M04** fits a 5th-gen 4Runner but not the shorter 6th-gen.
- The other seven are SUV-class in principle, subject to your own wheel-well and
  tailgate measurement.

---

## BN-M01 — Cook Station

- **Purpose:** two-burner outdoor cooking and cookware storage.
- **Built around:** Jetboil Genesis Basecamp two-burner stove, UPC
  `0858941006274`. Status: orderable (verify current stock; propane bottle
  carried separately, outside the enclosed module). Packed envelope ~10.75 ×
  10.75 × 6.25 in.
- **Concept interior:** packed stove low in the bay on a pull-out tray; a
  deployable worktop shelf above it (~21.5 × 17.5 in).
- **Still open:** the flat worktop panel — material and food-contact finish not
  selected; hot-use clearances and windscreen deployment not tested; propane
  handling procedure. Drawer slides for the stove tray are a "verify load"
  placeholder.

## BN-M02 — Dry Pantry

- **Purpose:** sealed storage for packaged dry food and cookware.
- **Built around:** no validated container. The prototype BOM suggests Rubbermaid
  Commercial `FG350700WHT` 2-gal food-tote boxes (~18 × 12 × 3.5 in) ×3, stacked
  vertically — dealer-order, and matching lids must be sourced separately. The
  CAD provenance file records a Milwaukee PACKOUT box as the original pick,
  **rejected** for exceeding the 22 in clear width by 0.1 in.
- **Still open:** source a sealed container no larger than 21.5 W × 16 D × 11 H
  in with a lid that opens inside the frame; food-contact suitability applies to
  packaged food only. Three drawer-slide pairs are "verify load" placeholders.

## BN-M03 — Fridge / Freezer  *(van / truck class)*

- **Purpose:** 12 V top-opening cold storage, rides low and restrained.
- **Built around:** Engel `MD-14F` 15 qt — **manufacturer sold out**, carried at
  quantity zero. Prototype alternate: Engel `MHD13F-DM` (~17.5 × 11.3 × 14.5 in),
  status **orderable-alternate-verify** — envelope fits with margin, but Engel
  direct is sold out, a retailer's dimensional listing is self-contradictory, and
  the manufacturer positions this unit for EMS medication transport, not consumer
  food. Confirm intended use and warranty before buying.
- **Still open:** fridge availability; compressor ventilation path; 12 V fused
  wiring and strain relief; Engel `TSLPLATE` + `TSL17` transit slide-lock
  packaging. **Does not fit a 4Runner** — 14 in lid headroom.

## BN-M04 — Sink / Wash  *(5th-gen 4Runner / van; top access)*

- **Purpose:** cold-water hand and dish washing with contained grey water.
- **Built around:** Dometic VA8000-series square sink (prototype BOM cites
  `VA8005` / `9102303252`; the CAD provenance file marks the exact SKU as not
  released). Demand pump: Pentair Shurflo `4008-101-E65` 12 V 3 GPM — dealer
  order, engineering hold. Grey water: Reliance `9405-03R` 4-gal Aqua-Tainer,
  permanently labelled, never returned to potable use.
- **Still open:** exact sink SKU and its cutout drawing; food-safe faucet / hose
  / pump SKUs; leak tray and drain routing; a full plumbing design and leak test.

## BN-M05 — Fresh Water

- **Purpose:** seven gallons of removable potable water.
- **Built around:** Reliance `9410-03R` 7-gal Aqua-Tainer (~11.5 × 11.25 ×
  15.75 in). Status: dealer order (manufacturer no longer sells direct).
- **Still open:** **positive tank restraint for the ~58 lb full-water mass** —
  not designed, and it needs a dynamic load case; food-safe pump / hose SKU;
  drainable spill tray. The tie-down straps in the BOM (NRS, 500 lb published
  WLL) are marked "module anchor / load path still requires engineering."

## BN-M06 — Recovery / Utility

- **Purpose:** weather-sealed recovery gear and tools, fast access.
- **Built around:** Pelican `1450-000-110` Protector case with foam (prototype
  BOM, orderable). The CAD provenance file's original pick was a Milwaukee
  PACKOUT, **rejected** for width.
- **Still open:** a payload-specific divider plan; the purchased case does not
  validate the module frame or its retention. One drawer-slide pair is a "verify
  load" placeholder.

## BN-M07 — Power Hub

- **Purpose:** portable AC / DC / USB power and cable storage.
- **Built around:** EcoFlow RIVER 3 Plus, 286 Wh portable power station
  (~9.2 × 9.1 × 5.75 in packed). Status: orderable. Keep manufacturer-required
  ventilation and all ports accessible.
- **Still open:** a ventilation / open-area calculation; cable pass-through
  grommets; charging access while restrained; electrical labelling. **The module
  is not a certified electrical enclosure** — do not treat it as one.

## BN-M08 — Hot Water / Shower

- **Purpose:** portable propane water heating and a shower.
- **Built around:** Joolca HOTTAP V2 Essentials kit (~17.7 × 11.4 × 6.6 in,
  transported horizontally). Status: orderable.
- **Safety (from the source design):** **never operate the heater inside the
  vehicle or the module.** It is transported in the module and deployed and run
  **outdoors only.** Propane bottle carried separately.
- **Still open:** the US kit SKU; hose restraint and a drying / ventilation path
  for wet storage.

## BN-M09 — Field Office / Camera  *(van / truck class)*

- **Purpose:** protected electronics / camera transport that unfolds into a
  trail-side work surface.
- **Built around:** Pelican `1485 Air` case with configurable foam (~19.2 × 13.0
  × 6.9 in). Status: orderable.
- **Still open:** a flat retention plate to hold the case; work-surface hinge /
  latch SKUs; laptop thermal management if operated in the module. Worktop
  headroom means it **does not fit a 4Runner**.

## BN-M10 — Camp Furniture / Soft Goods

- **Purpose:** chairs, table, awning accessories, soft gear — one-piece access.
- **Built around:** customer-selected soft gear. The prototype BOM fits Helinox
  Chair One ×2 and Table One ×1 in the concept bay; the CAD provenance file
  leaves the product set to the customer.
- **Still open:** the target chair / table set; cargo-net SKU; compression-strap
  SKU; a payload and centre-of-gravity target. Four tie-down straps in the BOM
  carry the standard "load path requires engineering" note.

---

## The honest read on the modules

None of the ten is a finished, orderable build. The frame under all of them is
the resolved asset; the interiors range from "one orderable appliance plus a
custom worktop and a hot-use test" (M01, M07, M08) to "the main component isn't
even sourced yet" (M02, M04, M06, M10). If you buy this pack, you are buying the
frame plus a well-researched starting point for whichever interior you want to
build — not a kit.
