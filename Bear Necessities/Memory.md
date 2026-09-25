# Memory.md — Bear Necessities

Durable facts and dated history.

## What it is
A **product / retail brand** side project of Conor's — physical goods, run alongside his primary employment.

## Details not yet captured
Products, customer, stage, sales channels, sourcing, fulfillment, entity/trademark status, financials.

## Log

- 2026-08-03: Project folder set up. Confirmed with Conor that Bear Necessities is a product/retail brand side project. Specifics still to be gathered.

## 2026-08-20 — Likely answer to "what are the products?"
Conor supplied a product sheet for a **Modular Overland Camp System**: a bolt-together 80/20 aluminium extrusion cube system for vehicle-based camping, with six interchangeable modules (cook, storage, fridge, sink, water, gear/utility), **all 24"W × 20"D × 18"H**, sliding into an SUV cargo area and lifting out with built-in handles. Positioning on the sheet: modular, lightweight/strong, quick-release, corrosion resistant, repairable/upgradeable, "made for overlanders, by overlanders."

**Unconfirmed as the Bear Necessities product** — he shared it in this folder and asked for CAD work on it, which is strong circumstantial evidence, but he did not say so outright. Confirm before treating the project's open questions as answered.

Cross-links: CAD work lives in `../Fusion CAD Agent` (first prototype drawing of the shared base frame generated 2026-08-20 by a local offline model). Ties naturally to `../Escalade Work` (his own adventure rig) and `../Outdoor Adventure`.

## 2026-08-20 (late) — Off-the-shelf build package created
Conor redirected the design toward **drop-shipping direct from an aluminium extrusion manufacturer with minimal custom parts**. Built `product/` with a verified BOM, the frame modelled from catalog parts, and the custom-part list deliberately held to one item.

- **Two cut lengths only.** A 24x20x18" outside cube in 1" profile needs 18" x8 (4 posts + 4 depth rails, same length) and 22" x4 (width rails). 232" / 19.33 ft per module. One saw setup covers 8 of 12 pieces — the cheapest order placeable with a cut-to-length supplier, and it falls straight out of the proportions already on the product sheet.
- **Verified part numbers** (8020.net, 2026-08-20): profile **1010-S** (TNUTZ **EX-1010** equivalent, cuts to length, ~48h turnaround), **4132** gusseted corner bracket, **4108** lite alternative, **3395** anchor fastener. **Trap avoided: 4302 is 15 Series, not 10 Series** — would have been a wrong-parts order.
- **Sourcing:** most 80/20 distributors don't stock, they drop-ship and take margin. Going direct to a cutting distributor is likely cheaper and faster.
- **Exactly one custom part designed:** C-01 anchor plate, 4.000 x 1.500 x 0.250", flat, laser-cut, DXF ready. Standing design rule adopted: **every custom part must be a flat plate cuttable from sheet** — no bends, no machining, no welds — because flat parts quote instantly from a DXF and many shops can make them.
- **Prices left deliberately blank** in the catalog. Get a live quote; do not estimate from memory.

**Biggest open issue blocking drop-ship: C-02, the vehicle floor bracket, is vehicle-specific and was not designed.** Every vehicle has a different tie-down pattern. Options are ship-undrilled, per-vehicle SKUs, or a universal slotted pattern — a product decision, not a CAD one. Also still unsourced: panels, handles, drawer slides, levelling feet. And C-01's thickness/pin diameter are assumptions until a load case is defined.

## 2026-08-20 (end of day) — C-02 vehicle queue built, all gated on measurement
Ranked the top 10 overland vehicles for the floor bracket and queued them for the local model to build later (`product/custom-parts/C-02-vehicle-queue.json`, runner at `../Fusion CAD Agent/bridge/run_queue.py`).

**All 10 are deliberately BLOCKED.** Research confirmed factory cargo tie-down spacing is **not published** for these vehicles — the only 4Runner D-ring data findable was for *front frame rail* anchors, not the cargo area. Asking a model to guess hole spacing produces confident wrong numbers and a bracket that does not bolt on. Same principle already adopted for part numbers: **measured or sourced data only, never model-generated.** `MEASUREMENT-WORKSHEET.md` is the unblock path.

