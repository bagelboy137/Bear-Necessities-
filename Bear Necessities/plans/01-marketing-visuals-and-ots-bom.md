# Plan 01 — Marketing-grade visuals, deployed configurations, off-the-shelf BOM

Created 2026-08-26. Scope comes from Conor's request, in his order:

1. Top-tier visuals for the ten modules.
2. Iterate ≥10 times on local models (save Claude usage), then **1** Claude pass to
   confirm marketing-ready.
3. Design how the modules fit together in different in-vehicle configurations.
4. Audit every component — including the aluminium extrusion — for off-the-shelf
   availability; rework the BOM to show OTS vs. not.
5. Absorb any model changes that fall out of 3 and 4, then re-render and re-confirm
   the visuals are still top tier.

Each phase is self-contained: it names the files to read, what to copy from, how to
prove it worked, and what not to do. Execute phases consecutively; a fresh context
per phase is fine.

---

## Handoff — 2026-08-26 16:20

**Two agents are working this plan in one tree, and Fusion cannot take both.**
A peer session has rendered a full ten-module set in its own view vocabulary
(`card`, `square`, `alpha`) and is doing Phase 7 work on BN-M03. I stopped driving
Fusion at 16:18 rather than keep competing for it — two drivers on one crash-prone
app is very likely *why* it keeps crashing. Fusion is free now.

**The two render sets fail on complementary axes, which is the useful finding:**

| | mine (`hero`) | peer's (`card`/`square`) |
|---|---|---|
| specular fraction | **0.023 pass** | 0.0000 fail, all 20 |
| background | **gradient pass** | flat fail |
| subject coverage | 0.10 fail | **0.33 / 0.44 pass** |
| edge richness | 62 | **95–111** |
| tonal p99 | **254** | 226, pinned to that value on every image |
| gates passed | 8 of 10 | fails 3 |

Their framing and detail are clearly better; my lighting is the only one producing
a specular highlight or a real backdrop. **The combination passes everything.**
The p99 sitting at exactly 225.8 on all twenty of theirs is worth a look — that is
a ceiling, not a lighting choice.

**What I changed so the pipeline survives the crashes** (`render_module.py`,
`fusion_render.py`):

- **The crash was probably ours.** `_open_module` cached every imported document
  and never closed one, so a ten-module batch held ten designs open at once, each
  with its own copied appearances. `adexmtsv` — the material-library service those
  appearances live in — crashed mid-batch. It now closes all documents before
  opening the next, at the cost of one re-import per module.
- **The MCP port is not stable.** After a crash-relaunch Fusion came back on
  **27180**, not the documented 27182, and every tool pointed at 27182 reported
  "Is Fusion running?" while it was running fine. That cost two hours.
  `discover_mcp_url()` now asks the OS which port the Fusion process is listening
  on and verifies each candidate with a real MCP `initialize` handshake — a plain
  HTTP check is not enough, it picks up port 9766, which answers but is not MCP.
- **One render per bridge call, with retry and relaunch.** A crash now costs one
  module instead of the batch. `render-progress.json` records finished outputs so
  a resume skips them.
- Progress output is flushed, so an unattended run's log is not silent for an hour.

**Not done, and why:** Phase 3's ten-cycle sweep, Phase 4, and the rest of Phase 8
all need sustained Fusion time that this laptop has not been able to give. The
plan already called this out — `native` is not an unattended path. On the evidence
of today it is a Mac mini job.

## Execution status — 2026-08-26

| Phase | State | Evidence |
|---|---|---|
| 0 Discovery | **done** (one finding corrected — see below) | this document |
| 1 Define "marketing-ready" | **done** | `visual/VISUAL-MARKETING-BRIEF.md`, `visual/visual_quality.py`, baseline **0/20 pass** |
| 2 Render path | **done** — Fusion's own ray tracer | `visual/fusion_render.py`, `visual/render_module.py` |
| 3 Ten local cycles | **running** — launched 2026-08-26 13:43, ~35 min/cycle, resumable | `visual/run_visual_cycles.py`, ledger at `visual/visual-iteration-ledger.json` |
| 4 Claude confirmation | blocked on 3 | — |
| 5 Configurations | **done** | `configurations/` — solver, envelopes, 6 validated configurations |
| 6 Off-the-shelf BOM | **done** | `product/bom/OTS-AUDIT.md`, `ots_class` on all 111 rows |
| 7 Absorb changes | blocked on 3/4 | — |
| 8 Final verification | **partial** — everything not gated on Phase 3 verified | see below |

Phase 8 checks that could run today, all passing 2026-08-26:

```
./build.sh validate            4/4 deterministic gates PASS
config_solver.py --validate-all   6 configurations, 0 with no fitting vehicle
visual_quality.py --demo       PASS      run_visual_cycles.py --demo   PASS
config_solver.py --demo        PASS
grep CUSTOM_OTHER in the BOM   none      grep invented Fusion API      none
grep oversized models in visual/  none
```

**BN-M01 hero currently clears 8 of the 10 image gates.** Reproduced twice:
p99 254, specular 0.0227, metal modulation 44.0, coverage 0.295, gradient
background, resolution 2400x1800. The two open failures are `subject_centering`
(0.115 against 0.080) and `contact_shadow_ratio` (1.239 against 0.900 - the frame
is mostly open, so little of the band under it is actually shadowed). Both are
what the Phase 3 loop is tuning.

**Corrections to this plan, made while executing it:**

1. Phase 0 asserted Fusion's render workspace is not scriptable. **It is** — see the
   resolved block below. Rung B (Blender) was withdrawn, along with its install
   approval gate.
2. Phase 1 claimed `panel_modulation` and `subject_coverage` passed at baseline.
   They pass on the iso views and **fail on all ten front views** (coverage 0.820,
   panel modulation 8.7–15.0). Corrected in the brief.
