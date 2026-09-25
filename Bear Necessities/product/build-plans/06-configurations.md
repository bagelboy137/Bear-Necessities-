# 06 — Configurations: how modules combine in a vehicle

Six module combinations, each checked by the project's placement solver against
real (sourced) vehicle cargo envelopes. Generated 2026-08-26 from
`config_solver.py`; every row here is solver output, not an assertion.

> **What the solver checks:** envelope fit including the wheel-well pinch, module
> overlap, stack support, top-opening headroom, and whether anything blocks a
> front-opening module from the tailgate.
>
> **What it does NOT check:** payload (all module masses are unverified — it
> refuses to return a load figure), centre of gravity, whether the arrangement
> can actually be restrained (that's the undesigned C-02 question), and whether
> a person can reach the rear module of a deep stack.

---

## The arithmetic that decides everything

One module is **24 W × 20 D × 18 H in**.

| Arrangement | Dimension | Fits an SUV? |
|---|---|---|
| Two side by side, unrotated | 48 in wide | No — a 4Runner is 40–43 in between the wheel wells |
| Two side by side, **rotated 90°** | 40 in wide | Yes, barely, in a 5th-gen 4Runner |
| Two stacked | 36 in tall | No — a 4Runner is ~29.5–31 in floor to ceiling |
| One module | 18 in tall | Yes, ~11.5–13 in headroom left |

**Rotating a module 90° is what makes two-across possible in an SUV.** It costs
4 in of width and buys the second module.

## The headroom ceiling

An 18 in module in a ~31 in bay leaves ~13 in (5th-gen 4Runner) or ~11.5 in
(6th-gen). Anything that opens upward has to fit its lid/tray/worktop in that gap:

| Module | Needs above it | 4Runner 5th (~13 in) | 4Runner 6th (~11.5 in) |
|---|---|---|---|
| BN-M01 Cook | ~10 in | fits | fits |
| BN-M04 Sink | ~12 in | fits | **does not fit** |
| BN-M03 Fridge | ~14 in | **does not fit** | **does not fit** |
| BN-M09 Field Office | ~14 in | **does not fit** | **does not fit** |

BN-M03 and BN-M09 are **van / truck class** for this reason.

---

## What fits which vehicle

| Vehicle | Bay W × D × H (in) | Between wells | Max modules |
|---|---|---|---:|
| Toyota 4Runner 5th gen | 47 × 59 × 31 | 43 | **2** |
| Toyota 4Runner 6th gen | 45 × 59 × 29.5 | 40 | **2** |
| Ford Transit (low roof) | 54.8 × 100 × 56.9 | 54.8 | **5+** |
| Mercedes Sprinter | 53.1 × 100 × 68 | 53.1 | **5+** |
| Bronco, Wrangler, Tacoma, Outback | — | — | **unverified — the solver refuses to answer** |

Every sourced figure has a URL and date in the project's
`VEHICLE-ENVELOPES.json`, but **several fields inside those entries are still
marked unverified** — wheel-well heights are assumed, van floor lengths are
conservative placeholders. Treat this as design guidance, not as measurements to
cut anything against. Measure your own vehicle with the project's
`MEASUREMENT-WORKSHEET.md` before committing.

---

## The six named configurations

All solver-validated. The "fits" column is exactly the set the solver found a
valid arrangement for.

| Configuration | Modules | Fits |
|---|---|---|
| **Weekend Base** | Cook (M01) + Fresh Water (M05) | 4Runner 5th, 4Runner 6th, Transit, Sprinter |
| **Trail Kitchen** | Cook (M01) + Dry Pantry (M02) | 4Runner 5th, 4Runner 6th, Transit, Sprinter |
| **Recovery Day** | Dry Pantry (M02) + Recovery (M06) | 4Runner 5th, 4Runner 6th, Transit, Sprinter |
| **Wash Up** | Cook (M01) + Sink (M04) | 4Runner 5th, Transit, Sprinter |
| **Basecamp** | Cook (M01) + Pantry (M02) + Fridge (M03) + Water (M05) | Transit, Sprinter |
| **Expedition** | Cook (M01) + Pantry (M02) + Recovery (M06) + Hot Water (M08) + Furniture (M10) | Transit, Sprinter |

Renders of each are in `product/marketing/configurations/` in the project (not
bundled in this pack — they're marketing assets).

**Example placement — Weekend Base in a 5th-gen 4Runner** (origin at the tailgate
edge, both modules rotated 90° so each footprint is 20 × 24 in):

```
BN-M01 Cook  @ (0, 0, 0)     footprint 20 x 24, rotated
BN-M05 Water @ (20, 0, 0)    footprint 20 x 24, rotated
```

**Example placement — Basecamp in a Transit** (origin at the tailgate edge,
driver side, +y forward):

```
BN-M01 @ (0,0,0)   BN-M02 @ (24,0,0)   BN-M03 @ (0,20,0)   BN-M05 @ (24,0,18)
```

---

## The practical takeaway

The product story is **a chosen subset per trip, not a full stack**. An SUV
holds two modules; a van holds five or more. Design your build around 2–4
modules unless you're in a van. And re-confirm any of this against your own
vehicle's real measurements — the envelopes here are good enough to design with
and not good enough to cut a vehicle bracket against.