**The more important finding: per-vehicle SKUs may be the wrong strategy entirely.** L-track (airline track) is a **published standard with a fixed 1.000" hole pitch**, and factory cargo Sprinters already ship with OEM L-track. Designing C-02 to the L-track standard collapses all 10 SKUs into **one part that never goes obsolete on a model refresh**. Trade-off stated honestly: it pushes an install step onto the customer. That is a product decision, not a CAD one — but it is queued as rank 0 and READY to build now with zero measurements, while the 10 vehicle variants remain blocked.

Ranking (by overland relevance, grounded in Q1 2026 sales where available): 4Runner (33,244 units Q1, +294% YoY), Bronco (31,197 Q1), Wrangler JL, Sprinter, Tacoma, Transit, Gladiator, ProMaster, Lexus GX/Land Cruiser, Subaru Outback/Forester.

**Two of the ten may drop out on inspection** — worth checking before designing anything: the **Subaru** cargo bay may not physically fit a 24"-wide module between the wheel wells (check this FIRST — cheapest possible disqualification), and the **Sprinter** may need no custom bracket at all if factory L-track is present. Also flagged: Tacoma and Gladiator are *bed* mounting, a different problem from an SUV cargo floor, and probably need their own bracket family rather than a variant.

## 2026-08-25 — Reviewed Codex's model-build work; made the project buildable on either machine

Codex built a lot and built it well: ten native Fusion assemblies (F3D/STEP/STL/OBJ
plus 1600×1200 renders, ~113 named components each), a schema-gated job system, an
OTS catalog with provenance rules, deterministic validators, and an honest
human-release gate. The anti-hallucination discipline is the best part — rejected
components stay visible at quantity zero, part numbers are never model-generated,
and no model output can move a job to RELEASED.

**What was wrong, and what got fixed.**

1. **A 27-character sentence killed a 30-cycle run.** The local-model review sweep
   stopped at cycle `design-04`: module BN-M05's `acceptance_check` came back at
   267 characters against a 240 cap. The validator reported only
   "length/type invalid" — no measured length, no bound — so the repair attempt
   resampled and returned a version two characters *longer*, and the run aborted
   after three tries. The ledger has 10 of 300 module reviews and reads INCOMPLETE.
   Fixed: character limits are now stated in the prompt contract, the failure
   message reports the measured length and how much to cut, limits live in one
   `FIELD_LIMITS` table, and the attempt budget is a `--attempts` flag.
   `design-01`–`03` still resume clean, so nothing completed was lost.

2. **A stale green gate.** The committed `native-validation-report.json` read
   PASS with zero failures — genuinely, but from an *earlier* validator carrying
   only 7 checks per module. Codex then added `local_qwen_revision_evidence` and
   `ots_catalog_traceability`, committed the tightened validator, and never
   re-ran it. Re-running today yields FAIL on 20 checks. Fixed: the gate now
   stamps its own SHA-256 and the checks it applied into every report, preflight
   flags any report whose validator hash does not match the current file, and the
   report in the tree was regenerated to the truthful FAIL. **Geometry passes;
   only provenance fails.**

3. **The model roster could not run the pipeline.** `model-profiles.json` listed
   no vision model at any tier, and the 32/48/64GB tiers did not include the
   reviewer model the pipeline requires by name. A mini built to that roster would
   have failed on first run. Added `vision` and `cad-review` roles using the two
   ids actually proven on this study, and `local-ai-manager.py` now derives its
   role list from the profiles file instead of a hard-coded tuple.

4. **No front door, and no portability story.** Added `Bear Necessities/cad/`:
   `runtime.json` (machine-agnostic config, `BN_*` env overrides), `preflight.py`
   (scoped readiness check that names what is missing and how to fix it),
   `build.sh` (validate / revision / native / all), plus `README.md` and
   `STATUS.md`. Verified on this laptop: layout, Python and CadQuery 2.8.0 pass;
   LM Studio and Fusion are simply not running, which preflight reports as such.

5. **Working memory had drifted.** This project's `CLAUDE.md` still asked "what
   are the products?" while a ten-module family sat in the folder, and there was
   no `AGENTS.md` at all — which is *why* Codex's work never landed in project
   memory. `CLAUDE.md` rewritten; `AGENTS.md` is now a symlink to it so the two
   cannot diverge again.

