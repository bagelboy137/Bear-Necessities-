# Memory.md — Fusion CAD Agent

Durable knowledge base. Dated entries; decisions and why.

## Verified facts (2026-08-20)

### Machine state
- **Autodesk Fusion 360 is already installed** on Conor's current laptop (Apple M1 Pro, 16GB). Support folder: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/`, versions `2703.1.20` and `2704.1.36` seen in the add-in cache files.
- `API/Scripts/` and `API/AddIns/` both **exist and are empty** — no prior scripting work on this machine. A `MyScripts/` folder also exists.
- LM Studio is installed and serving at `http://localhost:1234/v1`; models present as of 2026-08-19: `qwen/qwen3.5-9b`, `meta-llama-3.1-8b-instruct`, `voxtral-realtime-et`, `text-embedding-nomic-embed-text-v1.5`. None of these are strong coding models — all are below what this project needs.

### Fusion API constraints (design-shaping)
- Fusion's Python API runs **inside Fusion's embedded CPython interpreter, in the GUI process**. It is not a normal importable library — `import adsk` only resolves inside Fusion.
- **No supported headless mode on macOS.** Fusion must be running, signed in, with a GUI session. This is compatible with the Mac Mini Setup plan only because auto-login is already decided (FileVault off, unattended reboot recovery).
- A Fusion "script" is a folder containing `<Name>.py` plus a `<Name>.manifest` JSON file, placed under `API/Scripts/`.
- **Fusion is not an offline application.** Autodesk sign-in is required, with only a limited offline window (historically ~2 weeks) before re-auth. The local LLM is offline; Fusion is not. Any pitch of "fully air-gapped CAD" is wrong and should be corrected on sight. Re-verify the current offline window against Autodesk docs before relying on it.

### Hardware implication (feeds Mac Mini Setup)
- Mac Mini Setup's existing target is **32GB unified memory**, sized for a coding model alone (Qwen3-Coder-30B ≈19GB at Q4, Devstral-24B ≈14GB).
- **This project adds a second consumer on the same box:** Fusion 360 is a heavyweight GUI app that wants several GB on its own, and the loop needs both resident at the same time. That makes 32GB the *floor* rather than a comfortable target, and argues for 48–64GB if the budget allows.
- Current laptop (16GB) cannot host a 30B-class coding model **and** Fusion simultaneously — fine for prototyping the plumbing, not for the real workload.

## Decisions

- **2026-08-20 — The model writes scripts; it does not "drive" Fusion.** Follows directly from the embedded-interpreter constraint. Any design that assumes the agent clicks around Fusion's UI is rejected; UI automation of a CAD app is brittle and slow compared to generating API scripts.
- **2026-08-20 — Prototype on the laptop first.** Fusion and LM Studio are both already installed here. Same approach that worked for `lm_studio_bridge.py`: prove the mechanism before the mini is purchased, so October is assembly rather than discovery.

