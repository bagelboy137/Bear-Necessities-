# 05 — Off-the-shelf parts catalog

Every catalog component referenced across the frame and the ten module concepts.
Compiled from the project's audited prototype BOM (`all-modules-prototype-bom.csv`,
`OTS-AUDIT.md`). **All prices are quote-on-request** — the project deliberately
keeps them null and so does this pack.

**Status legend:**

| Status | Meaning |
|---|---|
| Orderable | An order page was visible on the research date (2026-08-20 / -26). Not a stock guarantee. |
| Check stock | Orderable but limited stock was shown — confirm or qualify a second source. |
| Dealer order | No direct consumer sale; go through a dealer / distributor. |
| Alternate — verify | A substitute for a sold-out part; envelope fits but availability / use / warranty unconfirmed. |
| Sold out | Manufacturer page showed no stock. Carried at quantity zero. |
| Engineering hold | Buyable today, **not engineering-released** — the joint / load / retention it's part of is untested. |
| Custom cut | Catalog material, cut to size from a drawing (drawing may not exist yet). |

The "engineering hold" flag is independent of buyability. Twenty BOM rows are
*both* orderable and engineering-hold.

---

## Structural — the frame

| Part | Vendor | Description | Used in | Status | Source |
|---|---|---|---|---|---|
| `1010-S` / `EX-1010` | 80/20 (alt: TNUTZ) | 1 × 1 in 10 Series smooth T-slot profile, cut to 18 in | Frame ×8/frame | Orderable | tnutz.com/product/ex-1010/ · 8020.net |
| `1010-S` / `EX-1010` | 80/20 (alt: TNUTZ) | same, cut to 22 in | Frame ×4/frame | Orderable | tnutz.com/product/ex-1010/ |
| `4132` | 80/20 | 10 Series 2-hole gusseted inside corner bracket | Frame joint ×24/frame | **Engineering hold** | 8020.net/4132.html |
| `3393` | 80/20 | 1/4-20 × 0.500 in bolt + slide-in economy T-nut, for `4132` (×2 per bracket) | Frame joint ×48/frame | **Engineering hold** | 8020.net/3393.html |
| `3395` / `AF-010` | 80/20 / TNUTZ | 10 Series 10-32 anchor fastener — *concealed-joint alternative* | Not used (qty 0) | Not evaluated | tnutz.com/product/af-010/ |

## Frame trim — shared across modules

| Part | Vendor | Description | Per module | Status | Source |
|---|---|---|---|---|---|
| `HAN-015-AL` | TNUTZ | Black aluminium carry handle with 10 Series mounting hardware | 2 | Check stock; **not rated for a loaded lift** | tnutz.com/product/han-015-al/ |
| `GAS-010-A` | TNUTZ | 10 Series panel gasket for ~3/16 in panels | ~20 ft (allowance) | Orderable | tnutz.com/product/gas-010-a/ |
| `BUM-010-TS` | TNUTZ | 10 Series anti-skid rubber tread strip | ~8 ft (allowance) | Orderable | tnutz.com/product/bum-010-ts/ |
| King Hy-Pact panel | TAP Plastics | Black UV-stabilised polymer sheet, cut to size for skins / trays / dividers | 1 "cut-panel lot" | **Custom cut — needs a released DXF that doesn't exist yet** | tapplastics.com …/hypact_vhmw_polyethylene/527 |

## Drawer / access hardware

| Part | Vendor | Description | Used in | Status | Source |
|---|---|---|---|---|---|
| `3832-C16` | Accuride | 16 in full-extension side-mount drawer-slide pair | M01, M02 (×3), M03, M06, M09 | Dealer order + **engineering hold** — verify exact suffix, load, side clearance, lock, finish | accuride.com …/3832ec-easy-close-light-duty-slide |
| `E3-57-25` | Southco | Small black knob-style vise-action compression latch (grip 6.4–9.5 mm) | M01, M02, M07, M08, M09 | Orderable + engineering hold — confirm cam geometry and panel stack | shop.southco.com/e3-57-25 |
| `1 in HD Tie-Down Strap` | NRS | UV-protected 1 in polypropylene cam strap, published 500 lb WLL | M03, M04, M05, M06, M08, M10 | Orderable + **engineering hold — module anchor / load path still requires engineering** | nrs.com/nrs-1-hd-tie-down-straps/p4yc |

## Module appliances / primary components

