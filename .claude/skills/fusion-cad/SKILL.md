---
name: fusion-cad
description: Inspect, edit and verify Autodesk Fusion designs and assemblies through MCP - the ten BN-M module assemblies, the base frame, C-01 and any new part. Use whenever a task touches a Fusion design, or the fusion-desktop proxy tools (fusion_mcp_*, bn_snapshot, bn_fusion_status) or Autodesk's Fusion Compute connector tools (start_fusion, invoke_fusion, ...) are available.
---

# Fusion CAD agent

You drive a real CAD kernel through a narrow pipe. The kernel is right about
geometry and silent about intent; the pipe returns an error string at best. So
the work is a loop of **predict → small change → measure → compare**, and the
measurement decides, not how the result looks or how confident the script felt.
The evidence for each rule is in `Fusion CAD Agent/reference/ai-cad-best-practices.md`.

## 1. Find out which Fusion you have

| You see | It is | Notes |
|---|---|---|
| `bn_fusion_status`, `bn_snapshot`, `fusion_mcp_read`, `fusion_mcp_execute` | **Desktop Fusion on the Mac**, via `Fusion CAD Agent/bridge/fusion_mcp_proxy.py` (`.mcp.json`) | Python API, live session, Conor's files |
| only `bn_fusion_status`, `bn_snapshot` | the proxy is up, Fusion is not | call `bn_fusion_status` - it says what to fix |
| `start_fusion`, `invoke_fusion`, `fusion_api_index`, ... | **Fusion Compute** - headless Fusion in Autodesk's cloud (public beta) | TypeScript API, Fusion Team files, see §7 |
| none of these | no Fusion | say so. New parts can still be built headless with `bncad` (§8) |

Tool schemas are discovered when the client connects and Autodesk changes them
between builds. **The schema in front of you is the truth; this file is not.**

## 2. The loop, for every change

1. **Establish state.** `bn_snapshot` (units `in`) before anything else. Record
   document id + version, body count, the visible envelope, unhealthy timeline
   features. Never assume state from an earlier session - Fusion may have
   crashed and recovered to something older.
2. **Predict in numbers.** Before a write, state what the snapshot should say
   afterwards: which bodies change, the new bbox or volume, the body/joint count.
   A prediction you cannot write down is a change you do not understand yet.
3. **One small script per step.** One feature, one move, one property change.
   Inspection scripts pass `"readOnly": true`. Print results as one line,
   `RESULT {json}`, so they parse - Fusion wraps stdout in a
   `{"message", "success"}` envelope.
4. **Measure.** `bn_snapshot` again and diff it against the prediction. For
   anything placed among other parts, run interference
   (`design.createInterferenceInput(collection)` → `design.analyzeInterference`)
   on the affected occurrences. Intentional contact is not a collision; list
   which overlaps are meant.
5. **Look.** Screenshot at the steps that matter (`fusion_mcp_read`,
   `queryType: "screenshot"`, a `direction` such as `current` or
   `iso-top-right` - the schema lists the rest) and compare with the reference
   images in `Bear Necessities/product/marketing/` or the module's
   `-iso.png`/`-front.png` under
   `Mac Mini Setup/tools/cad-product-agent/production/ten-modules/fusion-native/exports/`.
   Looks catch wrong-shape mistakes the numbers miss; numbers catch
   right-shape-wrong-size mistakes the eye misses. Neither alone is evidence.
6. **Save milestones.** `fusion_mcp_execute` with `featureType: "document"`,
   `object: {"operation": "save", "userMessageSummary": "<what changed>"}`; then
   snapshot and confirm the version went up. Save is not export, and export is
   not save.

If a step misses its prediction, fix that step before starting the next. Do not
accept "close enough" and carry on - say what is off, by how much, and iterate.

The proxy logs every call that can change a design - scripts, saves, undo -
with its arguments and outcome to `Fusion CAD Agent/bridge/logs/mcp/`
(gitignored). That log is the change
history when someone asks what was done to a design and why.

## 3. Rules that are not negotiable

- **Look up the API before using it.** Ask the server's API documentation query
  (the read tool's `apiDocumentation` query on desktop; `fusion_api_index` on
  Compute) for any class or method you have not already used successfully this
  session. Local and frontier models alike invent plausible members;
  `Fusion CAD Agent/reference/fusion-api-notes.md` lists ones already caught.
- **Units.** The API is **centimetres and radians**, whatever the document
  shows. The product is in **inches** (1 in = 2.54 cm). Prefer
  `adsk.core.ValueInput.createByString("18 in")` - Autodesk's API reference
  confirms explicit-unit expressions - over hand-converted reals. One module
  spans at most 24 in (about 61 cm); a part dimension far outside that, or
  2.54x / 25.4x off a spec number, is a units bug until proven otherwise.
- **Never close a document**, never open a modal dialog (`messageBox`,
  `inputBox`, file dialogs). Both block Fusion's API until a human clicks. The
  proxy refuses them; Fusion Compute has no human to click at all.
- **A timeout is not a failure.** A write that timed out may have run. Snapshot,
  then decide - never blind-retry a write.
- **Never join, combine or delete the user's geometry without asking.** Build a
  new body or component, show it (numbers + screenshot), and wait for a yes.
