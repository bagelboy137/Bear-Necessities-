# Eval Scores

Score 0–3 per task (see `../README.md`).
**3** runs + correct · **2** runs + wrong geometry · **1** errors but self-corrects from the traceback · **0** errors and cannot recover / hallucinates API methods

---

## qwen/qwen3.5-9b — general-purpose reasoning model (5.57 GiB loaded)
Run 2026-08-20 on M1 Pro 16GB. **Run only because the 14B coder could not be loaded** (see below). Not a coding model; included as a floor, not a fair test.

| # | Task | Score | Notes |
|---|---|---|---|
| 1 | plate (Fusion API) | **0** | 2m37s, no answer produced. Degenerate reasoning loop — emitted `Wait, createExtrude might take profile and direction and distance?` several hundred times until the token budget ran out. Output file empty. |
| C1 | plate (OpenSCAD control) | **0** | 1m54s, no answer produced. Same loop failure on a trivially easy task. |

**Verdict: unusable.** Confirms the quirk already recorded in `Mac Mini Setup/Memory.md` — this model burns its entire budget on hidden reasoning without answering.

**The control test is inconclusive.** Because it failed OpenSCAD *too*, the failure is the model, not the Fusion API specifically. The Fusion-API-vs-neutral-format question is still open and needs a competent model to answer.

---

## qwen/qwen2.5-coder-14b — BLOCKED, not yet run
Downloaded and registered (8.33 GB on disk). **Will not load on this machine as configured.**

```
Estimated GPU Memory:   10.86 GiB
Estimated Total Memory: 10.86 GiB
Error: Model loading was stopped due to insufficient system resources.
```

- The estimate is **10.86 GiB regardless of context length** (tested 3072 / 4096 / 6144 / 8192) — it is weights-dominated, so shrinking context does not help.
- Retried after unloading all other models. Still blocked.
- **The blocker is LM Studio's own resource guardrail, not the hardware.** 10.86 GiB against 16 GB total is exactly the ~70% GPU-addressable ceiling.

### To unblock (GUI only — cannot be done from the CLI)
LM Studio → **Settings → Hardware → Model Loading Guardrails** → set to **Relaxed** or **Off**, then:

```bash
lms load qwen/qwen2.5-coder-14b -c 8192 -y
```

Close other apps first. At 10.86 GiB on a 16 GB machine there is little headroom, and **Fusion cannot be open at the same time** — use the sequential workflow (generate → `lms unload --all` → run in Fusion).

---

## qwen2.5-coder-7b-instruct (MLX 4-bit, 4.00 GiB loaded, 8k ctx) — RAN
Pulled from Hugging Face (`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`) as a workaround for the blocked 14B. Loads in 8.17s, generates in ~24s/task. **A real code-specialised model, one tier below the 14B.**

### Fusion Python API
| # | Task | Score | Notes |
|---|---|---|---|
| 1 | plate | **0** | Fluent, plausible Python. Every Fusion-specific call wrong. Also a **10x unit error** — wrote `length = 100.0 # cm` for a 100 mm plate (should be 10.0), i.e. a 1-metre plate. |
| 5 | L-bracket | **0** | Same. Every feature call invented; no mm→cm conversion attempted at all. |

### OpenSCAD control — same model, same parts
| # | Task | Score | Notes |
|---|---|---|---|
| C1 | plate | **3** | `cube(size = [100, 60, 6]);` — correct, first try, no unit confusion. |
| C5 | L-bracket | **2** | Valid OpenSCAD that would render, but geometry wrong: no gusset, only one leg, holes unioned instead of subtracted. **Wrong but fixable by iteration** — a different class of failure from "won't run". |

### Verdict — this answers the open architecture question
**Generate-and-import beats direct Fusion API scripting, decisively, at this model size.**

The model writes fluent Python and simply does not know the Fusion API. Its failures there are *unrecoverable* — invented classes and method signatures, so nothing executes and there is no traceback to iterate from. In OpenSCAD its failures are *geometric* — the code runs, you see a wrong shape, and you can correct it.

