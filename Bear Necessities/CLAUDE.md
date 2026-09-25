# Claude.md — Bear Necessities

Working memory for **Bear Necessities**, Conor's product / retail brand side project.

## What it is
A **Modular Overland Camp System** — bolt-together 1" aluminium extrusion cubes
for vehicle camping. Every module is **24"W × 20"D × 18"H**, slides into an SUV
cargo bay, and lifts out by built-in handles. Ten modules are now designed
(cook, pantry, fridge, sink, water, gear, power, shower/heat, field office,
furniture/soft goods).

Still technically unconfirmed that this *is* the Bear Necessities product — Conor
has never said so outright — but a full product build now lives in this folder,
so treat it as the working assumption and ask if it ever matters.

Stage: **pre-launch, concept CAD complete, nothing ordered.**

## If Fusion looks wedged, it is solved
Assigning the render environment while a heavy design is open hangs Fusion
permanently. Warm the render stack on an empty document first — that is what
`visual/render_module.py` does. Never close a Fusion document (the save prompt is
modal and blocks the API), never assume the MCP port (it moves; discovery lives
in `Fusion CAD Agent/bridge/fusion_port.py`), never leave a killed Fusion's
render worker behind (it spins at ~900% CPU under `Contents/Libraries`), and
never let LM Studio hold the GPU while Fusion renders. Full account in
`Memory.md`, 2026-08-26.

## Build it

```bash
cd "Bear Necessities/cad" && python3 preflight.py
```

`cad/` is the front door and works the same here and on the Mac mini — see
`cad/README.md` for the commands and `cad/STATUS.md` for what currently passes
and fails. Machine-specific values live in `cad/runtime.json` or `BN_*` env vars;
nothing hard-codes a home directory.

**New 2026-08-27 — `./build.sh parts` builds parts from a written spec.** A JSON
part spec goes in, a local model writes CadQuery, and a validated
millimetre-correct STEP/STL comes out, headless. Six parts are specified
(including C-01 and the C-02-U universal bracket) and five of six build on a 7B
in well under a minute each. Framework and full notes:
`../Fusion CAD Agent/bncad/README.md`.

**Read the units section there before sending any STEP to a supplier.** CadQuery
stamps millimetres into every STEP it writes, so an inch-authored part describes
millimetres — a validated C-01 imported into Fusion 25.4× too small before this
was found and fixed.

## Where things live
- `product/build-plans/` — the sellable digital build-plans pack (v1 draft, 2026-09-08):
  README, `00-status-and-limitations.md` (read first), frame cut list + BOM,
  frame assembly guide, C-01 spec, module concepts, OTS catalog, configurations,
  `drawings/`. Built from the CAD/BOM; C-02 deferred; nothing build-verified.
- `product/` — BOM, catalog part numbers, custom parts, the drop-ship thesis
- `product/marketing/` — the publishable image set: 10 module cards (1600×1200),
  10 squares (1200×1200), 10 alpha cutouts, and 6 solver-validated configuration
  boards (2400×1600). Composed from the native Fusion exports, no invented
  geometry. `open index.html` to review; see its README to regenerate.
- `product/reference/competitors/` — 96 competitor product photos across 9 brands
  (CMV, Goose Gear, Trail Kitchens, Adventure Wagon, Alu-Cab, Kanz, Roam, Tembo
  Tusk, Drifta) for design reference. Images are gitignored — third-party
  copyright, never for the website. `open index.html` to review; see its README.
- `cad/` — build front door: preflight, runner, runtime config, status
- `website/` — the Sites-powered product/field-story website and its deployment config
- `../Mac Mini Setup/tools/cad-product-agent/production/ten-modules/` — the ten-module
  study, jobs, exports, and gates (product data sitting in a hardware project;
  see `cad/README.md`). Two subfolders added 2026-08-26:
  - `visual/` — marketing render pipeline: brief, deterministic image gate,
    Fusion ray-trace driver, local iteration loop
  - `configurations/` — in-vehicle packing solver, vehicle envelopes, the six
    named configurations
- `../Fusion CAD Agent/` — CadQuery and Fusion MCP bridges, specs, venvs

## Current state
- Ten native Fusion assemblies exist: F3D/STEP/STL/OBJ plus 1600×1200 renders,
  ~113 named components each. Geometry gates pass.