- **Do not swallow exceptions.** If you catch one, print the traceback and
  re-raise: an error string is the only feedback the loop has.
- **Sketch coordinates.** Do not hand-map sketch axes on XZ/YZ planes - they do
  not map the way they look. Convert with `sketch.modelToSketchSpace(point)`, or
  sketch on an XY-parallel offset plane.

## 4. Assemblies

- **This product's native archives** (`BN-M01…M10.f3d`, built by
  `ten-modules/fusion_native/build_native_modules.py`) are **direct-modeling** designs: one
  component per body, every occurrence at an identity transform, the body
  geometry itself at its absolute position, no joints, no timeline. The
  snapshot's body bboxes locate parts; occurrence translations will read zero.
  Do not look for parameters that are not there. Converting one to parametric is
  a design decision - ask first.
- **New or reworked assemblies:** one component per physical part, never loose
  bodies in the root. Repeated parts are occurrences of one component, so the
  browser counts the BOM: the frame is two components (18 in rail, 22 in rail)
  and twelve occurrences.
- Ground one base component. Mate everything else with **joints** (rigid unless
  it moves), or **as-built joints** where parts are already in place; rigid
  groups for weldment-like sub-assemblies. When a component has jointed
  subcomponents, joint those subcomponents rather than the parent to the
  top-level component - Autodesk documents that case failing to mate.
- Fusion now has **part, assembly and hybrid** design types. An assembly design
  refuses modeling features; a part design refuses new components. If an
  operation fails that way, check the type before rewriting the script.
- After any placement: interference, joint health (snapshot `joints`), and a
  screenshot from two directions.

## 5. Parametric hygiene (new parts)

User parameters for driving dimensions (`FRAME_W = 24 in`, `EXTRUSION = 1 in`),
features and components named for what they are, dimensions taken from datums
rather than absolute coordinates, and a healthy timeline after every step
(snapshot `timeline.unhealthy` must stay empty). A sketch drawn with raw
coordinates and no constraints passes today and breaks on the first edit.

## 6. Bear Necessities rules the CAD must keep

- Module frame **24 W × 20 D × 18 H in**, 1 in aluminium extrusion.
- **Two cut lengths only - 18 in ×8 and 22 in ×4.** Any redesign that adds a
  third length needs Conor's say-so; it is the cheapest orderable cut list.
- **Every custom part is a flat plate cuttable from sheet.**
- Do not break the family frame or replace the chest fridge to force SUV fit.
  C-02 (vehicle floor bracket) is Conor's product decision, not a CAD task.
- **STEP units trap:** CadQuery STEPs claim millimetres. `bncad` deliverables
  are real millimetres; anything else, import and check the bbox in inches
  before trusting it (`bncad fusion <step>` cross-checks both kernels).
- Heavy design + render environment hangs Fusion: warm the render stack on an
  empty document first (`ten-modules/visual/render_module.py`). Do not let LM Studio hold
  the GPU while Fusion renders. Full account: `Bear Necessities/Memory.md`.

## 7. Fusion Compute (cloud, headless) specifics

Autodesk's hosted server: `https://developer.api.autodesk.com/da/v3/mcp/fusion`,
Autodesk sign-in, a Fusion licence and a Fusion Team hub. Public beta.

1. `fusion_sessions` - reuse a running session if there is one (two per user).
2. `start_fusion` (`toolMode: "CRUD"` for the native assembly/CAM tools,
   default `Execute` for TypeScript, `CRUDE` for both). A `queued` status is
   normal - poll `fusion_status`.
3. `invoke_fusion` with no arguments lists the worker tools; describe one
   before calling it.
4. Scripts for `MCP.ExecuteTypeScript` are bare scripts: no top-level
   `import`/`export`; `adsk` is already in scope; types via
   `type Design = import("@adsk/fusion").adsk.fusion.Design;`. Return data by
   assigning `adsk.result = JSON.stringify(...)` and log with `adsk.log(...)` -
   spelled literally, never through an alias, or the output is lost.
5. There is no `bn_snapshot` here. `snapshot.ts` beside this file is its port -
   **untested against Fusion Compute**; on first use run it on a part with known
   dimensions (C-01, P01) and fix it with `fusion_api_index` if it errs.
6. Sessions stop after **15 minutes idle** and anything not saved to Fusion Team
   or exported is lost. Export links (`fusion_view_3d`, STEP/STL) expire after
   15 minutes. Save before you pause; `stop_fusion` when done.

## 8. When not to use Fusion for it

New parts from a written spec go through `bncad` first (`Fusion CAD Agent/bncad`):
headless, sandboxed, measured against the spec and repaired with real numbers.
Then import the validated STEP into Fusion to assemble and finish it. Autodesk's
own guidance is the same: the MCP is strongest at reading designs, editing
properties of existing components and assisting scripting, and weakest at
sketch-heavy creation from scratch.

## 9. Done means

Every predicted number matched (or the gap is reported), the timeline is healthy,
interference is clean or explained, a screenshot was reviewed, the document is
saved and its new version recorded - and the report says plainly what is **not**
verified: physical fit, strength, manufacturability, anything only a build shows.
