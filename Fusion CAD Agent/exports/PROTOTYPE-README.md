# Prototype Drawing — Modular Overland Camp System, Base Frame

**Generated entirely by a local model** (`qwen2.5-coder-7b-instruct`, LM Studio, offline)
on 2026-08-20. No cloud AI wrote this geometry.

## Files
| File | What |
|---|---|
| `PROTOTYPE-overland-base-frame.dxf` | The drawing. **Opens directly in Fusion 360** (Insert → Insert DXF) |
| `PROTOTYPE-overland-base-frame.png` | Preview render |
| `../scripts/PROTOTYPE-overland-base-frame_gen.py` | The ezdxf script the model wrote |

## What it contains
Three orthographic views (front, top, right), labelled, plus a cut list.

**The cut list is correct and usable:**

| Member | Qty | Cut length |
|---|---|---|
| Vertical corner posts | 4 | 18.0" |
| Horizontal width members | 4 | 22.0" |
| Horizontal depth members | 4 | 18.0" |

That is a valid bill of materials for a 24 × 20 × 18" **outside** cube in 1010 (1" square)
extrusion, with horizontals fitting between the posts. 12 members total.

## Known defects — this is a prototype, not a production drawing
1. **View sizes are slightly off.** The right view renders ~22" wide; it should be 20" (depth). Front view is correct at 24 × 18".
2. **Not all 12 members are drawn.** Front and right show the vertical posts; the horizontal members and most of the top view are simplified or missing.
3. **Top view has a misaligned rectangle** — an artifact, not a real feature.
4. **No dimensions, tolerances, title block, or fastener callouts.**

Use it as a starting geometry to import and correct in Fusion, not as a shop drawing.

## Reproduce or improve
```bash
cd "Fusion CAD Agent"
python3 bridge/cad_loop.py --spec specs/overland-base-frame.md \
  --model qwen2.5-coder-7b-instruct --out-name overland-base-frame --max-attempts 20
```
The loop keeps the best attempt at `*-best.dxf` even when no attempt is fully clean.