3. Phase 5 predicted "most vehicles take 2–4 modules". Measured: a 4Runner takes
   **exactly 2**, and only rotated 90°. A Transit takes 5.
4. Phase 6 predicted the extrusion was a cut-to-length service worth re-costing.
   It is not — TNUTZ sells any length 1–96 in from the product dropdown, so the
   extrusion was already maximally off the shelf and was reclassified `OTS_STOCK`.

**Findings that create new work, none of which this plan anticipated:**

- **BN-M03 (fridge) does not fit any 4Runner.** Its top-opening lid needs 14 in of
  headroom; an SUV bay leaves 11.5–13 in. BN-M09 fails the same way. This is a
  product decision, and it now sits next to the C-02 decision.
- The BOM's `status` column was conflating availability with engineering release.
  Twenty rows are `ENGINEERING_HOLD` **and** `OTS_STOCK` — buyable today, not
  released. That was invisible before the split.

**Two operational hazards found while running the render pipeline, both now
guarded in code:**

- Fusion's MCP server stops answering for the duration of a render. Two
  overlapping drivers destroy each other's output; `render_module.py` now takes a
  lock.
- **Killing a driver does not cancel the renders.** Fusion finishes them minutes
  later and overwrites the files, which produced several measurements of images
  that had been silently replaced. After killing a driver, wait for the render
  directory to go quiet before trusting it.

**Two measurement bugs of my own, both fixed:**

- A matte older than the render it describes silently produces plausible but wrong
  coverage and shadow numbers. Four render cycles were spent before identical
  coverage across four different framings gave it away. `visual_quality.py` now
  refuses a stale matte and says so.
- `edge_density` (edge pixels over subject *area*) falls as the subject grows in
  frame, so it cannot be a fixed floor across framings. Replaced with
  `edge_richness` (over sqrt of area). Its floor is deliberately **not** taken
  from the legacy captures: their edge richness is inflated by Fusion's CAD
  edge-line overlay, which a photographic render legitimately lacks.

---

## Phase 0 — Documentation discovery (ALWAYS FIRST) — **already done, findings below**

This phase was executed on 2026-08-26. Re-run only the ⚠️ items, which are the
ones that were *not* verified by running them.

### Verified facts (with sources)

**Build front door.** `Bear Necessities/cad/build.sh` resolves everything from
`cad/runtime.json` + `BN_*` env vars; no hard-coded paths. Stages: `test`,
`validate`, `revision`, `native`, `all`. `cad/preflight.py --for <stage>` says what
would fail. Source: `cad/README.md`, `cad/build.sh`.

**Current gate status.** All four deterministic gates PASS as of 2026-08-26
(`validate_family.py`, `validate_jobs.py`, `mesh_integrity.py`,
`validate_native_family.py`). Source: `cad/STATUS.md`.

**How the current images are made.** `production/ten-modules/fusion_native/build_native_modules.py`
lines ~815–860: two explicit cameras (`iso`, `front`), then
`adsk.core.SaveImageFileOptions.create(...)` → `width/height = 1600/1200`,
`isAntiAliased = True`, `isBackgroundTransparent = True`, then
`vp.saveAsImageFileWithOptions(...)`, with a fallback to
`vp.saveAsImageFile(filename, 1600, 1200)`.
**This is a viewport screen capture, not a render.** That is the whole gap.

**Appearances already exist.** Same file, lines ~115–138: a `PALETTE` dict is
copied off the Fusion generic appearance `Prism-129` out of material library
`BA5EE55E-9982-449B-9D66-9F036540E140`, setting `opaque_albedo` and
`surface_roughness` (0.28 for aluminium, 0.52 otherwise). So the models carry
per-body colour and roughness already; the capture path simply does not light it.

**Exports available per module** (`production/ten-modules/fusion-native/exports/<ID>/`):
`.f3d`, `.step`, `.stl`, `.obj` + `.mtl`, `-iso.png`, `-front.png`, `-build.json`.
The OBJ/MTL is described in the header comment as the "material-capable
visualization mesh" — it is the natural input to an external renderer.

**Baseline quality, inspected directly** (`BN-M01-iso.png`): correct geometry, all
twelve members, legible stove/knobs/drawer — but flat shading, one light, no
shadows, no ground contact, no material differentiation between aluminium and
charcoal beyond value, transparent background flattening to white. Reads as a CAD
screenshot. It passes `VISUAL-QA.md` because that gate asks "is the equipment
recognisable", which is a *completion* bar, not a *marketing* bar.

**Local model roster actually loaded** (`curl http://127.0.0.1:1234/v1/models`,
2026-08-26): `prism-ml/bonsai-27b`, `qwen2.5-vl-3b-instruct`,
`qwen2.5-coder-7b-instruct`, `qwen/qwen2.5-coder-14b`, `google/gemma-4-e4b`,
`meta-llama-3.1-8b-instruct`, `qwen/qwen3.5-9b`, `text-embedding-nomic-embed-text-v1.5`.
`runtime.json` asks for reviewer `qwen/qwen2.5-coder-14b`, vision `google/gemma-4-e4b`.

**Hard local-model constraint.** `product/cad/evidence/LM-STUDIO-SAFE-PROFILES.md`:
this 16 GB M1 Pro laptop **kernel-panicked twice** on 2026-08-25 running the 14B MLX
worker (`completeMemory() prepare count underflow`, `IOGPUMemory.cpp`). The laptop
profile is 7B / 6144 ctx / 1800-token cap / 30 s cool-down / 30 % free-memory floor.
Gemma-4-e4b (8.95 GiB) and Qwen3.5-9B (7.79 GiB) are **rejected for the laptop**.
The `qwen2.5-vl-3b` canary loaded at 2.88 GiB, completed one image, then LM Studio
*silently spawned a second parallel instance* and free memory fell 74 % → 32 %. Its
JSON was also self-contradictory: `PASS` with populated blocking findings.