**Architectural note, unresolved:** the ten-module study — Bear Necessities product
data — lives inside `Mac Mini Setup/tools/cad-product-agent/production/`, a
*hardware* project, and this folder holds a lone orphaned copy of
`BN-family-10-modules.step`. Moving ~200 tracked binary artifacts is Conor's call,
so it was not done; `cad/` exists so the location can change without every command
changing with it.

**Real constraint on autonomy:** Fusion's MCP server only exists while the app is
open and signed in. `validate` and `revision` are overnight-safe; `native` is not.

- 2026-08-26 (STL deliverable gate + stale status corrected): Reviewed the eight
  skills in Snyk's "top Claude skills for 3D modeling" roundup for use supervising
  CAD on the mini and installed **none** of them. The only plausible fit, CAD Agent
  (`clawd-maf/cad-agent`), failed review on two counts: it is licensed **PolyForm
  Small Business + Perimeter** — not open source, permitted only under 100 people
  and $1M prior-year revenue, with derivatives carrying the same terms, so it would
  terminate precisely when this brand succeeds — and its advertised
  `analyze_printability` has no overhang check at all and tests "wall thickness"
  against the part's whole bounding box. Moot anyway: nothing here is 3D printed,
  it is 80/20 extrusion plus purchased parts. Wrote `mesh_integrity.py` instead
  (stdlib only, in the ten-module study, wired into `./build.sh validate`): per-solid
  watertightness, outward normals, degenerate facets, body count vs. the job's cut
  list plus components, and envelope vs. the declared frame. Fault-injected against
  five defect classes; all caught. Two findings: the STL exports are **mm while the
  project declares inches** (609.6×508×457.2mm = 24×20×18in exactly — correct but
  previously implicit, now pinned), and an assembly STL must be judged **per solid**
  — the ten files each hold 14 touching bodies whose merged mesh is legitimately
  non-manifold, so a global check falsely failed all ten before being corrected.
  Separately, `cad/STATUS.md` and this file both still claimed the native gate
  failed on provenance; it passes, and both were corrected.

- 2026-08-26 (plan authored — marketing visuals, configurations, OTS BOM): Wrote
  `plans/01-marketing-visuals-and-ots-bom.md`, a nine-phase plan covering Conor's
  four asks: marketing-grade module visuals, ≥10 local-model iterations then one
  Claude confirmation, in-vehicle configuration design, and an off-the-shelf BOM
  rework. Discovery established four things that shape every phase. **The current
  renders are viewport screen captures, not renders** — `build_native_modules.py`
  calls `vp.saveAsImageFileWithOptions` at 1600×1200 with a transparent
  background; per-body appearances (Prism-129 copies with `opaque_albedo` and
  `surface_roughness`) already exist but nothing lights them, so BN-M01 reads as a
  CAD screenshot. **Fusion has no headless mode on macOS**, so a 10-cycle × 10-module
  sweep through Fusion would be ~200 attended renders — the argument for rendering
  outside Fusion off the existing OBJ/MTL exports, with Fusion re-run only when
  geometry changes. **The 16 GB laptop cannot run a capable VLM** (it kernel-panicked
  on the 14B on 2026-08-25; gemma-4-e4b and qwen3.5-9b are over budget; the 3B
  canary silently spawned a second instance and returned PASS-with-blocking-findings),
  so the plan makes a model-free PIL/numpy image gate the primary judge and the 3B
  VLM a checklist second opinion. And **the BOM's status column conflates
  availability with engineering release** — 111 rows, 25 unique catalog IDs, values
  like `ORDERABLE_ENGINEERING_HOLD` — so the OTS audit adds an independent
  `ots_class` axis rather than editing statuses. Arithmetic worth remembering for
  the configuration phase: two modules side by side is 48in and two stacked is 36in,
  both larger than a typical SUV cargo bay, so the product story is likely a chosen
  2–4 module subset per trip, not a full stack. Nothing was built; this is a plan.

- 2026-08-26 (product website built and deployed): Created `website/` as a
  Sites-powered Bear Necessities brand site and published the owner-only first
  release at `https://bear-necessities-overland.cmkennedy218.chatgpt.site`. The
  site uses the ten real 1600×1200 CAD module captures, exposes function filters,
  and includes an interactive trip-kit configurator for four-module high-desert,
  wet-forest, and lakeside combinations. Three U.S. field scenarios use licensed
  Unsplash landscape photography and are deliberately labeled **route concepts**
  so the site does not claim physical testing that has not happened. It also says
  the next step is physical prototyping and real field miles. Generated and wired
  a branded social preview card, production-origin Open Graph/X metadata, and a
  responsive mobile layout. The source is a self-contained Git repository inside
  `website/`; Sites project metadata lives in `website/.openai/hosting.json`.

