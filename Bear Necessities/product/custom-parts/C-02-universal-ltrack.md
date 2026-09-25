# Part C-02-U: Universal Floor Bracket (L-Track)

**Purpose:** anchors a module to the vehicle floor. Mates with C-01 (module anchor plate) via a vertical quick-release pin dropped through both.
**Process:** laser cut from 1/4" (0.250") 5052-H32 aluminium sheet. Flat. No bends, no machining.
**Qty:** 2 per module.

## Why this exists — and why it may replace all 10 vehicle SKUs

Vehicle factory tie-down patterns are undocumented and differ by model, generation, trim and body style. Designing per vehicle means measuring every one, carrying 10+ SKUs, and still being wrong when a model year changes.

**L-track (airline track) is a published standard with a fixed 1.000" hole pitch.** Design to the standard instead of the vehicle:
- Factory cargo **Sprinters already ship with OEM L-track**
- For every other vehicle, L-track is cheap, off-the-shelf, and its vehicle-specific mounting is a solved problem someone else already sells
- **One SKU covers every vehicle**, and it never goes obsolete on a model refresh

Trade-off, stated plainly: it pushes an install step onto the customer. That is a real cost to the buying experience and is a product decision, not a CAD one.

## Geometry
- Overall plate: **6.000" long × 2.000" wide × 0.250" thick**
- **3 × L-track mounting holes**, Ø0.281" (clearance for 1/4-20), on the plate centreline at **−2.000", 0.000", +2.000"** from centre. 2.000" is exactly 2× the L-track 1.000" pitch, so the plate always lands on track holes.
- **1 × pin hole**, Ø0.266" (clearance for a 1/4" quick-release pin), on the centreline at **+1.000"** from centre, offset **0.625"** off the centreline in Y so it clears the mounting fasteners.
- **Corner radius 0.375"** on all four corners.

## Interfaces (must be exact)
| Feature | Dimension | Tolerance | Why |
|---|---|---|---|
| Mounting hole pitch | 2.000" | ±0.010" | must land on L-track 1.000" pitch |
| Mounting hole dia | 0.281" | +0.005/−0.000 | 1/4-20 clearance |
| Pin hole dia | 0.266" | +0.005/−0.000 | free fit on a 1/4" pin |
| Thickness | 0.250" | sheet tol | shear strength |

## Explicitly free
Outline styling beyond the stated radius, lightening cutouts, edge chamfer, any logo etch.

## Deliverable
STEP (3D) + **DXF of the flat profile** for laser quoting.

## Unresolved
Pin diameter and plate thickness are assumptions until a load case is defined. Worst case is presumably a fully loaded fridge module under hard braking — that number is not yet established, and it sets both the pin size and the plate thickness.