**Existing iteration harness to copy, not reinvent:**
- `production/ten-modules/iterations/run_revision_cycles.py` — resumable text
  critique loop; one validated file per cycle, reused on the next run.
- `production/ten-modules/iterations/validate_revision_ledger.py` — ledger gate.
- `production/ten-modules/fusion_native/review_native_family.py` — the local
  vision-model reviewer. **Copy its resource guard** (`memory_free_percent()` via
  `memory_pressure -Q`, `wait_for_resources(max_load, min_free_percent)`) and its
  `extract_json()` fence-stripping. Lines ~1–60.
- `production/ten-modules/iterations/validate_visual_completion.py` — existing
  image gate.

**Fusion.** Installed at `~/Applications/Autodesk Fusion.app`. Per
`Fusion CAD Agent/reference/fusion-api-notes.md`: **no headless mode on macOS** —
Fusion must be running with a GUI session; `ui.messageBox` blocks forever
unattended; Fusion's embedded CPython cannot import pip packages. The same file
carries a table of API methods local models confidently invent — read it before
writing any Fusion script.

**BOM reality** (`product/bom/modules/all-modules-prototype-bom.csv`, 111 rows,
**25 unique catalog IDs**):

| status | rows |
|---|---|
| ORDERABLE | 48 |
| ENGINEERING_HOLD | 20 |
| ORDERABLE_ENGINEERING_HOLD | 11 |
| ORDERABLE_CHECK_STOCK | 10 |
| ORDERABLE_CUSTOM_CUT | 10 |
| DEALER_ORDER_ENGINEERING_HOLD | 7 |
| DEALER_ORDER | 3 |
| SOLD_OUT | 1 |
| ORDERABLE_ALTERNATE_VERIFY | 1 |

Note the status axis **conflates availability with engineering release** — that is
exactly what Phase 6 has to separate.

**Catalog rules** (`iterations/ots-components.json` → `rules`): models may cite
catalog IDs but may **not** invent vendors, SKUs, dimensions, ratings, availability,
certifications, prices or URLs. ORDERABLE means an order page was visible on the
research date, not a stock guarantee.

### ⚠️ Still to verify by running it (do this at the top of Phase 2)

**RESOLVED 2026-08-26 by probing the live Fusion session — the original entry in
this slot was wrong and is corrected below.**

I had written that Fusion's ray-tracing Render workspace is not part of the
scripted API surface. **It is.** Probing the running session returned a complete
render API:

| Object | Members that matter |
|---|---|
| `design.renderManager` | `activateRenderWorkspace()`, `isRenderWorkspaceActive`, `rendering`, `sceneSettings`, `renderEnvironments`, `inCanvasRendering` |
| `.rendering` | `startLocalRender(filename, camera) -> RenderFuture`, `renderQuality`, `resolution`, `resolutionWidth/Height`, `aspectRatio`, `isBackgroundTransparent` |
| `.sceneSettings` | `backgroundEnvironment`, `backgroundSolidColor`, `isGroundDisplayed`, `isGroundReflections`, `isGroundFlattened`, `groundOffset`, `groundRoughness`, `groundPosition`, `brightness`, `lightAngle`, `cameraExposure`, `cameraFocalLength`, `cameraType`, `isDepthOfFieldEnabled`, `depthOfFieldBlur`, `centerOfFocus` |
| `RenderFuture` | `renderState`, `progress`, `filename`, `imageWidth`, `imageHeight` |
| `renderEnvironments` (14) | Sharp Highlights, Rim Highlights, Cool Light, Warm Light, Soft Light, Grid Light, Crossroads, Dry lake bed, Field, Photobooth, Plaza, Skylight, Snow Field, Custom |
| `RenderResolutions` | up to `Print3000x2400RenderResolution`, plus `CustomRenderResolution` |
| `LocalRenderStates` | `Queued`, `Processing`, `Finished`, `Failed` |

So Fusion can produce HDRI-lit, ray-traced, ground-shadowed renders at 3000 × 2400,
scripted, with no new dependency. **Rung B (Blender) is not needed and the install
checkpoint is withdrawn.**

Gotchas found by running it, all of which cost a failed attempt:

- `app.activeViewport` and `activeProduct` are `None` when no document is open —
  probe with a document, or every attribute reads as absent.
- `inCanvasRendering` raises `Render Workspace must be active` until
  `activateRenderWorkspace()` has been called.
- `sceneSettings.backgroundType` is **read-only**. Assigning
  `backgroundEnvironment` is what flips it to the environment type — which is also
  what produces a gradient backdrop instead of a flat fill.
- `groundRoughness` refuses assignment unless `isGroundReflections` is true.
- `renderComplete` is a `RenderEvent` object, not a bool — it is an event to
  subscribe to, and it is not JSON-serialisable.
- `renderEnvironments` has no `.current`; use `itemByName(...)`.
- `startLocalRender` is asynchronous and queued, one at a time. It outlives any
  single MCP call, so **fire the render in one call and poll for the output file
  from the host** rather than blocking inside Fusion.

Still open:

- ⚠️ Whether the Prism metal appearances (as opposed to the generic `Prism-129`
  currently copied) give a better aluminium under ray tracing. Test during Phase 3.
- ⚠️ Wall-clock per render at quality 75 and 2400 × 1800, which sets whether a
  10-cycle sweep is an overnight job or a multi-day one.

### Allowed APIs / tools list

