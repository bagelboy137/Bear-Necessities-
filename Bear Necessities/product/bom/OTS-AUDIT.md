# Off-the-shelf audit

Date: 2026-08-26. Source of record: `production/ten-modules/iterations/ots-components.json`
(25 catalog IDs) and the regenerated module BOMs (111 rows).

## Headline

**24 of 25 catalog items (96%) are buy-as-is off the shelf. One is a flat panel cut
from sheet. Nothing requires a fabricated part that is not a flat plate.**

| `ots_class` | Catalog IDs | BOM rows | Meaning |
|---|---|---|---|
| `OTS_STOCK` | 24 | 101 | Buy the catalogue item as-is |
| `OTS_CUT` | 0 | 0 | Vendor cuts to a specified length |
| `OTS_MODIFIED` | 0 | 0 | Needs drilling/tapping/machining after receipt |
| `CUSTOM_FLAT` | 1 | 10 | Fabricated, but a flat plate from sheet |
| `CUSTOM_OTHER` | **0** | **0** | Fabricated and not flat — a design failure. There are none. |

Plus one custom part outside the catalogue: **C-01 anchor plate**, `CUSTOM_FLAT`,
flat and laser-cut. It satisfies the standing rule in `Bear Necessities/CLAUDE.md`
that every custom part must be a flat plate cuttable from sheet.

## Why the BOM now has two columns instead of one

`status` and `ots_class` were tangled together in values like
`ORDERABLE_ENGINEERING_HOLD` and `DEALER_ORDER_ENGINEERING_HOLD`. They answer
different questions and they move independently:

- **`status`** — can I buy this today?
- **`ots_class`** — is this off the shelf at all?

The cross-tab makes the point:

| status | ots_class | rows |
|---|---|---|
| ORDERABLE | OTS_STOCK | 48 |
| ENGINEERING_HOLD | OTS_STOCK | 20 |
| ORDERABLE_ENGINEERING_HOLD | OTS_STOCK | 11 |
| ORDERABLE_CHECK_STOCK | OTS_STOCK | 10 |
| ORDERABLE_CUSTOM_CUT | CUSTOM_FLAT | 10 |
| DEALER_ORDER_ENGINEERING_HOLD | OTS_STOCK | 7 |
| DEALER_ORDER | OTS_STOCK | 3 |
| SOLD_OUT | OTS_STOCK | 1 |
| ORDERABLE_ALTERNATE_VERIFY | OTS_STOCK | 1 |

**Twenty rows are `ENGINEERING_HOLD` and also `OTS_STOCK`** — you can put them in a
cart today; they are simply not engineering-released. That is a procurement fact
and a release fact, and collapsing them into one string hid it. No hold, sold-out
or dealer-order disposition was changed by this audit; the durable rule in
`LOCAL-MODEL-ITERATION-LEARNINGS.md` says preserve them, and they are preserved.

## The aluminium extrusion — the specific question asked

The frame is `TNUTZ-EX1010-18` ×8 and `TNUTZ-EX1010-22` ×4. The BOM described
these as "cut to 18 inches" / "cut to 22 inches", which reads like a custom cutting
service being bought.

**It is not.** The TNUTZ EX-1010 product page sells the profile from a length
dropdown covering **1 to 96 inches, with fractional selections from 0" to 15/16"** —
so any length in 1/16-inch steps is a catalogue selection. The listed price range
is **$0.22 – $25.46**, spanning that 1-to-96-inch range. No separate cut fee or
minimum is shown on the product page.

Source: [TNUTZ EX-1010](https://www.tnutz.com/product/ex-1010/), fetched 2026-08-26.

So the answer to "can the extrusion be more off the shelf?" is **it already is
maximally off the shelf**: 18 in and 22 in are ordered straight from the dropdown,
no saw, no drop, no machining, no cut fee. Reclassified `OTS_CUT` → `OTS_STOCK`.

This also means the "two cut lengths only" rule is cheaper than it looked. Its
value is not saw setups — there is no saw. It is **two line items instead of
twelve**, and it stays worth preserving for that reason.

Not yet verified, and worth one phone call before any real order:

- Whether a cut fee appears at checkout that the product page does not show.
- Whether volume pricing changes the 18-in/22-in unit price.
- Whether 80/20's own 1010-S (the primary part, with TNUTZ as the drop-ship
  alternate) offers the same any-length ordering, or only mill lengths.

## Items that are off the shelf but not currently buyable

These are `OTS_STOCK` — the problem is availability, not fabrication.

| Item | Status | What closes it |
|---|---|---|
| `ENGEL-MD14` 15 qt fridge | SOLD_OUT | `ENGEL-MHD13-ALT` (14 qt) is the envelope-verified prototype alternate. It fits, but remains a procurement/intended-use hold. See below. |
| `RELIANCE-AQUATAINER-7G` / `-4G` | DEALER_ORDER | Find a stocking retailer or accept dealer lead time |
| `RUBBERMAID-FG350700WHT` tote | DEALER_ORDER | Commercial-channel item; a consumer-channel equivalent would remove the hold |
| `TNUTZ-HAN015AL` handle | ORDERABLE_CHECK_STOCK | Confirm stock or qualify a second source |
| `ACCURIDE-3832-C16` slides | DEALER_ORDER_ENGINEERING_HOLD | Both a channel and a release problem |
| `SHURFLO-4008` pump | DEALER_ORDER_ENGINEERING_HOLD | Both a channel and a release problem |

## The one fabricated item

`TAP-HYPACT-PANEL` — black UV-stabilised polymer sheet, cut to size for skins,
trays and dividers. One "cut-panel lot" per module, so 10 BOM rows.

It is `CUSTOM_FLAT` and therefore allowed, but it is the only thing in the product
that cannot be ordered from a catalogue page, and it is gated on released DXF panel
drawings that do not exist yet. Those drawings are the single largest remaining
piece of non-CAD product work.

## BN-M03 alternate disposition

The MHD13F-DM dimensions published by Engel are **17.5 × 11.3 × 14.5 in**. It
keeps the MD14 footprint and is 1.3 in shorter, so it fits the existing BN-M03
component origin and 22 × 18 × 16 in clear envelope with more clearance than the
original. `module-family.json` now carries the alternate's real envelope.

It is **not promoted to buy-ready**. Checked 2026-08-26:

- Engel's own page says sold out and positions the unit for EMS medication and
  saline transport, not consumer food storage.
- Zoro carries an order page, but lists both 14.5 in “outside height” and a
  contradictory 18.25 in “exterior height.”
- Engel confirms the existing TSLPLATE + TSL17 transit-lock combination fits
  both MD14F and MHD13F-DM.

The honest disposition is therefore `ORDERABLE_ALTERNATE_VERIFY`: **envelope
verified; availability, dimensional discrepancy, intended food use and warranty
still held.** This closes the model-fit task without laundering uncertain
procurement evidence into an ORDERABLE claim.

Sources checked 2026-08-26: Engel MHD13 manufacturer page, Engel transit slide
lock and lock-plate pages, and Zoro G7673053 order page (URLs are retained in
`ots-components.json`).

## Deployment consequence

The configuration work done the same day found that **BN-M03 does not fit any
4Runner measured** — its top-opening lid needs 14 in of headroom and an SUV bay
leaves 11.5–13 in. See `configurations/CONFIGURATIONS.md`.

The shorter alternate does not solve lid swing. BN-M03 still needs 14 in above the
closed module and does not fit either measured 4Runner cargo bay. It is therefore
classified as a **van/truck-class module** for this release rather than forcing a
third extrusion length or replacing a chest fridge with a front-opening product.
