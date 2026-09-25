# Build status

Last verified: 2026-08-26 (Conor's laptop).

## What passes

- `validate_family.py` — 10 modules/jobs, 31 BOM rows, two cut lengths, clearance
  and BOM evidence. **PASS**
- `validate_jobs.py` — 10 unique jobs preserve frame/cut/component/release
  invariants. **PASS**
- Native geometry checks — bounding box within 0.01in of 24×20×18, twelve named
  frame members, 113 named components per module, required visible parts present,
  1600×1200 renders, OBJ materials, ten distinct F3D archives. **PASS**
- `mesh_integrity.py` — the ten exported STL deliverables: every body watertight,
  outward-facing normals, no degenerate facets, body count matching the job's cut
  list plus components, envelope within 0.01in of the declared frame. **PASS**

## What fails

Nothing. `validate_native_family.py` now returns **PASS** (10 modules, 10 distinct
F3D archives).

The provenance failures recorded here on 2026-08-25 —
`local_qwen_revision_evidence` and `ots_catalog_traceability`, 20 failures across
all ten modules — were closed by the revision sweep completing. This file went
stale between that fix landing and 2026-08-26; the gate was re-run on 2026-08-26
and passes.

### The bug that caused the original stall, kept for the record

The gate wanted 300 module reviews and the ledger had 10. The sweep stopped in
cycle `design-04` because module BN-M05's `acceptance_check` came back at 267
characters against a 240-character cap — and the failure message said only
"length/type invalid", so the model's repair attempt resampled instead of
shortening and came back two characters *longer*. One sentence, 27 characters
over, killed a 30-cycle run.

Fixed 2026-08-25: the limits are now stated in the prompt, the failure message
reports the measured length and how much to cut, and the attempt budget is
configurable.

## Re-running

```bash
cd "Bear Necessities/cad"
./build.sh validate      # all four deterministic gates, no model, no Fusion
./build.sh test          # framework suites (needs the CadQuery venv)
```

## Note on the evidence that was in the tree

The committed `native-validation-report.json` said `PASS` with zero failures. It
was genuine — but produced by an *earlier* validator that had only 7 checks per
module. The two provenance checks were added afterwards and the report was never
regenerated, so a tightened gate sat next to a stale green report.

The gate now stamps its own SHA-256 into every report it writes, and preflight
flags a report whose validator hash does not match the current file. The report
in the tree has been regenerated and now reads `FAIL` — which is the truth.

## Marketing render pipeline (added 2026-08-26)

`./build.sh visuals` drives Fusion's own ray tracer through
`production/ten-modules/visual/`. The deterministic image gate
(`visual_quality.py`) scores the legacy viewport captures at **0 of 20 passing**,
which is the point of it. BN-M01 and BN-M02 both reach **8 of 10** under the
current scene.

### The machine limit this hit

The pipeline **crashed Fusion on this laptop**. `adexmtsv` — the Autodesk
material-library service, which is exactly what appearances and render
environments go through — crashed at 14:03 on 2026-08-26 during a ten-module
render batch, a crash-report dialog fired at 14:34, and Fusion restarted at 15:46
without rebinding its MCP port. Two of ten modules had rendered.

This is the render-side sibling of the LM Studio kernel panics in
`LM-STUDIO-SAFE-PROFILES.md`: a 16 GB M1 Pro will run this workload, but not at
full tilt for an hour. Treat a ten-module × ten-cycle sweep as a Mac mini job.
Two further hazards, both now guarded in code:

- Fusion's MCP server stops answering **for the duration of a render** (curl
  returns 000, then 405 once the queue drains). Do not read that as Fusion having
  died. `render_module.py` takes a lock so two drivers cannot overlap.
- **Killing the driver does not cancel the renders.** Fusion finishes them
  minutes later and overwrites the files, long after the run looks dead. Wait for
  the render directory to go quiet before trusting anything in it.

## bncad part building (added 2026-08-27)

`./build.sh parts` builds parts from JSON specs with a local model, headless.
`./build.sh test` now also runs its 42-check suite, which needs no model, no
Fusion and no network.

**Passing:** the full self-test suite. Six specs, each validated against a reference
solid. Sandbox escape and network denial are proven by test, not asserted. The
full chain was verified into a live Fusion session: Fusion independently
measured a model-built C-01 at 4.0000 x 1.5000 x 0.2500in, volume 1.4417in^3 -
agreeing with CadQuery to four decimals.

**Benchmark, qwen2.5-coder-7b-instruct, two runs per part:**

| Part | Runs passed | Note |
|---|---|---|
| BN-FRAME-base | 2/2 | first attempt both times, ~28s |
| C-01-anchor-plate | 2/2 | two attempts both times |
| P01-plate | 2/2 | |
| P05-spacer | 2/2 | |
| C-02-U-floor-bracket | **1/2** | marginal - passes about half the time |
| P06-l-bracket | **0/2** | capability ceiling, see below |

Other models: **qwen/qwen2.5-coder-14b**, re-run later with memory free and the
improved prompt, builds **C-02-U 4/4 and P06 3/4 in about 30s each** - both parts
the 7B struggles with. Its earlier 933s median was memory starvation, not a
slower model. **ollama/qwen3:8b** managed 1 of 5 completed parts, importing
`FreeCAD` and inventing `fillet(segments=4)`; model *class* matters more here
than size or reasoning ability.

**All six parts are buildable.** The 7B is the right pick when something else
needs the RAM; the 14B is faster *and* more accurate when it does not.

**P06-l-bracket was not a capability ceiling after all.** It is an L of two legs
with holes on two different axes, and it failed 0/2 on the 7B and 6/6 on the 14B
under the original prompt. Three evidence-driven prompt rules - a selector
cheat-sheet, cut-a-positioned-cylinder for off-axis holes, and always build boxes
on XY and translate - took the 14B to 3/4, first attempt, ~31s. **The prompt was
the ceiling, not the model.** It remains marginal on the 14B and out of reach for
the 7B, which is what a benchmark part is for.

### The unit trap this found

**CadQuery stamps `SI_UNIT(.MILLI.,.METRE.)` into every STEP it writes.** An
inch-authored part therefore describes millimetres to every reader. A fully
validated C-01 imported into Fusion as **0.157 x 0.059 x 0.010in** - 25.4x too
small - and every internal check was still green, because the geometry was right
and only the file's declared units were wrong. A supplier's CAM would have read
it the same way.

bncad now converts to real millimetres before anything is measured, so the file
that is validated is the file that ships. Four tests guard it. **A geometry check
that never leaves its own kernel cannot catch a units error** - the Fusion
cross-check was the only thing that could have, and it did so on the first run.

## Still open (unchanged, and not CAD problems)

Load cases and safety factor, frame joinery selection, the C-02 vehicle anchor,
supplier drop-ship terms, custom panel drawings, and physical fit/load/vibration
testing. See `PRODUCTION-READINESS-AUDIT.md` in the study folder.