Caveat: 7B is two tiers below what a 32GB mini would run, and API knowledge is exactly the kind of thing that improves with scale. This is strong evidence, not proof. Re-run both columns on the 14B (and later the 30B) before treating the Fusion-API path as closed.

Not verified: the OpenSCAD output was never rendered — OpenSCAD is not installed. Scores C1/C5 are from reading the code.

---

## Hallucinated API members seen
Populate as real runs happen. Feeds `../reference/fusion-api-notes.md`.

From qwen2.5-coder-7b-instruct. **Note it invents a *different* wrong answer each run** — `modelRoot.findItem("XY Plane")` on one task, `model.workplanes.itemByName("XY Plane")` on the next. It is not misremembering a fixed thing; it is generating plausible shapes on demand.

| Invented | Reality |
|---|---|
| `adsk.fusion.DesignManager.activeDesign` | no such class — use `adsk.fusion.Design.cast(app.activeProduct)` |
| `rootComp.modelRoot.findItem("XY Plane")` | no such member — use `rootComp.xYConstructionPlane` |
| `rootComp.model.workplanes.itemByName("XY Plane")` | no such member — same fix |
| `rootComp.features.sketchBasedFeatures.addExtrude(...)` | no such collection |
| `extrudeFeatures.add(profile, operation)` | must build a `createInput(...)` first, then `.add(input)` |
| `extrudeFeature.distance = ValueInput...` | not assignable — set extent on the input via `setDistanceExtent(False, ValueInput)` |
| `holeFeatures.add(profile, ValueInput, operation)` | wrong signature; holes need a `HoleFeatureInput` with a position |
| `context.application` | use `adsk.core.Application.get()` |
| `setDistanceExtent(ValueInput)` | needs the leading bool: `setDistanceExtent(False, ValueInput)` |

---

## qwen/qwen2.5-coder-14b (MLX 4-bit, **7.75 GiB actual**, 8k ctx) — RAN 2026-08-20
Unblocked by setting `modelLoadingGuardrails.mode` to `off` in `~/.lmstudio/apps/bionic/settings.json`.

**The guardrail was wrong.** It refused based on a **10.86 GiB estimate**; the model actually loads at **7.75 GiB** — a ~3 GiB over-estimate on a machine where 3 GiB is the difference between "works" and "blocked."

| # | Task | Score | Notes |
|---|---|---|---|
| 1 | plate (Fusion API) | **1** | Two bugs, both traceback-recoverable: `sketch.sketchLines` (needs `sketch.sketchCurves.sketchLines`) and a diagonal first line `(0,0)→(L,W)` that never closes the rectangle. |
| C5 | L-bracket (OpenSCAD) | **2** | Named variables as instructed, but **no `difference()`** — holes unioned instead of subtracted, same bug the 7B made. Legs do not form a proper L. |

### What the 14B got RIGHT that the 7B invented
- `adsk.core.Application.get()` · `app.activeProduct` · `rootComp.xYConstructionPlane`
- `extrudes.createInput(profile, operation)` → `setDistanceExtent(False, distance)` → `extrudes.add(input)` — **including the leading bool** the 7B omitted
- **Units.** `LENGTH = 10.0  # 100 mm`, `HEIGHT = 0.6  # 6 mm`. Correct mm→cm throughout. The 7B wrote `100.0 # cm` — a 1-metre plate.

Zero hallucinated API members. Every call above is real.

## REVISED VERDICT — the 7B result did not generalise

| | Fusion API | OpenSCAD |
|---|---|---|
| 7B | 0 | 3 / 2 |
| 14B | **1** | **2** |

**Fusion API improved sharply with scale (0 → 1, now two small bugs from working). OpenSCAD did not improve at all (2 → 2, identical union-instead-of-difference bug).**

The earlier "generate-and-import wins" conclusion was an artefact of testing at 7B, where the model simply did not know the Fusion API. At 14B that knowledge is largely there, and the remaining failure — **3D spatial reasoning** — hits *both* formats equally, so switching formats does not buy you anything.

**Do not abandon the Fusion API path.** The bottleneck moved from "doesn't know the API" to "can't reason about 3D space," and only the first of those is fixed by changing output format. Re-test at 30B on the mini, where the spatial reasoning should also improve.