- 2026-08-26 (executing plan 01 — visuals, configurations, OTS BOM): Built and ran
  most of `plans/01-marketing-visuals-and-ots-bom.md`. Four things in the plan were
  wrong and got corrected by contact with the actual system.

  **Fusion's render workspace IS scriptable.** The plan asserted it was not.
  Probing the live session returned `design.renderManager` with
  `rendering.startLocalRender(filename, camera) -> RenderFuture`, `sceneSettings`
  (ground plane, background, brightness, exposure, focal length, depth of field),
  14 `renderEnvironments`, and resolutions to 3000×2400. That killed the planned
  Blender dependency and its install-approval gate — Fusion ray-traces a 2400×1800
  frame in ~35–65s. Gotchas that each cost a failed attempt, all now recorded in
  `visual/fusion_render.py`: `activeProduct`/`activeViewport` are None with no
  document open; `inCanvasRendering` raises until `activateRenderWorkspace()`;
  `sceneSettings.backgroundType` is read-only and assigning `backgroundEnvironment`
  is what flips it; `groundRoughness` refuses assignment unless
  `isGroundReflections` is true; `groundPosition` takes a `Point3D`, not a float;
  `isGroundDisplayed` alone renders no visible floor — `isGroundFlattened` is what
  puts a shadow-catching plane under the product; and **`camera.viewExtents` is a
  silent no-op while `isFitView` is on**, so framing must be done by moving the eye.
  Also: the light-rig environments (Soft Light, Sharp Highlights, Rim Highlights,
  Grid Light) render their own softbox geometry into frame if used as a visible
  background — Photobooth is the one that is an actual backdrop.

  **Two measurement bugs of my own, both worth remembering.** A matte older than
  the render it describes silently produces plausible-but-wrong coverage and shadow
  numbers — identical coverage across four different framings is what gave it away,
  after four wasted render cycles; `visual_quality.py` now refuses a stale matte.
  And a contact-shadow metric referenced against the far margins reads *brighter*
  than background on a cyclorama, because the backdrop vignettes toward frame edge;
  the reference has to be the floor immediately beside the object.

  **BN-M03 does not fit a 4Runner** — the sharpest finding of the day. The
  top-opening fridge lid needs 14in of headroom; a 4Runner cargo bay is 29.5–31in
  tall and an 18in module leaves 11.5–13in. BN-M09 fails the same way, and BN-M04
  fails in the 6th gen only. More generally a 4Runner takes **exactly two** modules
  and only when both are rotated 90° (20in each = 40in against 43in between the
  wheel wells); a Ford Transit takes five. Two side by side is 48in and two stacked
  is 36in — neither fits any SUV measured.

  **The aluminium extrusion was already maximally off the shelf.** The BOM said
  "cut to 18 inches", which read like a cutting service being bought; the TNUTZ
  EX-1010 page sells any length from 1 to 96in in 1/16in steps straight from a
  dropdown, no cut fee shown. Reclassified `OTS_CUT` → `OTS_STOCK`. Net result of
  the audit: 24 of 25 catalog items buy-as-is, one flat panel, **zero** parts that
  are fabricated and not flat. Added an `ots_class` column independent of `status`,
  which exposed that 20 BOM rows are `ENGINEERING_HOLD` *and* `OTS_STOCK` —
  buyable today, simply not engineering-released. All four deterministic gates
  still pass after the BOM regeneration.