| Part | Vendor | Description | Module | Status | Source |
|---|---|---|---|---|---|
| Genesis Basecamp, UPC `0858941006274` | Jetboil | Two-burner stove (stove + regulator + bag; propane separate) | M01 | Orderable | jetboil.johnsonoutdoors.com …/genesis-basecamp-stove |
| `FG350700WHT` | Rubbermaid Commercial | 2-gal 18 × 12 × 3.5 in polyethylene food-tote box (lids separate) | M02 (×3) | Dealer order | rubbermaidcommercial.com …?sku=FG350700WHT |
| `MD-14F` | Engel | 15 qt top-opening 12 V fridge / freezer | M03 | **Sold out** (qty 0) | engelcoolers.com/products/md14-ems-ambulance-fridge |
| `MHD13F-DM` (Zoro `G7673053`) | Engel | 14 qt top-opening 12/24 V fridge / freezer / warmer — alternate | M03 | **Alternate — verify** dimensions, food-use, warranty, availability | zoro.com …/i/G7673053/ |
| `VA8005` / `9102303252` | Dometic | Square stainless sink with glass cover + AC 540 siphon (faucet separate) | M04 | Orderable (exact SKU not released per CAD file) | dometic.com …?v=9102303252 |
| `4008-101-E65` | Pentair Shurflo | 12 V 3 GPM Revolution fresh-water demand pump | M04, M05 | Dealer order + **engineering hold** (needs hose, fuse, wiring, connectors from a schematic that doesn't exist) | pentair.com …/sku/4008-101-e65.html |
| `9405-03R` | Reliance Outdoors | 4-gal Aqua-Tainer — **grey water only, permanently labelled** | M04 | Dealer order | relianceoutdoors.com …/aqua-tainer-4g-15l |
| `9410-03R` | Reliance Outdoors | 7-gal Aqua-Tainer, potable (~58 lb full) | M05 | Dealer order | relianceoutdoors.com …/aqua-tainer-4g-15l |
| `1450-000-110` | Pelican | 1450 Protector case with foam | M06 | Orderable | pelican.com/us/en/product/cases/1450 |
| RIVER 3 Plus | EcoFlow | 286 Wh portable power station | M07 | Orderable | us.ecoflow.com …/river-3-plus-portable-power-station |
| HOTTAP V2 Essentials | Joolca | Portable propane hot-water / shower kit — **operate outdoors only** | M08 | Orderable | joolca.com/products/hottap-v2?country=US |
| `1485 Air` | Pelican | 1485 Air case with configurable foam | M09 | Orderable | pelican.com/us/en/product/cases/air/1485 |
| Chair One | Helinox | Packable camp chair (14 × 4.5 × 4.5 in case) | M10 (×2) | Orderable | helinox.com/products/chair-one |
| Table One | Helinox | Packable camp table (16.5 × 4 × 4 in case) | M10 | Orderable | helinox.com/products/table-one |

## Custom (not catalog)

| Part | Description | Process | Status |
|---|---|---|---|
| C-01 anchor plate | 4.000 × 1.500 × 0.250 in flat plate, 5052-H32 aluminium | Laser / waterjet from `drawings/C-01-anchor-plate-FLAT.dxf` | Geometry verified; **thickness and pin size are load-case assumptions** — see `03-anchor-plate-C-01.md` |
| C-02 vehicle floor bracket | The vehicle-side anchor | Laser / waterjet flat plate | **Not designed. Not in this pack.** See `00-status-and-limitations.md` §3a |
| Side / back panels | Enclosure skins | Cut-to-size sheet from a released DXF | **DXFs do not exist.** Thickness is module-specific and unengineered |
| Module-specific small parts | Worktop (M01), sink cutout (M04), retention plate (M09), dividers, etc. | Varies | Per-module open items — see `04-module-concepts.md` |

---

## Availability holds worth knowing before you quote

| Item | Issue |
|---|---|
| Engel `MD-14F` fridge | Sold out at the manufacturer. The `MHD13F-DM` alternate fits the envelope but Engel direct is also sold out, a retailer's listed dimensions contradict each other, and it's positioned for EMS use, not food. |
| Reliance Aqua-Tainers (4G, 7G) | Manufacturer no longer sells direct — dealer locator only. |
| Rubbermaid `FG350700WHT` tote | Commercial channel; a consumer-channel equivalent would remove the hold. |
| TNUTZ `HAN-015-AL` handle | Only a handful shown in stock on the research date. |
| Accuride `3832-C16` slides + Shurflo `4008` pump | Both a channel problem (dealer order) and a release problem (engineering hold). |

---

## The one honest headline from the audit

**24 of 25 catalog items are buy-as-is off the shelf; the 25th is a flat panel
cut from sheet. Nothing in the design requires a fabricated part that is not a
flat plate.** That is a real result and it's the reason the drop-ship idea is
plausible at all. What it does *not* mean is that the modules are
buildable-complete today — the engineering holds, the missing panel drawings, and
the undesigned vehicle mount are all still in front of you.