| Use | Allowed | Source |
|---|---|---|
| Build/validate | `cad/build.sh {test,validate,revision,native,all}`, `cad/preflight.py --for <stage> [--json]` | `cad/README.md` |
| Fusion geometry | `adsk.fusion.Design.cast(app.activeProduct)`, `rootComp.xYConstructionPlane`, `extrudeFeatures.createInput(...)` → `.add(input)`, `setDistanceExtent(False, ValueInput)`, `design.exportManager` | `fusion-api-notes.md` |
| Fusion appearance | `app.materialLibraries.itemById(...)`, `lib.appearances.itemById(...)`, `design.appearances.addByCopy(...)`, `appearanceProperties.itemById("opaque_albedo"/"surface_roughness")` | `build_native_modules.py:115–138` |
| Fusion capture | `adsk.core.SaveImageFileOptions.create(path)` + `vp.saveAsImageFileWithOptions(opts)`; fallback `vp.saveAsImageFile(path, w, h)` | `build_native_modules.py:838–847` |
| Fusion render | `design.renderManager` → `activateRenderWorkspace()`, `sceneSettings`, `renderEnvironments.itemByName(...)`, `rendering.startLocalRender(path, camera)`, poll `RenderFuture.renderState` against `adsk.fusion.LocalRenderStates` | probed live 2026-08-26 |
| Local models | LM Studio OpenAI-compatible endpoint at `http://127.0.0.1:1234/v1` | `runtime.json` |
| Units | API is **cm and radians** always; 1 inch = `2.54` | `fusion-api-notes.md` |

### Anti-patterns (apply to every phase)

- Do not invent Fusion API members. Check the offline table of confirmed
  hallucinations in `fusion-api-notes.md` first.
- Do not invent a vendor, SKU, dimension, rating, price, availability or URL.
  Cite a catalog ID from `ots-components.json` or mark it UNVERIFIED.
- Do not break the frame invariants: 24 × 20 × 18 in outer, 22 × 18 × 16 in clear,
  exactly twelve members, **8 × 18 in + 4 × 22 in — two cut lengths only**.
- Do not load `google/gemma-4-e4b` or `qwen/qwen3.5-9b` on the laptop.
- Do not accept a self-contradictory model verdict (PASS with blocking findings) —
  that is a failed attempt, not a pass.
- Do not overwrite the last-good render set until the replacement passes the gate.
- Do not describe local-model output as engineering release, measurement, or safety
  evidence.
- Do not regenerate an evidence report without stamping the validator SHA-256 —
  the existing gates already do this; a report whose hash does not match the
  current validator is flagged by preflight. See `cad/STATUS.md`.

---

## Phase 1 — Define "marketing-ready" as a checkable thing

Nothing here needs a model. This phase exists because "top tier" is currently
unfalsifiable, and every later phase gates on it.

### Implement

1. Write `production/ten-modules/visual/VISUAL-MARKETING-BRIEF.md`. Copy the
   structure of the existing `VISUAL-DESIGN-BRIEF.md` (family visual language →
   per-module required content → QA), but replace the *completion* bar with a
   *presentation* bar:
   - camera: one hero 3/4 iso, one straight front, one detail crop, consistent
     focal length and horizon across all ten so a grid reads as one family
   - materials: brushed aluminium must read as metal (anisotropic highlight), not
     as light grey; charcoal panels matte; rubber, glass and fabric distinct
   - light: key + fill + rim; contact shadow under the frame so the module sits on
     a surface instead of floating
   - background: a real neutral gradient or seamless ground, plus a separate
     alpha-channel cut-out variant for web use
   - resolution: 2400 × 1800 minimum for hero, ≥ 1600 × 1200 for the rest
   - the existing per-module required-visible-content list (BN-M01…BN-M10) carries
     over verbatim from `VISUAL-DESIGN-BRIEF.md` — legibility is still required,
     presentation is now required *as well*
2. Write `production/ten-modules/visual/visual_quality.py` — a **model-free**
   image gate using only PIL/numpy. This is the cheap first opinion that catches
   "still looks like flat CAD" without spending a single token:
   - luminance histogram spread and clipped-highlight fraction
   - distinct-value count on the aluminium mask vs. the charcoal mask (flat
     shading collapses these)
   - presence of a contact shadow: luminance gradient in the band below the
     silhouette
   - silhouette coverage fraction of frame (hero framing, not a speck)
   - edge density (proxy for detail retention after lighting)
   - background classification: transparent / flat white / gradient
   - per-image SHA-256 in the report, matching the existing evidence convention
   - a `--baseline` mode that scores the current 20 PNGs so every later score is
     relative to a real number, not a guess
3. Run it against the existing 20 renders and commit
   `production/ten-modules/visual/visual-quality-baseline.json`.

### Verify

```bash
cd "Bear Necessities/cad" && ./build.sh validate
python3 "../../Mac Mini Setup/tools/cad-product-agent/production/ten-modules/visual/visual_quality.py" --baseline
```

- Baseline report exists, covers 20 images, each with a SHA-256.
- The baseline **fails** the new thresholds. If it passes, the thresholds are too
  loose — the whole premise is that today's images are not marketing-grade.
- `./build.sh validate` still returns four passing gates (this phase adds no
  geometry).

### Anti-patterns

- No model calls in `visual_quality.py`. It is deterministic or it is worthless as
  a tiebreak.
- Do not tune thresholds until the baseline passes. Set them from the brief.

---

## Phase 2 — Pick the render path and prove it on one module

**DECIDED 2026-08-26: Fusion's own local renderer.** The Phase 0 probe resolved
this — Fusion ray-traces to file, scripted, at up to 3000 × 2400 with HDRI
environments and a ground plane. No install, no approval gate, no second toolchain
to keep in sync with the geometry. The Blender option is withdrawn.