- 2026-08-26 (plan 01 continuation — gates hardened, BN-M03 disposition): Added
  the `./build.sh visuals` front door and matching `preflight.py --for visuals`,
  with laptop-safe Qwen 7B text / Qwen 3B vision roles in `runtime.json`. Hardened
  `visual_quality.py --all` so it requires the exact 40 canonical deliverables
  (hero/front/detail/alpha ×10) and never mistakes old scene sweeps for release
  images. Added a 20-image hash-bound contact sheet, exact solver-driven vehicle
  configuration boards, a website sync command that refuses to publish until the
  10-cycle/100-review ledger + 40-image gate + final confirmation all pass, and
  `cad/completion_audit.py` to prove the whole plan rather than infer completion.
  The audit currently fails honestly because final renders/reviews/confirmation/
  website swap are not done. Fusion's local-render queue wedged after five outputs;
  its MCP began rejecting execution. Restart was not attempted because the safety
  layer could not prove no unsaved document existed; explicit approval is needed.
  Separately resolved BN-M03: MHD13F-DM is envelope-verified at 17.5×11.3×14.5in
  and fits with 1.3in more height clearance than MD14, so jobs now use it and both
  family/job validators pass. Engel direct shows sold out and describes EMS use;
  Zoro's order page contradicts itself (14.5in outside vs 18.25in exterior height),
  so it remains `ORDERABLE_ALTERNATE_VERIFY`, not falsely promoted. Product
  classification: BN-M03 and BN-M09 are van/truck-only; BN-M04 fits 5th-gen
  4Runner/van but not 6th-gen. Website cards now say so.

- 2026-08-26 (competitor reference set): Conor supplied an Instagram photo of a
  Coastal Mountain Vanworks–style fridge module — Dometic CFX on a tilt/slide
  mount, bamboo counter above, drawer below, black frame on wall L-track — and
  asked for a competitor image library to design against. Collected 96 product
  photos across 9 brands into `product/reference/competitors/`, with `README.md`
  (sources + attribution), `make-index.sh`, and a generated `index.html` contact
  sheet. The images are gitignored: third-party copyright, 65MB, reference only,
  never for the BN website — the visual render pipeline exists for that.
  Two findings worth acting on:
  (1) **No competitor reserves headroom above a chest fridge.** CMV, Goose Gear
  (Icebox 1/2 with top drawer), Tembo Tusk (side-pull), Front Runner and Trail
  Kitchens all pull the fridge out of the bay on a slide instead. This is an
  unconsidered route around the BN-M03/BN-M09 van/truck-class classification —
  it would keep the 24×20×18 family frame and the chest fridge, both of which
  CLAUDE.md forbids breaking, and spend drawer-slide hardware plus rear-door
  swing clearance instead of vertical space. Needs the fridge envelope checked
  against slide travel and a real 4Runner tailgate measurement before it counts.
  (2) **Goose Gear's plate system is a third answer to C-02.** One vehicle-
  specific flat plate bolts to that vehicle's factory tie-downs; every module in
  the catalog is then vehicle-agnostic and bolts to the plate. Isolates the
  per-vehicle engineering in a single flat part — consistent with the standing
  flat-plate rule — instead of ten SKUs or a customer-installed L-track.
  Goose Gear module footprints for scale: 19in and 22in wide × 25/28/30/31.5in
  deep. BN's 24W × 20D is wider and much shallower.
  Not captured — JS-rendered sites defeated plain fetching: Decked, Front Runner,
  Vandoit, BOXIO. Front Runner's slide and BOXIO's cube stacking are worth a
  real browser session later.

