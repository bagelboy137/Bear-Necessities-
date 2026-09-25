# Fusion Python API — Notes & Patterns

Cached offline reference. **Everything here should be verified by actually running it** before the local model is told to rely on it — unverified entries are marked ⚠️.

## The shape of a script
A Fusion script is a **folder** under `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Scripts/<Name>/` containing:
- `<Name>.py` — must define `run(context)`
- `<Name>.manifest` — JSON metadata (see `scripts/_template/`)

Fusion picks up new script folders on restart, or via **Utilities → Scripts and Add-Ins → the green `+`**.

## Units — the single most common mistake
The API is **always in centimeters and radians**, independent of the document's display units.

| Intent | API value |
|---|---|
| 50 mm | `5.0` |
| 1 inch | `2.54` |
| 90° | `math.pi / 2` |

Write conversions explicitly: `MM = 0.1` then `plate_len = 120 * MM`.

## Canonical skeleton
See `scripts/_template/Template.py` — verified-to-run starting point. The core:

```python
import adsk.core, adsk.fusion, traceback

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        # ... build here ...
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
```

## Patterns to fill in (as they're verified)
- [ ] Sketch a rectangle on XY and extrude it
- [ ] Circles → hole features vs. cut-extrudes (which is more reliable to generate?)
- [ ] Fillet a selected edge set
- [ ] Named user parameters (`design.userParameters`) so dimensions are editable in the UI afterward
- [ ] Export STEP / STL via `design.exportManager`
- [ ] Create a new document vs. building into the active one — ⚠️ decide which the agent should do; building into whatever is open is dangerous unattended

## Known hazards
- ⚠️ **No headless mode on macOS.** Fusion must be running with a GUI session.
- ⚠️ `ui.messageBox` **blocks** waiting for a click. Fine when a human is present; it will hang an unattended run forever. The watcher add-in must log instead of message-box, or the agent's scripts must not call it.
- ⚠️ The embedded interpreter is Fusion's own CPython. Do **not** assume pip packages are importable.
- ⚠️ Fusion updates can change API behavior between versions. Two versions are cached on this machine (`2703.1.20`, `2704.1.36`).

## Confirmed hallucinations — do NOT use these (observed 2026-08-20, qwen2.5-coder-7b)
Local models invent these confidently. Every one fails at runtime.

| Invented | Reality |
|---|---|
| `adsk.fusion.DesignManager.activeDesign` | `adsk.fusion.Design.cast(app.activeProduct)` |
| `rootComp.modelRoot.findItem("XY Plane")` | `rootComp.xYConstructionPlane` |
| `rootComp.model.workplanes.itemByName("XY Plane")` | same fix |
| `rootComp.features.sketchBasedFeatures.addExtrude(...)` | no such collection |
| `extrudeFeatures.add(profile, operation)` | build `createInput(...)` first, then `.add(input)` |
| `extrudeFeature.distance = ValueInput...` | set extent on the *input*: `setDistanceExtent(False, ValueInput)` |
| `setDistanceExtent(ValueInput)` | needs the leading bool |
| `holeFeatures.add(profile, ValueInput, operation)` | holes need a `HoleFeatureInput` with a position |
| `context.application` | `adsk.core.Application.get()` |

**The model invents a different wrong answer each run** — two different fake ways to get the XY plane across two consecutive tasks. It is not misremembering a fixed API; it is generating plausible shapes on demand. Feeding it this table in the system prompt is worth testing as a mitigation.

## Alternative path — TESTED 2026-08-20, it wins at 7B
Model training data contains vastly more **OpenSCAD** and **CadQuery** than Fusion API code.

**Result:** the same model scored **0/0** on Fusion API tasks and **3/2** on the identical parts in OpenSCAD. The decisive difference is the *failure mode* — Fusion API output does not execute at all, so there is no traceback and no feedback loop, while OpenSCAD output runs and produces visibly wrong geometry you can iterate on.

Cost of switching: you lose Fusion's parametric feature tree. Re-test at 14B/30B before committing. See `../evals/results/SCORES.md`.