- **All four deterministic gates pass** (2026-08-26, `./build.sh validate`),
  including the native release gate — the provenance blocker recorded through
  2026-08-25 is closed. A fourth gate, `mesh_integrity.py`, was added 2026-08-26
  and checks the exported STL deliverables suppliers actually receive.
- Two cut lengths only per frame: 18" ×8 and 22" ×4. One saw setup covers 8 of 12
  pieces. Preserve this in any redesign — it is the cheapest orderable cut list.
- Exactly one custom part designed (C-01 anchor plate, flat, laser-cut). Standing
  rule: **every custom part must be a flat plate cuttable from sheet.**
- A private product website is deployed at
  `https://bear-necessities-overland.cmkennedy218.chatgpt.site`. It presents all
  ten CAD modules, function filters, an interactive four-module trip-kit builder,
  and honest concept routes for Utah, Oregon, and New York. Source lives in
  `website/`; field scenarios are explicitly labeled as concepts pending the
  physical prototype and real field miles.

## Product blocker now
**C-02, the vehicle floor bracket.** Every vehicle has a different tie-down
pattern and factory cargo spacing is unpublished, so all ten vehicle variants are
deliberately blocked pending real measurements. The L-track option collapses them
into one part that never goes obsolete, at the cost of a customer install step.
That is a product decision, not a CAD one — it is still Conor's to make.

**Deployment classification decided 2026-08-26.** BN-M03 and BN-M09 are
van/truck-class modules because their top openings need 14in above an 18in frame;
neither measured 4Runner has it. BN-M04 fits the 5th gen but not the shorter 6th
gen. Do not break the family frame or replace the chest fridge to force SUV fit.
The MHD13F-DM prototype alternate is envelope-verified at 17.5×11.3×14.5in, but
still has procurement/intended-food-use holds. See `OTS-AUDIT.md` and
`configurations/CONFIGURATIONS.md`.

**Unconsidered route around that classification (2026-08-26, competitor scan).**
No competitor reserves headroom above a chest fridge — CMV, Goose Gear, Tembo
Tusk, Front Runner and Trail Kitchens all pull the fridge *out* of the bay on a
slide or tilt tray. That would keep both the family frame and the chest fridge
intact and spend drawer-slide hardware plus rear-door swing clearance instead of
vertical space. Unverified: needs the fridge envelope checked against slide
travel and a real 4Runner tailgate measurement. See
`product/reference/competitors/README.md`.

## Open questions
- Confirm this is the Bear Necessities product.
- Solo, or with a partner?
- Registered as a business? Is the name trademarked?
- Goal — side income, or something to grow?

## Revenue + tax (2026-09-02)
`2026-09-02-revenue-paths-and-mac-mini-tax-analysis.md` — Conor asked about
monetizing "the app" (the private website) and buying the Mac mini through the
business. Findings: no software product to monetize on its own; realistic
near-term revenue is a digital build-plans pack + one-off custom builds, ≈ a few
hundred dollars over six months. **The tax plan does not hold up** — no revenue =
no profit to offset, a deduction is worth ≈ cost × marginal rate not the sticker
price, and §183 hobby-loss is a live risk. Doc closes with questions for a CPA;
it is not tax advice.

## Note on the name
"Bear Necessities" is a well-worn pun and likely in use by other businesses. A
**trademark search** is worth doing before spending on packaging and signage.

## Next steps
0. **Build-plans pack pre-sale checklist** (`product/build-plans/00-status-and-limitations.md` §7):
   re-export C-01 / base-frame CAD with correct inch unit tags; write the
   licence / no-warranty / buyer-responsibility terms; get one live BOM quote;
   confirm `3393` vs `3395` with 80/20; **build one frame**; trademark search.
1. Execute `plans/01-marketing-visuals-and-ots-bom.md` — marketing-grade visuals,
   local iteration loop, in-vehicle configurations, off-the-shelf BOM rework.
2. Swap the website's placeholder CAD captures for `product/marketing/modules/`
   (the render set now exists — the copy command is in that folder's README).
   Local file swap only; publishing stays behind the existing sync gate.
3. Decide C-02: per-vehicle SKUs vs. the universal L-track part vs. Goose Gear's
   third shape — one vehicle-specific flat plate that every module bolts to,
   isolating the per-vehicle engineering in a single sheet-cuttable part.
   (Also gates a real v2 of the build-plans pack — v1 defers C-02 entirely.)
4. Send `SUPPLIER-RFQ-DRAFT.md` to get real cut tolerance and drop-ship terms.
5. Trademark search on the name before any spend on packaging or signage.