- 2026-08-26 (marketing image set built from native CAD): Conor picked Trail
  Kitchens and Goose Gear as the visual targets and asked for publishable images
  of all ten modules plus configuration views. Found the existing marketing
  pipeline was the wrong tool: only 6 of 40 canonical files existed and the
  Fusion ray-trace heroes that did exist were unusable — murky, no material
  separation, product barely readable against the gradient. The native Fusion
  exports (`fusion-native/exports/*/`-iso.png, all 10, 1600×1200) were by
  contrast accurate and clean, so those became the source.
  Added `visual/make_module_cards.py`: keys the white studio background to alpha
  by border flood fill (not a global white threshold — that punches holes in the
  extrusion highlights and stove top), trims, and composes brand cards in the
  website palette (cream #f5f1e7 / forest #1f3a29 / accent #d56838). Presentation
  only; it invents no geometry. Ships `--selfcheck`. Output: card 1600×1200,
  square 1200×1200, and alpha cutout per module.
  The alphas unblocked `configurations/render_configurations.py`, which had been
  dead for want of 8 missing alphas — all six solver-validated boards now render.
  Fixed two real defects in it while there: (1) modules that stack, or sit side by
  side, project to the same rectangle in one view, so the last drawn silently hid
  the other — Basecamp showed 3 boxes for 4 modules. `group_labels()` now gives
  the visible box every name sharing its rect ("BN-M02 + BN-M05"). Placements were
  always correct; only the label was lying. (2) long module names collided with
  the wordmark on the square format — titles now shrink to the width actually
  left over.
  Everything copied to `product/marketing/` (11MB, ours, safe to commit and
  publish) with a README and `index.html` contact sheet.
  Deliberately NOT done: the website swap. The command is in the README and it is
  a local file change, but the sync gate (10-cycle/100-review ledger + 40-image
  gate + confirmation) is Conor's to clear. Also did not AI-generate any imagery —
  for a real CAD-designed product a generated photo would show a product that
  differs from what ships.
  Known limitation: identical camera on all ten modules. Fine as a comparison
  grid, repetitive as ten heroes. A second angle needs Fusion, still wedged.

- 2026-08-26 (Fusion wedge root-caused; render pipeline packaged for the mini):
  Two entries above record Fusion's render queue "wedging" and a second camera
  angle being blocked by it. **That is solved.** The cause is not a queue limit
  and not a crash: assigning `sceneSettings.backgroundEnvironment` for the FIRST
  time while a freshly imported ~113-component design is open hangs Fusion
  permanently — process alive at 0% CPU, resident memory flat, every later API
  call blocking until it is killed. Fusion's own crash reporter had recorded
  `CrashCount` 5 with `DWGFile` pointing at BN-M01.f3d, and `adexmtsv` — the
  material-library service the render environments resolve through — crashed
  outright at 14:03. A step-trace written to a file from inside the Fusion script
  is what found it: six consecutive attempts stopped at the identical line, after
  import (11s) and workspace activation (2s) had both succeeded.

  **The fix is to warm the render stack on an empty document before importing
  anything.** Assigning the environment there costs about a second because there
  is nothing to resolve, and makes the same assignment on the heavy design
  instant. Cold-then-heavy wedged 6 of 6; empty-first has never wedged.

  Four more traps found the same way, each now guarded in `visual/render_module.py`:
  **(1)** `Document.close(False)` on a never-saved import raises a modal save
  prompt, and any modal dialog blocks the whole API — never close documents,
  recycle the process instead. **(2)** Killing Fusion orphans its render worker,
  which lives under `Contents/Libraries`, not `Contents/MacOS`; one was found
  reparented to init at 888% CPU, 12 minutes in, producing nothing and starving
  real renders. Every "slow render" of 9+ minutes was one of these. **(3)** The
  MCP port is not stable — after a crash-relaunch Fusion came back on **27180**,
  not the documented 27182, and every tool pinned to the old number reported
  Fusion missing while it ran fine. `bridge/fusion_port.py` now asks the OS and
  confirms with a real handshake; nothing anywhere names a port. A plain HTTP
  liveness check picks 9766, which answers and is not MCP. **(4)** LM Studio and
  Fusion contend for the GPU — both Metal — and with a 3B model resident renders
  fire and never complete. The sweep unloads models before rendering and reloads
  the vision model only for review.

  Hardware conclusion, measured rather than estimated, in
  `visual/HARDWARE-FROM-THIS-JOB.md` and fed back into
  `Fusion CAD Agent/Hardware-Requirements.md`: **this job is core-bound, not
  memory-bound.** The ray tracer runs at 900–975% CPU (9 of 10 cores) while free
  memory sits at 75–81% of 16GB and the whole render path peaks near 3GB. 16
  renders measured 35–240s (mean 104s); the spread is framing, not variance. The
  full 200-render sweep is ~13.5h on 10 cores, ~10h on 14. **More unified memory
  does not fix the GPU contention** — that is scheduling, not capacity. Revised
  buy: M4 Pro, 14-core, 48GB, the RAM still sized for the coding model. The
  display question is now load-bearing: if a headless mini will not drive the
  window server, this sweep cannot run unattended at all.

- 2026-09-02 (revenue paths + Mac mini tax question): Conor asked whether he could
  generate revenue "with the app" and buy the Mac mini "through the business" to
  offset profits — asked for a startup-tax-expert take. Wrote
  `2026-09-02-revenue-paths-and-mac-mini-tax-analysis.md`.
  **The app is a private brochure site** (owner-only Next.js/Sites deploy) for a
  physical product that doesn't exist yet — no cart, no email capture, no payment.
  No entity, no trademark, no customers, $0 revenue ever, solo.
  **Part 1 — revenue:** realistic near-term paths are (1) sell the existing CAD /
  cut list / BOM as a digital build-plans pack (weekend of work, niche money) and
  (2) one-off custom builds once a prototype exists. Both together ≈ a few hundred
  dollars over six months. Everything with upside (pre-orders, full product
  business, audience play) needs capital or an audience he doesn't have. Honest
  headline given: meaningful near-term revenue is unlikely.
  **Part 2 — tax (info for a CPA, not advice):** led with the load-bearing point —
  no revenue = no profit to offset; a deduction is worth ≈ cost × ~30% marginal
  rate (~$850 on the $2,899 machine), not the sticker price; the Mac mini does not
  become free through the business. Then current rules verified against 2026 web
  sources: §179 can't create a loss (useless at $0 revenue); 100% bonus
  depreciation is permanent post-OBBBA for property placed in service after
  1/19/2025; de minimis safe harbor is $2,500/item so the ~$2,900 machine doesn't
  qualify as one item; computers are no longer listed property (TCJA 2018) but
  business-use % and a contemporaneous log still govern; **§183 hobby-loss is the
  real risk** — no-revenue + big equipment deduction + overlapping existing hobby
  + strong W-2 income is the textbook audit pattern, and the 3-of-5-year safe
  harbor is unavailable; §195 startup costs likely defer any benefit because the
  business isn't "active." Closed with ordered questions for his CPA.
  **Straight answer recorded: the tax plan does not hold up on today's facts.**
  If he wants the Mac mini he should buy it because he wants it and revisit tax
  treatment with a CPA if/when Bear Necessities earns money.

- 2026-09-08 (digital build-plans pack, v1 draft): built the revenue path the
  2026-09-02 analysis called the shortest road to a first dollar. Lives in
  `product/build-plans/` — 8 markdown files + `drawings/` (C-01 DXF/PNG/STEP,
  base-frame STEP/STL/ISO-SVG copied from `product/drawings/`). Deliverable
  notice in the vault Outbox (`2026-09-08 Bear Necessities - Build-plans pack
  v1 draft.md`).
  **Scope, and what it deliberately excludes:** the pack documents the *frame*
  (2-cut-length list 8×18 + 4×22 in, BOM with real 80/20/TNUTZ part numbers,
  procedural assembly guide) and *C-01* (dimensioned drawing, CAD-verified
  geometry). It **defers C-02 (the vehicle mount) entirely** — no factory
  tie-down measurements exist for any target vehicle and even the L-track
  version's pin/thickness are unproven assumptions, so shipping vehicle-attach
  guidance would not be responsible. Also excluded: load ratings, fastener
  torque, safety factor, panel drawings (none exist), and any "kit you can
  order complete" framing for the module interiors (every one of the ten has
  open custom parts / unsourced SKUs — the pack says so per module).
  **Discipline held:** no invented dimensions, tolerances, torque or load
  numbers — every figure traces to a CAD gate, a BOM file, or a vendor page,
  and gaps are marked TBD. The `4132`/`3393` frame joint is listed as parts but
  flagged `ENGINEERING_HOLD` (not load-tested); torque points at 80/20's spec
  rather than a guess. Source files disagree `3393` vs `3395` on the bracket
  fastener — pack uses `3393` (current procurement BOM + readiness audit) and
  says to confirm with 80/20.
  **Found a real defect:** the STEP/DXF files in `product/drawings/` carry a
  millimetre `SI_UNIT` tag but inch-valued geometry (pre-date the 2026-08-27
  bncad units fix). A 4.000 in plate reads as 4 mm on a blind import. Pack
  flags it loudly and treats the markdown dimensioned drawing as authoritative;
  a clean re-export is item 1 on the pre-sale checklist
  (`00-status-and-limitations.md` §7).
  **Honest read given to Conor:** sellable *now as a design reference* ($20–80,
  matches the revenue analysis) if the listing keeps the framing honest (no
  "tested/proven/rated"; no-prototype disclosure + C-02 exclusion above the buy
  button). Not sellable as "a build" — nothing is build-verified, the assembly
  guide is written from CAD not a bench build. Building one frame is the single
  step that closes most of the gap; pre-sale checklist is in the pack.
