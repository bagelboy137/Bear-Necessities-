# Eval Set — Fusion CAD Agent

Fixed prompts, easy → hard. Do not edit these once scoring has started; changing the test invalidates comparison between models.

---

### 1. Smoke test — flat plate
> Write a Fusion Python API script that creates a 100 × 60 × 6 mm rectangular plate.

Checks: `run(context)` present, cm-vs-mm conversion correct, sketch→extrude works at all.

---

### 2. Hole placement
> Add four 8 mm through-holes to that plate, one 10 mm in from each corner, measured to hole centre.

Checks: coordinate arithmetic, cut operation, whether it re-sketches on the right plane.

---

### 3. Parametric edit
> Rewrite it so length, width, thickness, hole diameter and corner inset are named Fusion user parameters editable in the UI after the script runs.

Checks: knowledge of `design.userParameters` — a genuine API-specific test that Python fluency alone won't pass.

---

### 4. Fillets and a real feature tree
> Add a 5 mm fillet to all four vertical corner edges, leaving the hole edges sharp.

Checks: edge selection — the hardest thing to get right generatively, since it needs reasoning about which BRep edges to collect rather than a formula.

---

### 5. L-bracket
> Model a 90° L-bracket: 80 mm × 60 mm legs, 5 mm thick, 40 mm wide, with two 6 mm holes per leg and a triangular gusset between them.

Checks: multi-feature part, planes other than XY, whether it can hold a whole part in its head at once.

---

### 6. Export
> Extend the previous script to export the result as both STEP and STL into a given folder path.

Checks: `exportManager` — very commonly hallucinated.

---

### 7. Error recovery
> *(Feed it the traceback from whichever task above failed.)* This script failed with the following error. Fix it.

Checks: the single most important capability for unattended operation. A model that iterates from tracebacks is usable even if its first pass is poor; one that can't is not usable at all.

---

### 8. Underspecified brief
> Model a bracket to mount a 12 V air compressor to a flat surface.

Checks: does it state assumptions and build something, or stall / invent silently. The rules file requires: assume, note the assumption in a comment, build.

---

### Control tasks
Repeat **1, 5, and 6** asking for **OpenSCAD**, then again for **CadQuery**. Compare scores against the Fusion API runs. If the neutral formats win clearly, change the architecture.