The one real constraint that survives: **Fusion has no headless mode on macOS**, so
Fusion must be running and signed in for every render. Renders are queued one at a
time and run as a background process tied to the Fusion process. A sweep is
therefore long-running-but-unattended-ish: it does not need a human clicking, but it
does need the app left open, and it cannot share the machine with a heavy local
model run. That interacts directly with the LM Studio memory ceiling in Phase 3 —
sequence them, do not overlap them.

### Implement

1. Read `fusion-api-notes.md` in full, then `build_native_modules.py:100–200` and
   `:805–870`.
2. Rung A: add `--visual-profile marketing` to `build_native_modules.py`, defaulting
   to today's behaviour so the existing native gate is untouched. Probe the live
   `Viewport` object for shadow/AO/environment properties and **log what is
   actually there**; do not code against a property you have not seen.
3. Render **BN-M01 only**. Score with `visual_quality.py`. Compare to baseline.
4. If Rung A clears the brief, stop — Phase 3 uses it. If not, write
   `production/ten-modules/visual/RENDER-PATH-DECISION.md` with the two scored
   BN-M01 images side by side and the attended-render argument, ask Conor, and on a
   yes build `production/ten-modules/visual/render_module.py` for Blender:
   - `bpy.ops.wm.obj_import(filepath=...)` reading the existing OBJ + MTL
   - map the `PALETTE` keys from `build_native_modules.py` onto Principled BSDF
     values (metallic 1.0 / roughness 0.28 for aluminium; metallic 0 / roughness
     0.52 charcoal; separate glass, rubber and fabric)
   - three-point light, ground plane with contact shadow, gradient world
   - the brief's camera set, identical across modules
   - CLI: `--module BN-M01 --views iso,front,detail --out <dir> [--alpha]`
5. Whichever path wins, BN-M01 must produce a full view set that passes Phase 1.

### Verify

- BN-M01 hero, front and detail exist at the brief's resolutions.
- `visual_quality.py` scores BN-M01 **above** the Phase 1 thresholds and above its
  own baseline on every metric.
- Direct inspection: the aluminium reads as metal, the module sits on a surface,
  every item on BN-M01's required-visible-content list is still identifiable.
- The default (no `--visual-profile`) path still reproduces the old images, so
  `./build.sh native` and `validate_native_family.py` are unaffected.

### Anti-patterns

- Do not block inside Fusion waiting for a render. `startLocalRender` is async and
  queued; fire it and poll for the output file from the host.
- Do not set `groundRoughness` without first enabling `isGroundReflections`, and do
  not assign `backgroundType` — it is read-only.
- Do not re-model geometry to make a render look better. Phase 2 changes
  presentation only. Geometry changes are Phase 7.
- Do not install Blender before asking.
- Do not delete the existing 20 PNGs. Write the new set to a new directory.

---

## Phase 3 — Ten local iteration cycles across all ten modules

Target: **≥ 10 cycles × 10 modules = ≥ 100 module-visual reviews**, all local, zero
Claude usage.

### The local-model design, given the laptop constraint

Phase 0 established that this 16 GB laptop kernel-panicked on the 14B and that
every capable VLM is over budget. So the loop uses **two graded opinions**, not one:

1. **Deterministic** — `visual_quality.py`. Free, runs on every image, every cycle.
   This is the primary gate.
2. **Local VLM second opinion** — `qwen2.5-vl-3b-instruct` (2.88 GiB, the only
   vision model that fits), **one image at a time**, against a fixed yes/no
   checklist derived from the brief, not an open-ended "is this good?".
3. **Local text critique** — `qwen2.5-coder-7b-instruct` (the profile-approved
   7B) reads the *numeric* `visual_quality.py` report plus the VLM checklist and
   proposes the next parameter change. It never sees an image, so it costs nothing
   in VRAM beyond the 7B, and its job is narrow: pick the next lighting/material/
   camera delta from a fixed vocabulary.

If Conor runs this on the Mac mini instead, `runtime.json`'s `mac-mini` profile and
`google/gemma-4-e4b` apply and step 2 upgrades — the loop must read the profile,
not hard-code the model.

### Implement

1. Copy the resource guard and JSON extraction from
   `fusion_native/review_native_family.py:1–60` verbatim into a new
   `production/ten-modules/visual/run_visual_cycles.py`. Do not rewrite them.
2. Copy the **resumability** pattern from `iterations/run_revision_cycles.py`: one
   validated file per cycle, reused on re-run. A 100-review sweep must survive an
   interrupt without restarting. This is stated in `cad/README.md` as the reason it
   exists — a full sweep is expensive.
3. Enforce the laptop profile from `LM-STUDIO-SAFE-PROFILES.md`: 6144 context,
   1800-token output cap, one prediction, speculative decoding off, 30 s cool-down,
   load ceiling 20, free-memory floor 30 %.
4. **Guard against the two known failure modes, explicitly:**
   - *Silent parallel instance* — after each VLM call, query
     `/v1/models` and abort if more than one instance of the vision model is
     resident. This is what drove free memory 74 % → 32 % on 2026-08-25.
   - *Self-contradictory verdict* — reject any response where
     `verdict == "PASS"` and `blocking_findings` is non-empty. Count it as a failed
     attempt and retry within the attempt budget.
   - *The 2026-08-25 length bug* — `cad/STATUS.md` records a 30-cycle run killed by
     a 267-character field against a 240-character cap whose error message said only
     "length/type invalid", so the model resampled instead of shortening. **State
     every limit in the prompt, and make every failure message report the measured
     value and the delta.** Repeat that fix here; do not re-earn it.
5. Write `visual-iteration-ledger.json` in the shape of
   `iterations/runs/iteration-ledger.json`: per cycle, per module — image SHA-256,
   deterministic scores, VLM checklist, adopted delta, model ID actually used.