## Open threads
- Manual script execution vs. a persistent watcher add-in (leaning watcher).
- Model selection — untested, no eval suite exists yet.
- **Neutral-format escape hatch:** generating OpenSCAD or CadQuery (both far better represented in model training data than Fusion's API) and importing the result may beat direct Fusion API scripting on first-pass success rate. Untested, but it is the most likely thing to change the whole architecture — test it early.
- First real part to attempt. Escalade bracket is the leading candidate (`Escalade Work`).

## Log

- 2026-08-20: Project created. Conor asked for a Mac mini running an offline model to develop CAD models in Autodesk Fusion; folders scaffolded under the standing rule. Audited the existing landscape first and found three things that shaped the design rather than starting from scratch: (1) `Mac Mini Setup` already owns the hardware decision and already targets 32GB for local models, (2) `Mac Mini Setup/tools/lm_studio_bridge.py` already implements the "send a task to the local model, write the answer to a file" half of the loop, and (3) an established LM Studio agent workspace exists in iCloud with a `01_rules` / `02_context` / `03_skills` / `04_outputs` convention and four agents already defined. Rather than duplicate any of that, this project owns only the CAD-specific half and cross-links out. Added a `fusion-cad-agent` to the LM Studio workspace following its existing convention. Verified Fusion is installed locally with empty, ready API script folders. Two constraints documented up front because they invalidate the obvious approaches: Fusion's Python API only runs inside Fusion's own GUI process (no headless macOS mode), and Fusion itself requires periodic Autodesk sign-in, so the *model* is offline but the CAD app is not.

## Trial setup — 2026-08-20

### The constraint that decides the model: macOS GPU memory cap
macOS lets the GPU address only **~70% of unified memory**. A 16GB Mac is effectively an **~11GB machine** for model weights. `iogpu.wired_limit_mb` is `0` (default) on this laptop; it can be raised with `sudo sysctl`, but doing so starves everything else.

**This is the single most useful number in the project** — it is what actually determines which models are reachable at each RAM tier, and it applies to the mini purchase too. A 32GB mini is a ~22GB model machine; a 64GB mini is a ~45GB one.

### LM Studio catalog, checked 2026-08-20
| Model | ~Size @ 4-bit | Fits ~11GB |
|---|---|---|
| qwen/qwen2.5-coder-14b | ~8.3GB | ✅ chosen for the trial |
| mistralai/devstral-small-2-2512 | ~13GB | ❌ |
| qwen/qwen3-coder-30b (MoE A3B) | ~17GB | ❌ |
| qwen/qwen2.5-coder-32b | ~18GB | ❌ |
| qwen/qwen3-coder-next (80B MoE) | ~45GB | ❌ |

Also on disk but **not valid tests** — all general-purpose, none coding-specialised: `qwen/qwen3.5-9b`, `meta-llama-3.1-8b-instruct`, `google/gemma-4-e4b`.

### Machine audit
- Fusion 360 installed; `API/Scripts/` and `API/AddIns/` empty and ready.
- LM Studio service running, server on port 1234; `lms` CLI at `~/.lmstudio/bin/lms`, already on PATH via `~/.zshrc` line 3.
- System Python **3.9.6** — fine for the stdlib-only bridge, but **too old for CadQuery** (wants 3.10+), which is why OpenSCAD is the chosen control-test format.
- No Homebrew. 522GB disk free.

### Caveat on what the trial proves
Qwen2.5-Coder-14B is **two tiers below** what a 32GB+ mini would run. A poor score is a floor, not a verdict on the approach. A good score is a strong buy signal.

## First trial run — 2026-08-20

### Result: blocked on a settings toggle, not on hardware
`qwen/qwen2.5-coder-14b` (MLX 4-bit, 8.33 GB) downloaded and registered fine, but **will not load**: LM Studio estimates **10.86 GiB** and its resource guardrail refuses. Key detail — the estimate is **10.86 GiB at every context length tested** (3072/4096/6144/8192), so it is weights-dominated and shrinking context does not buy anything. Unloading all other models did not help either.

Fix is a GUI-only setting: **Settings → Hardware → Model Loading Guardrails → Relaxed/Off**. Not reachable from the `lms` CLI, and not stored anywhere under `~/.lmstudio/.internal` that could be edited.

### The harness works
`evals/run-eval.sh` ran end-to-end against a loaded model, wrote its output file, and **correctly detected and reported the failure mode** ("hit --max-tokens before any answer text was produced"). The plumbing is proven; only the model is missing.

### `qwen/qwen3.5-9b` scored 0 on everything — and the useful part is *why*
Run as a floor while the 14B was blocked. On the trivial "100×60×6 mm plate" task it produced **no answer in 2m37s**, emitting `Wait, createExtrude might take profile and direction and distance?` several hundred times until the budget ran out. This is the quirk already logged in `Mac Mini Setup/Memory.md`, now reproduced on this workload.

**It also failed the OpenSCAD control the same way (1m54s, empty output).** That matters: because it failed the *easy neutral format* too, the failure is the model rather than the Fusion API. **The Fusion-API-vs-OpenSCAD architecture question remains genuinely open** — this run does not answer it, and should not be cited as if it did.

### Confirmed: the general-purpose models on disk are not substitutes
`qwen3.5-9b`, `meta-llama-3.1-8b`, `gemma-4-e4b` are not coding models. The 9B result shows what that costs — this workload needs a code-specialised model, not merely a competent general one.

### Catalog gap worth knowing
LM Studio's staff picks contain **no Qwen2.5-Coder below 14B** — the coder list is 14b, 32b, qwen3-coder-30b/480b/next. There is no smaller in-catalog fallback; anything below 14B would have to come from a direct Hugging Face URL.

## Architecture question ANSWERED — 2026-08-20

Worked around the blocked 14B by pulling **`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`** from Hugging Face (4.30 GB, loads at 4.00 GiB in 8s, ~24s per generation). LM Studio's staff-pick catalog has no Qwen coder below 14B, but `lms get <hugging-face-url>` works and is the escape hatch.

### Result: generate-and-import beats direct Fusion API scripting
Same model, same two parts, two output formats:

| Part | Fusion Python API | OpenSCAD |
|---|---|---|
| 100×60×6 plate | **0** — every Fusion call invented; 10x unit error (`length = 100.0 # cm` for a 100 mm plate = a 1-metre plate) | **3** — `cube(size = [100, 60, 6]);` correct first try |
| L-bracket | **0** — every feature call invented, no mm→cm conversion at all | **2** — renders, but no gusset and holes unioned instead of subtracted |

**The important part is not the scores, it is the *kind* of failure.** In the Fusion API the model invents classes and method signatures, so nothing executes and there is no traceback to iterate from — a dead end. In OpenSCAD the code runs and produces a *wrong shape*, which is visible, diagnosable, and fixable by iteration. One failure mode has a feedback loop; the other does not.

Also telling: it invents a **different** wrong answer each run — `modelRoot.findItem("XY Plane")` on one task, `model.workplanes.itemByName("XY Plane")` on the next. It is not misremembering a fixed API; it is generating plausible-looking shapes on demand. Full list in `evals/results/SCORES.md`.

### Caveat — this is strong evidence, not proof
7B is two tiers below what a 32GB mini would run, and niche-API knowledge is exactly what improves with scale. Re-run both columns on the 14B, and later on a 30B, before declaring the Fusion-API path closed. The eval set and harness now exist to make that a cheap repeat.

### Not verified
OpenSCAD is still not installed, so its output was never rendered — the OpenSCAD scores are from reading code, not from looking at geometry.

### Consequence if this holds
The architecture in `CLAUDE.md` changes: model emits OpenSCAD → render/convert to STEP → import into Fusion. That trades away Fusion's parametric feature tree, which is a real loss for a *parametric* CAD workflow, and is the main argument for retesting at 14B/30B before committing.

## First real prototype produced by the local model — 2026-08-20

Conor supplied a product sheet for a **Modular Overland Camp System** (80/20 extrusion, six module types, all 24"W × 20"D × 18"H) and asked for one prototype drawing, generated by the local model, overnight.

### CAD toolchain: neither Fusion nor OpenSCAD — `ezdxf`
Audit found no `uv`/`pipx`, no OpenSCAD, and **Python 3.9 only**, which rules out CadQuery (needs 3.10+) and build123d. Fusion is installed but has no headless mode, so it cannot be driven unattended.

**Chose `ezdxf` + matplotlib in a venv.** Pure Python, installs on 3.9, fully headless, and emits **DXF — a real CAD interchange format that opens directly in Fusion**. This is the toolchain to keep for unattended work; it is the only one that closes the loop without a GUI.

### The loop works, and the feedback is what makes it work
Built `bridge/cad_loop.py` + `bridge/validate_drawing.py`: model writes an ezdxf script → script runs → **drawing is validated geometrically** → failures are fed back as specific, actionable errors → retry. Watched it go 4 errors → 3 → clean across three attempts. The model demonstrably fixes what it is told about.

### Finding: "it ran" is a near-worthless bar
The first run passed on attempt 1 and produced a **bad** drawing — all three views stacked at (0,0), a nonsense cut list ("12 x 4\" x 18\""), and the right view using WIDTH instead of DEPTH. The check was "script exits 0 and DXF has ≥10 entities." Both true, drawing useless. **Validation has to check the geometry, not the exit code** — view bounding boxes disjoint, view sizes correct, text not colliding, cut-list arithmetic right. That change is what turned the loop into something useful.

### Finding: the 7B cannot invent spatial layout, but can apply it
It was stuck for 12 straight attempts emitting the **byte-identical script** (2305 chars, 22s each) — it could not work out how to offset three views so they do not overlap, and re-feeding the error changed nothing. Supplying the pattern explicitly in the system prompt (a `place(points, dx, dy)` helper plus example offsets) unstuck it immediately. **Local models need structural scaffolding for spatial reasoning; they can execute a pattern they cannot derive.** Also added stuck-detection that raises temperature when output repeats.

### Finding: an all-or-nothing loop can destroy its own best work
The loop deleted the DXF before each attempt, so tightening the validator mid-run **overwrote a good drawing with worse ones** and ended with nothing. Now keeps `*-best.dxf`/`*-best.py` scored by error count. Any long unattended run needs this.

### Result
`exports/PROTOTYPE-overland-base-frame.dxf` (+ PNG, + README). Three labelled orthographic views and a **correct, usable cut list**: 4 posts @ 18", 4 width members @ 22", 4 depth members @ 18" — a valid BOM for a 24×20×18" outside cube in 1010 extrusion. Remaining defects: right view renders ~22" wide instead of 20", not all 12 members drawn, a stray rectangle in the top view, no dimensions or title block. **A genuine prototype, not a shop drawing.**

### The 14B stayed blocked
It loaded once earlier at 7.75 GiB, but the guardrail refused it for the rest of the session even with `mode: "off"` in `settings.json` and 78% memory free. **The guardrail setting is not reliably honoured** — worth remembering before depending on a 14B-class model on 16GB. The whole run therefore used the 7B, which is the weaker model; the 14B would likely clear the strict bar.

## Workflow upgraded to CadQuery + BOM — 2026-08-20 (late)

### Python 3.12 installed without touching system Python
CadQuery 2.8.0 requires **>= 3.11**, so the user's suggested 3.10 would have been too old — checked rather than assumed. Installed **Python 3.12.14** via `uv` (itself pip-installed into `.venv-boot`, avoiding a `curl | sh`). System Python 3.9.6 untouched, no sudo, no Homebrew. CadQuery env at `.venv-cq/`. OCP has macOS arm64 wheels for cp310-cp314.

### CadQuery is a large step up on validation
Solid geometry allows **numeric** checks that 2D cannot: exact bounding box, exact volume against an analytical target, solid count, validity. "Volume is 34452.00, expected 232.00 - members are overlapping" is a far better signal than any DXF entity count. `bridge/cq_loop.py` + `bridge/cq_validate*.py`.

### CONFIRMED TECHNIQUE: supply the pattern the model cannot derive
Three independent cases now, all identical in shape — the model fails repeatedly, is given the code pattern, then succeeds **first try**:

| Task | Before scaffolding | After |
|---|---|---|
| Three non-overlapping 2D views (ezdxf) | 12 attempts, byte-identical output each time | success |
| Flat plate w/ holes + fillets (CadQuery) | 10 attempts, invented `workplane(centerX=...)` | **1st attempt, volume exact to 4dp** |
| 12-member 3D frame (CadQuery) | 10 attempts, got 38x27x54 and 34452 in^3 | **1st attempt, 24x20x18, 232.00 in^3** |

The failure is never "can't write Python" — it is inventing API that does not exist, and being unable to derive a spatial layout scheme. Both are fixed by putting a concrete, copyable pattern in the system prompt. **This is the single highest-leverage thing in the whole project** and should be the first move for any new part type.

### Ceiling is sharp, not gradual
The 7B did the flat plate perfectly on the first attempt while being *completely* unable to place 12 members in 3D (off by 34,000 in^3) until given the member table. Flat/parametric work is within reach; unscaffolded 3D assembly is not.

### BOM: part numbers must never come from the model
Built `../Bear Necessities/product/bom/` with a **hand-verified catalog** (`catalog.json`) separate from the generator. The LLM produces geometry; part numbers come from curated data. A hallucinated part number is the one error that costs real money on a drop-ship order. Web research caught a real trap: **4302 is a 15 Series bracket, not 10 Series** - the correct 10 Series parts are **4108** (lite), **4132** (gusseted), **3395** (anchor fastener), profile **1010-S** (TNUTZ **EX-1010** equivalent, cuts to length, ~48h).

### Design finding worth keeping
24 x 20 x 18" outside in 1" profile yields only **two distinct cut lengths** - 18" x8 (posts + depth rails) and 22" x4 (width rails). Cheapest possible cut-to-length order. Falls straight out of the proportions already on the product sheet.

## 2026-08-20 (end of day) — job queue added
`bridge/run_queue.py` walks a JSON queue and builds only jobs marked READY, skipping anything gated on missing real-world data. Validators are per-part (`cq_validate_c02u.py` etc.) and selected by the queue entry. Dry-run verified: 1 ready, 10 blocked. LM Studio closed for the day afterwards; the queue runs whenever it is next up.

**Pattern worth reusing:** the queue's value is the *gate*, not the automation. The model is perfectly willing to invent vehicle hole spacing, and the output would look plausible. Encoding "this job cannot run until a human supplies measurements" into the queue is what stops a confident wrong answer becoming a physical part that does not fit.

## 2026-08-21 — Fusion ships an MCP server. The whole architecture changes.

Conor pointed out **Preferences → General → API → "Fusion MCP Server"** (local, `http://127.0.0.1:27182/mcp`) and enabled it. This **invalidates the central constraint recorded on 2026-08-20** — that Fusion has no headless mode and the model must write scripts for a human to run, requiring a custom watcher add-in. **That add-in should never be built.**

### What it actually provides
Tools: `fusion_mcp_execute`, `fusion_mcp_read`, `fusion_mcp_update`, `fusion_mcp_electronics_read`. `execute` runs Python **in the live Fusion session** and returns stdout *and the real traceback* — precisely the feedback loop the add-in was for, with nothing installed into Fusion. Fusion's own docs explicitly say **do not catch exceptions**, because the traceback is what lets the model fix itself.

### Verified end to end
Built `bridge/fusion_mcp.py` (client) and `bridge/fusion_loop.py` (local model → Fusion loop with numeric verification + screenshot). The 7B built the 12-member base frame **first attempt**: 24.0000 × 20.0000 × 18.0000 in, volume 232.0000 in³, one body — matching the CadQuery analytical value exactly. Screenshot captured through MCP.

### Protocol gotchas (each cost real time)
- Handshake needs `initialize` **then** `notifications/initialized`. Without the second, everything returns "Session not initialized" even though `initialize` returned 200. Session id arrives in the `MCP-Session-Id` **response header**.
- `Read` uses `queryType`; `Execute` uses `featureType`. `searchPattern` is **top-level**, not nested under `object`.
- Screenshots come back as MCP `image` content (base64), so a text-only content extractor silently returns nothing.
- `rootComponent.name` cannot be set — raises.

### The bug worth remembering: I blamed the model for my own harness fault
For six attempts the loop reported the frame as 55 × 38 × 18 with volume ~36,900 in³, and I attributed it to the 7B's spatial reasoning. **It was my clear-between-attempts step.** In a *parametric* design, `bRepBodies.deleteMe()` reports success but the timeline regenerates the bodies, so every attempt was measured against stale geometry. Switching to a fresh document per attempt (and `DirectDesignType`) made it pass **first try**. The model had been correct the whole time.

**Lesson: when a measurement is suspiciously constant across attempts (55/38/18 every single time, while the model's own printed output said 24/20/18), suspect the harness, not the model.** Varying input with invariant output is a harness signature.

### Still open
`apiDocumentation` returns `{"success": true}` with no payload for every pattern and category tried. If it worked it would directly fix the API-hallucination failure mode — worth revisiting on a Fusion update.

---

## 2026-08-27 — bncad: the headless framework, and the units bug that would have shipped

Built `bncad/`, a framework that turns a JSON part spec into a validated solid
using a local model, headless, with Fusion as the finisher. 42 tests, six part
specs, both LM Studio and Ollama, end-to-end verified into a live Fusion session.

### The architecture question is settled
CadQuery is the workhorse; Fusion is the finisher. Fusion has no headless mode,
its MCP server exists only while the app is up and signed in, and it crashed
under a sustained render batch on this 16 GB laptop the day before. CadQuery
builds unattended; Fusion receives the STEP and independently confirms it.

### The units bug — the most important find
**CadQuery always writes `SI_UNIT(.MILLI.,.METRE.)` into a STEP.** There is no
exporter option for it, and setting OCCT's `write.step.unit` does nothing at all
(it reads back empty and the output is unchanged). A part authored with the
numbers 4.0 × 1.5 × 0.25 inches therefore describes 4.0 × 1.5 × 0.25
**millimetres** to every correct reader.

This was invisible until the very first Fusion handoff. A C-01 anchor plate that
had passed every geometric check imported into Fusion as **0.157 × 0.059 ×
0.010 in** — 25.4× too small. CadQuery was right about the geometry the whole
time; the file lied about its units. A supplier's CAM would have read it exactly
the same way, and every internal check would still have been green.

Fixed by separating authoring from delivery: the model authors in the spec's
units, bncad scales to real millimetres before anything is measured, and
`measure(..., scale=25.4)` returns inches so checks compare like with like. **The
file that is validated is now the file that leaves the building.** After the fix,
Fusion reports 4.0000 × 1.5000 × 0.2500 in, volume 1.4417 in³ — agreeing with
CadQuery to four decimals.

**Lesson: a geometry check that never leaves its own kernel cannot catch a units
error. The cross-kernel import was the only thing that could have found this,
and it found it on the first try.** Worth running the Fusion cross-check on any
new part class, not just when something feels wrong.

### Two more harness faults I nearly blamed on the model
- **A relative `--out` doubled the script path.** The generated script runs with
  `cwd` set to its own work directory, so a relative output path resolved against
  that directory. The loop fed the resulting "can't open file" back to the model
  as though the model had written it, and burned six attempts over 36 minutes.
  Fixed by resolving `outdir`, and by refusing to spend attempts on errors whose
  text identifies them as ours (`_is_our_fault`).
- **The sandbox leaked through the system temp root.** The profile allowed
  writes to `/private/var/folders` so the interpreter had somewhere for temp
  files; the test suite escaped through it within a minute of being written. The
  child now gets a `TMPDIR` inside its own run directory and the broad grant is
  gone. *The test caught this, not review.*

This is the same shape as the 2026-08-21 lesson recorded above: when a run fails
identically over and over, suspect the harness.

### Prompt iteration is measurable, and worth doing
`P06-l-bracket` (an L of two legs with holes on two axes) failed on every model.
Three evidence-driven prompt changes moved it:

1. **Round-part pattern.** The model built a filleted *square* for a disc — same
   bounding box, wrong volume. It had no cylinder example, so it copied the
   nearest one. Adding `.circle()/.extrude()` fixed the spacer immediately.
2. **Selector cheat-sheet.** `.faces("|Z")` selects *every* Z-parallel face and
   `.workplane()` on that set raises "Selected faces must be co-planar". `>Z` is
   the single top face. This alone took P06 from "never executes" to "produces
   geometry".
3. **Build boxes on XY and translate.** `box()` takes world axes, so building on
   a `YZ` workplane does not rotate the box — it just makes the arguments mean
   something else, and one axis comes out wrong.

After all three, the 7B produced a correct bounding box with volume 0.9% off and
one of two holes. Still a fail, but it is now a capability ceiling rather than a
harness gap — which is what a benchmark part is for. A suite where everything
passes measures nothing.

### Benchmark: the 14B is starved, not weak
Six parts, 16 GB M1 Pro. 7B: **5/6, median 28 s**. 14B: **5/6, median 933 s** —
identical accuracy, roughly 33× the wall clock. 8.33 GB of weights on a machine
that lets the GPU address about 11 GB leaves nothing spare.

**This is a RAM finding for Mac Mini Setup, not a model finding.** Do not
conclude the 14B is a poor CAD model; conclude this laptop cannot feed it. Re-run
`bncad bench` on the mini before choosing anything.

### Fusion, confirmed again
The MCP port was **27180**, not the documented 27182 — the second time. Also
learned that Fusion does not return script stdout verbatim: it wraps it in
`{"message": "...", "success": true}`, so a parser looking for a line that
*starts with* a marker finds nothing while the answer sits inside the envelope.
And Fusion lives at `~/Library/Application Support/Autodesk/webdeploy/production/`,
**not** `/Applications` — looking there and concluding "not installed" is the
standard wrong turn.

### The audit that found what the tests could not (2026-08-27, later)

Ran five independent review lenses over the finished package — geometry, sandbox
security, loop control flow, portability, and docs-vs-code — then verified every
claim against the source by hand rather than trusting the reviewers. Fourteen
real defects, in code that already had a green 47-check suite.

The pattern worth keeping: **the tests were green because they tested what I had
thought of.** Every one of these was in the gap between "the function works" and
"the system behaves":

- **`_is_our_fault` was the inverse of itself.** Added that morning to stop the
  loop blaming the model for a harness bug, it matched the bare string
  `"No such file or directory: "` — which is what the *model's* own
  `FileNotFoundError` says when it exports into a directory it never created.
  So the guard against blaming the model for our bug started aborting whole
  builds by blaming us for the model's. The interpreter's own message is
  `can't open file '<path>'`; that distinctive half is what to match.
- **`bncad bench` exited 0 having benchmarked nothing.** `passed == len(board)`
  is true when both are zero, so a mistyped `--spec` reported success. A gate
  that passes when it did no work is worse than no gate.
- **`bench` ignored `BN_MODEL`** — which is exactly how `build.sh parts` passes
  the configured reviewer, so the documented Mac mini instructions did not work.
- **`build.sh parts` called `preflight revision`**, so the `parts` scope written
  for it (venv, bncad, sandbox) was never once invoked.
- **The fence regex was case-sensitive.** A model writing ```` ```Python ````
  matched nothing, the whole reply fell through as "code", and it came back to
  the model as a syntax error against text it had never written.
- **The escalated temperature never came back down.** One stuck episode on
  attempt 2 pinned every later attempt at 0.90 regardless of `--temperature`.
- **`finish_reason` was dropped**, so a reply truncated at the token limit
  reached the model as "your code does not parse".
- **A failed run left the previous run's passing STEP in place** with nothing
  marking it stale.
- **`checks["bbox_min"]` collided with `measure()["bbox_min"]`** and meant the
  opposite thing — minimum *size* versus minimum *corner coordinate*. Renamed to
  `size_min`/`size_max` before anyone pasted a measurement into a spec and got a
  check that silently passed everything.
- **`loop.build()` had no test at all.** Fixed with a fake provider that returns
  a canned script, and the key assertion is that the delivered file measures
  101.6mm rather than 4.0 — i.e. that the *millimetre* file was promoted, not the
  authored one. Mutation-tested: swapping those two arguments turns the suite
  red, and nothing else in it notices.
- **Two checks self-skipped and were tallied as passes**, so a green run on a
  machine with no venv and no model server verified less than it claimed.
  They now report SKIP.

And one I introduced *while fixing another*: making `preflight.py` read the
project folder from config left `config` out of scope in `resolve_fusion_url`,
where a deliberately broad `except Exception` would have swallowed the NameError
and silently returned the default MCP port — quietly undoing the port discovery
that cost two hours to learn was necessary. Passing `config` in explicitly, with
a comment saying why, was the fix.

**Lesson: a broad `except` around a lookup turns a scoping bug into a silent
wrong answer.** Fusion's port discovery is exactly where that is most expensive.

### Model class beats model size, decisively

qwen3:8b through Ollama is a *general reasoning* model and it is bad at this:
it imported `FreeCAD`, `FreeCADGui` and `Part`, invented
`fillet(0.5, segments=4)`, and returned unparseable output — on parts the
smaller qwen2.5-**coder**-7b builds first try. It cleared only the trivial
spacer.

**Do not pick the mini's model on parameter count or reasoning ability.** A 7B
dedicated coding model beat an 8B reasoner outright here. Run `bncad bench`
before believing anything else.

The AST guard earned its place in this: the FreeCAD hallucination came back as
"`import FreeCAD` is not permitted. Use only OCP, cadquery, json, math", which is
a message the model can act on, rather than an import traceback from inside a
sandbox.

### The correction: the prompt was the ceiling, not the model

Late in the day, with memory free and the three prompt rules in place, the 14B
built **P06-l-bracket 3/4 and C-02-U 4/4, first attempt, in about 30 seconds
each** - the same P06 that had failed 0/2 on the 7B and 6/6 on the 14B earlier,
and that I had already written up as a capability ceiling.

Two things I had concluded were wrong:

1. **"P06 is a model capability ceiling."** It was a prompt gap. The selector
   cheat-sheet (`>Z` is one face, `|Z` is a set), the cut-a-positioned-cylinder
   pattern for holes off the top face, and "build every box on XY and translate"
   were the difference. All three came from reading actual failures.
2. **"The 14B is accurate but ~33x slower here."** The 933s median was memory
   starvation, not the model. With nothing else resident it runs at **29-51s** -
   a 20-30x swing from available RAM alone, and it is then both the faster and
   the more accurate choice.

**Lesson: measure under the conditions you will actually run in, and say what
those conditions were.** The first sweep was honest about its numbers and wrong
about their cause, because I did not record that memory was contended. The
benchmark table now leads with the conditions column.

**Second lesson: a single run is a coin toss dressed as a result.** C-02-U passes
1/2 on the 7B; P06 passes 3/4 on the 14B. One run reports either as a clean yes
or a clean no, and both readings are wrong. `bncad bench --repeat N` prints the
pass *rate* and flags anything between 0 and N as marginal.

---

## 2026-08-27 (evening) — making it survive a machine nobody is watching

Triple-checked the stack against the conditions a Mac mini actually imposes,
rather than the ones a login shell does. Every defect below was **reproduced
before it was fixed**, and the reproduction is now a test.

### The four that only appear when nobody is looking

1. **`lsof` is not on a cron PATH.** It lives in `/usr/sbin`. Fusion's
   port-discovery fallback called it by bare name, so under a scheduled run it
   silently found nothing — re-creating the exact moved-port bug that cost two
   hours in the first place, but only where nobody would see it. Absolute path
   now, asserted in the demo.

2. **A relative interpreter path** fails as `execvp() ... No such file or
   directory`, because the child runs with `cwd` set to its work directory. The
   loop fed that to the model as though the model had written bad code.

3. **`Path.resolve()` on a venv interpreter leaves the venv.** Found while
   fixing 2. A uv venv's `bin/python` is a **symlink to the base interpreter**,
   so resolving it silently drops out of the environment and every
   `import cadquery` becomes `ModuleNotFoundError` — which reads as a broken
   install, not a lost venv. **`abspath`, never `resolve`, for an interpreter.**

4. **Overlapping builds destroyed each other.** Two builds of the same part share
   `_work-<id>`, which `build()` clears on entry, so the second deleted the
   first's files and the first died with `FileNotFoundError`. Reproduced
   deliberately with two threads and a slow fake model.

### The lock, and why the second version is much smaller than the first

My first fix wrote a pid into a lock file and "took over" when that pid looked
dead. An audit found a race in it, and checking the code confirmed three
separate problems, all of which only bite on a machine that runs for months:

- two processes could both judge a lock stale, and the second would then unlink
  the first's **live** lock;
- a **recycled pid** made a dead lock look alive forever, wedging that part;
- SIGKILL, a panic or a reboot left a file nothing would ever clear.

Replaced with **`flock`**. The kernel owns the lock and releases it when the
process dies, however it dies. That deleted `_pid_alive`, `_pid_start`, the
takeover loop and the corrupt-lock handling — the correct version is
substantially *less* code than the buggy one.

**Lesson: when a fix needs stale detection, liveness checks and takeover logic,
look for the primitive that makes all three unnecessary.** Reaching for the OS
here was both safer and shorter.

### On trusting an audit

Two workflow audits hit the session limit mid-run. The first reported
`confirmed: []` — which looked like a clean bill of health and was nothing of
the kind: three of five review lenses never ran, and my own scoring treated a
*failed* refuter agent's null result as a refutation. **A verification step that
cannot distinguish "disproved" from "did not run" will report silence as
success.** The second script separates `confirmed`, `refuted` and
`unverified_check_these_by_hand`.

Every finding I acted on was verified by reading the code myself first. Two of
the five lock findings were already fixed; three were real.

### What is now bounded, and measured

- **Disk**: deliverables are overwritten by exact name, so nightly runs of the
  same parts hold constant (measured across five consecutive runs: same file
  count, same 140 KB).
- **The run JSON**: ~2.7 KB at two attempts, ~8 KB at six. Capped by
  `--attempts`, not by uptime.
- **Time**: model calls and sandboxed scripts both time out for real — verified
  against a server that accepts a connection and never answers. Worst case per
  part is `attempts × timeout`.

### Exit codes, so a scheduler can branch without parsing prose

`0` success · `1` did not meet spec · `2` configuration · `3` busy. `3` is
deliberately not `1`: a scheduled run that met a manual one has not failed, it
has declined to race. `bench` re-raises rather than recording a phantom failure
against a model for a part it never built.

### The audit lens that mattered most: "can a wrong part ship?"

Three gates did not exist, and each was **measured and thrown away**:

- **A misspelled check key silently deleted that gate.** A spec written with
  `volumne` and `hole` passed a solid of 99 in³ with **no holes at all**,
  reporting zero errors. An ignored key is an ignored gate; unknown keys are now
  refused at load, by name.
- **Hole POSITION was never checked.** Two holes of the right diameter in the
  wrong place change volume by exactly zero, leave the bounding box untouched
  and satisfy `holes_exact` — a mirrored or mis-spaced bolt pattern was
  invisible to every gate. The coordinates were already written in each spec's
  `notes` and shown to the model. They were simply never verified. On a product
  whose open blocker is a bolt pattern.
- **Hole DEPTH likewise.** A blind hole is still an internal 360° cylinder of
  the right diameter, and one of them hides inside a typical volume tolerance.

Specs now take `at` and either `through` or an explicit `depth`, and
`bncad reference` emits them so a spec written the documented way carries the
check instead of never having one.

**`through` has a real limit, found immediately:** it compares depth to the
bounding box along the hole's axis, so it only means anything where the material
is uniform along it. On the L-bracket the bbox is the whole part, and a perfectly
good hole through a 0.25in leg read as blind. That part uses an explicit depth.

**Lesson: measuring a property is not checking it.** `_holes()` had returned
`at`, `depth` and `axis` from the first version, and a test even asserted the
positions came back correctly — while `check()` never looked at any of them. The
gap between "the measurement is right" and "the measurement is enforced" is
invisible in a green suite.

### The orphan

A subprocess timeout only holds while the parent lives. SIGKILL the loop during
a build and the sandboxed child is orphaned at 100% CPU **forever** — verified.
Fixed by having the child set `ulimit -t` for itself before exec, so the kernel
stops it regardless. `sh` applies the limit and execs, which sidesteps
`preexec_fn` and its thread-safety caveat.

### Setup day would have failed

Two of the four model ids `runtime.json` names were **in no RAM profile at
all**, so a freshly bootstrapped mini would download its roster and then have
preflight block on models nothing had fetched. And the documented next step was
`uv venv …` on a machine with neither uv nor a system python3.12. Fusion had no
install, sign-in or MCP-toggle step anywhere — only a RAM-sizing mention. All
now in `Setup-Checklist.md` §7d, in the order that was actually tested.

### Where P06 actually lands

Across every run today on the 14B, `P06-l-bracket` passed **5 of 7**. It is
genuinely marginal, not solved and not impossible — which is what a benchmark
part is for. Everything else builds first try in about thirty seconds.