6. Add `production/ten-modules/visual/validate_visual_ledger.py`, modelled on
   `iterations/validate_revision_ledger.py`: ≥ 10 cycles × 10 modules, every record
   carries a real model ID, every image hash is current, no adopted change violates
   a frame invariant.
7. Wire a `./build.sh visuals` stage into `cad/build.sh` and a matching
   `preflight.py --for visuals`. Follow the existing stage pattern exactly — resolve
   from `runtime.json`, honour `BN_*`, add the new models under `models` with
   `BN_VISUAL_*` overrides.

### Verify

```bash
cd "Bear Necessities/cad"
python3 preflight.py --for visuals
./build.sh visuals
python3 "$BN_STUDY/visual/validate_visual_ledger.py"
```

- Ledger shows ≥ 100 module-visual reviews across ≥ 10 cycles.
- Every one of the 10 modules scores above the Phase 1 thresholds on its final set.
- No record carries a fabricated model ID; the low-memory continuation policy is
  named explicitly if a mixed roster was used (the existing ledger convention).
- The sweep survives a deliberate `Ctrl-C` and resumes rather than restarting.
- **Zero Claude tokens spent in this phase.**

### Anti-patterns

- Do not send more than one image per request.
- Do not load a model above the profile's memory budget because "it's just one run".
  That is exactly the 2026-08-25 kernel panic.
- Do not let the VLM's prose become the gate. The numbers are the gate; the VLM is
  a checklist second opinion.
- Do not let a local model edit geometry. It proposes presentation deltas from a
  fixed vocabulary; anything else needs Phase 7.

---

## Phase 4 — One Claude confirmation pass

Exactly one pass. Its job is to answer a question the local loop structurally
cannot: *would a customer looking at this grid believe it is a real product?*

### Implement

1. Assemble a single contact sheet: all ten hero renders in one grid, plus the ten
   fronts, at review resolution.
2. Claude inspects each image directly and scores against
   `VISUAL-MARKETING-BRIEF.md`:
   - family consistency — does the grid read as one product line
   - material believability
   - per-module legibility of required content (the BN-M01…M10 list)
   - anything that reads as CAD rather than product
3. Write `production/ten-modules/visual/CLAUDE-VISUAL-CONFIRMATION.md`: verdict per
   module, every finding bound to the image SHA-256 it refers to, and — critically —
   each finding classified as **presentation** (fix in the render script) or
   **geometry** (feeds Phase 7).
4. Presentation findings go back through **one** more local cycle (cycle 11+), not
   through Claude.

### Verify

- Ten modules, ten verdicts, every finding hash-bound.
- Findings are split presentation vs. geometry; the geometry list is the input to
  Phase 7.
- If any module fails: fix locally, re-render, re-score with `visual_quality.py`,
  and only re-invoke Claude if a *second* confirmation is explicitly wanted. The
  budget is one pass — spend it after the local loop is exhausted, not during.

### Anti-patterns

- Do not use Claude to iterate. It confirms; the local loop iterates.
- Do not accept a Claude pass on a stale image. Re-hash first.

---

## Phase 5 — Deployed configurations

How the ten modules combine inside a real vehicle. This is a **deterministic
packing problem**, not a model task.

### The arithmetic that will drive every answer

One module is 24 W × 20 D × 18 H. Therefore:
- two side by side = **48 in wide** — wider than most SUV cargo bays between the
  wheel wells
- two stacked = **36 in tall** — taller than most SUV cargo-bay clear height, and
  it puts mass above the belt line
- one module deep = 20 in, so depth is the axis with the most room

Expect the honest answer to be that most vehicles take **2–4 modules**, not ten, and
that the product story is a *chosen subset* per trip, not a full stack. Design for
that; do not force a ten-module render that no vehicle can hold.

### Implement

1. Read `product/custom-parts/C-02-vehicle-queue.json` — it already ranks the target
   vehicles (4Runner first, and a `rank: 0` **UNIVERSAL L-track** entry whose note
   argues one SKU beats ten). Read `C-02-universal-ltrack.md` too. The configuration
   work and the C-02 decision are the same decision seen from two sides.
2. Read `module-family.json` for each module's `function`, `primary_component`
   envelope and `internal_layout` — that is where access requirements come from
   (BN-M01's stove tray pulls out; BN-M03's fridge lid opens *upward*, which forbids
   stacking anything on it; BN-M04's basin needs headroom).
3. Build `production/ten-modules/configurations/config_solver.py`:
   - input: a vehicle cargo envelope (W × D × H, wheel-well intrusion, tailgate
     opening) and a chosen module set
   - constraints: clearance, **access direction per module** (top-open vs.
     front-pull vs. side), stack limit, total mass, and load distribution front-to-rear
   - output: valid placements, ranked, with the reason any arrangement was rejected
   - **`# ponytail:` a brute-force placement search over ≤ 6 modules; swap for a
     real bin-packer only if the module count grows**
4. Write `configurations/VEHICLE-ENVELOPES.json` — cargo dimensions per target
   vehicle. **Every entry needs a source URL and a date, or status
   `UNVERIFIED_NEEDS_MEASUREMENT`.** `C-02-vehicle-queue.json`'s `_README` says it
   plainly: dimensions invented by a model produce parts that do not fit, and that
   is the most expensive error this project can make. The same applies here.
5. Define 4–6 named configurations as the product story, e.g.
   - **Weekend Base** — cook + pantry + water
   - **Trail Kitchen** — cook + fridge + sink
   - **Basecamp** — cook + fridge + water + power
   - **Remote Office** — power + field office + pantry
   - **Full Send** — the maximum that actually fits a 4Runner-class bay
6. Render each configuration through the Phase 2 pipeline: modules in place, with
   an indicative vehicle bay volume. Same camera language as the module heroes.
7. Write `configurations/CONFIGURATIONS.md`: per configuration — modules, footprint,
   mass, which vehicles fit it, what you can reach with the tailgate open.

### Verify

```bash
python3 "$BN_STUDY/configurations/config_solver.py" --vehicle 4runner-5th --set M01,M03,M05 --explain
```

- Every configuration is solver-validated, not hand-asserted.
- Every vehicle envelope is either sourced-and-dated or explicitly UNVERIFIED.
- Every configuration render passes `visual_quality.py`.
- Access is checked, not assumed: no configuration blocks a module's opening
  direction, and BN-M03's top-opening lid has nothing above it.
- The solver **rejects** an over-wide arrangement — prove it by asking for two
  side-by-side modules in a bay narrower than 48 in and confirming a clean rejection
  with a reason.

### Anti-patterns

- Do not invent a cargo dimension. Cite it or mark it unverified.
- Do not produce a marketing configuration the solver rejects.
- Do not silently resolve C-02 here. Configuration work will *inform* the L-track
  decision; `Bear Necessities/CLAUDE.md` says that call is Conor's.

---

## Phase 6 — Off-the-shelf audit and BOM rework

The ask: make as much as possible off the shelf — **explicitly including the
aluminium extrusion** — and mark clearly what is not.

### The problem with today's BOM

Statuses conflate two independent axes: *can I buy it* and *is it engineering-
released*. `ORDERABLE_ENGINEERING_HOLD` and `DEALER_ORDER_ENGINEERING_HOLD` are both
axes in one string. Split them.

### Implement

1. Add an `ots_class` column to `product/bom/modules/all-modules-prototype-bom.csv`,
   independent of `status`:
   - `OTS_STOCK` — buy the catalog item as-is
   - `OTS_CUT` — catalog item, vendor cuts to length; still off-the-shelf ordering
   - `OTS_MODIFIED` — catalog item requiring drilling/tapping/machining after receipt
   - `CUSTOM_FLAT` — must be fabricated, flat plate from sheet (the standing rule in
     `Bear Necessities/CLAUDE.md`)
   - `CUSTOM_OTHER` — must be fabricated, not a flat plate. **Any row landing here
     is a design failure to be escalated, not accepted.**
2. Update `product/bom/make_bom.py` to emit the column, and extend
   `validate_family.py`'s BOM checks to require it on every row. Keep the existing
   31-row single-module check intact.
3. **The extrusion question, specifically.** Today: `TNUTZ-EX1010-18` ×8 and
   `TNUTZ-EX1010-22` ×4, both `ORDERABLE` with "select length, no machining" —
   i.e. a vendor cut-to-length service, `OTS_CUT`. Answer three things with
   sourced evidence:
   - What does TNUTZ / 80/20 charge for cut-to-length vs. standard mill lengths?
   - Can 8 × 18 in + 4 × 22 in be cut from standard stock with acceptable drop?
     (12 pieces totalling 232 in — check against common mill lengths.)
   - Is there a *standard catalogue length* at or near 18 in or 22 in that removes
     the cut entirely?
   **Constraint: preserve two cut lengths only.** `Bear Necessities/CLAUDE.md`
   calls it the cheapest orderable cut list and says to preserve it in any redesign.
   Do not "optimise" into three lengths.
4. Resolve the outstanding availability holds:
   - `ENGEL-MD14` is **SOLD_OUT**; `ENGEL-MHD13-ALT` is the
     `ORDERABLE_ALTERNATE_VERIFY` replacement. The 2026-08-25 revision sweep already
     adopted this as BN-M03's one prototype requirement
     (`LOCAL-MODEL-ITERATION-LEARNINGS.md`). Close it: verify the alternate's
     envelope against BN-M03's `internal_layout` and either promote it or find
     another.
   - Three `DEALER_ORDER` rows (Reliance Aqua-Tainer ×2, Rubbermaid tote) — find an
     `OTS_STOCK` equivalent or document why dealer-order stands.
   - `TNUTZ-HAN015AL` is `ORDERABLE_CHECK_STOCK` — confirm or find a second source.
5. `TAP-HYPACT-PANEL` (`ORDERABLE_CUSTOM_CUT`) and `C-01-anchor-plate` are the two
   genuinely non-stock items. Both are flat cuts from sheet, so both satisfy the
   standing rule. Say so explicitly in the report rather than leaving them as
   unexplained exceptions.
6. Write `product/bom/OTS-AUDIT.md`: a table of all 25 catalog IDs by `ots_class`,
   the headline percentage, every non-OTS item with its justification, and the
   extrusion finding with its evidence URLs and date.
7. Regenerate `product/bom/modules/*.csv` and `procurement-bom.csv` and re-run
   `bom_reconcile.py`.

### Verify

```bash
cd "Bear Necessities/cad" && ./build.sh validate
python3 "$BN_STUDY/bom_reconcile.py"
```

- Every BOM row has an `ots_class`.
- **Zero rows** classified `CUSTOM_OTHER`. If any exist, they are named in the
  report as open design problems.
- Every OTS claim cites a catalog ID present in `ots-components.json`, or that file
  gains a new entry with a real vendor, part number, evidence URL and research date.
- The extrusion finding names actual prices/lengths with sources — not "probably
  cheaper".
- Two cut lengths still: 8 × 18 in and 4 × 22 in. `validate_family.py` still passes.
- `SOLD_OUT`, `DEALER_ORDER` and `ENGINEERING_HOLD` dispositions are **preserved**,
  not laundered into OTS. That is a durable framework rule in
  `LOCAL-MODEL-ITERATION-LEARNINGS.md`.

### Anti-patterns

- Do not fabricate a price, stock level or lead time.
- Do not reclassify an `ENGINEERING_HOLD` item as released. Availability and
  engineering release are separate columns for exactly this reason.
- Do not add a third cut length.

---

## Phase 7 — Absorb the changes and re-render

Conor's step 5. Phases 5 and 6 will produce geometry changes; this phase applies
them and proves the visuals survived.

### Implement

1. Collect every geometry change from three sources:
   - Phase 4's **geometry**-classified findings
   - Phase 5 access/clearance conflicts (a module that cannot open in any valid
     configuration needs its opening direction or handle position changed)
   - Phase 6 component substitutions (a different fridge is a different envelope in
     BN-M03's `internal_layout`)
2. Update `module-family.json` and the relevant builder functions in
   `build_native_modules.py`. Keep the frame invariants.
3. Re-run the native Fusion build for **only the changed modules**. Fusion must be
   open and signed in — `cad/README.md` is explicit that `native` is not an
   unattended path.
4. Re-render those modules through the Phase 2 pipeline, and re-render any
   configuration containing them.
5. Re-run one local cycle (cycle 11+) over the changed modules; log it to the same
   ledger.
6. If — and only if — a module's geometry changed materially, spend a second Claude
   confirmation on the changed subset. Note it explicitly in
   `CLAUDE-VISUAL-CONFIRMATION.md` as a second pass, with the reason.

### Verify

```bash
cd "Bear Necessities/cad"
./build.sh native      # Fusion open and signed in
./build.sh validate
python3 "$BN_STUDY/visual/visual_quality.py" --all
```

- All four deterministic gates still PASS, including `mesh_integrity.py` on the
  regenerated STLs.
- Every changed module's renders still clear the Phase 1 thresholds.
- Every affected configuration still solves.
- The visual ledger accounts for the extra cycle.

### Anti-patterns

- Do not rebuild all ten modules to change one. `native` is attended and slow.
- Do not let a geometry change slip in without re-running `mesh_integrity.py` —
  that gate exists because the STL is what suppliers actually receive.

---

## Phase 8 — Final verification

Prove the whole chain, then update project memory.

### Checklist

```bash
cd "Bear Necessities/cad"
python3 preflight.py --for all --json
./build.sh validate                 # four deterministic gates
./build.sh test                     # framework suites, CadQuery venv
python3 "$BN_STUDY/visual/validate_visual_ledger.py"
python3 "$BN_STUDY/visual/visual_quality.py" --all
python3 "$BN_STUDY/configurations/config_solver.py" --validate-all
python3 "$BN_STUDY/bom_reconcile.py"
```

Anti-pattern grep — every one of these must return nothing:

```bash
cd "$HOME/Claude"
grep -rn "CUSTOM_OTHER" "Bear Necessities/product/bom/"
grep -rn "gemma-4-e4b\|qwen3.5-9b" "Mac Mini Setup/tools/cad-product-agent/production/ten-modules/visual/"
grep -rn "renderManager\|DesignManager\|modelRoot" "Mac Mini Setup/tools/cad-product-agent/production/ten-modules/"
```

(The second only matters while the laptop profile is in force; on the Mac mini the
vision model is meant to be gemma. Read the profile, do not hard-code either way.)

### Deliverables

| Item | Path |
|---|---|
| Marketing brief | `production/ten-modules/visual/VISUAL-MARKETING-BRIEF.md` |
| Image gate | `production/ten-modules/visual/visual_quality.py` |
| Render path decision | `production/ten-modules/visual/RENDER-PATH-DECISION.md` |
| Render script | `production/ten-modules/visual/render_module.py` (or the Fusion profile) |
| Iteration loop + ledger | `production/ten-modules/visual/run_visual_cycles.py`, `visual-iteration-ledger.json` |
| Claude confirmation | `production/ten-modules/visual/CLAUDE-VISUAL-CONFIRMATION.md` |
| Config solver | `production/ten-modules/configurations/config_solver.py` |
| Vehicle envelopes | `production/ten-modules/configurations/VEHICLE-ENVELOPES.json` |
| Configurations | `production/ten-modules/configurations/CONFIGURATIONS.md` |
| OTS audit | `Bear Necessities/product/bom/OTS-AUDIT.md` |
| Reworked BOM | `Bear Necessities/product/bom/modules/*.csv` |

### Then

Update `Bear Necessities/CLAUDE.md` (current state) and append a dated entry to
`Bear Necessities/Memory.md` (what happened, what was decided) — the standing rule
in the top-level `CLAUDE.md`. Refresh `cad/STATUS.md` with the new gate list; that
file has gone stale once already and the fix was to re-run the gate, not to trust
the report.

---

## Known risks

| Risk | Where it bites | Mitigation |
|---|---|---|
| 16 GB laptop cannot run a capable VLM | Phase 3 | Deterministic gate is primary; 3B VLM is a checklist second opinion; single-instance guard |
| Fusion has no headless mode on macOS | Phases 2, 3, 7 | Decouple rendering from Fusion (Rung B); Fusion re-runs only on geometry change |
| ~~Blender install needs approval~~ | ~~Phase 2~~ | **Withdrawn** — Fusion renders natively; no dependency |
| Render sweep and local-model sweep both want the machine | Phases 3, 7 | Sequence them; never overlap a render queue with an LM Studio run |
| Vehicle cargo dimensions are largely unpublished | Phase 5 | Same gate as C-02: sourced or `UNVERIFIED_NEEDS_MEASUREMENT` |
| C-02 is still an open product decision | Phase 5 | Inform it, do not decide it |
| Two-high / two-wide stacks may not fit any target vehicle | Phase 5 | Let the solver say so; design the product story around 2–4 modules |
