# Deployed configurations — how the modules combine in a vehicle

Generated 2026-08-26 from `config_solver.py`. Every claim here is solver output,
not an assertion. Re-check with `python3 config_solver.py --validate-all`.

## The arithmetic that decides everything

One module is **24 W × 20 D × 18 H inches**. Therefore:

| Arrangement | Dimension | Fits an SUV? |
|---|---|---|
| Two side by side, unrotated | 48 in wide | No — a 4Runner is 40–43 in between the wheel wells |
| Two side by side, **rotated 90°** | 40 in wide | Yes, barely, in a 5th-gen 4Runner |
| Two stacked | 36 in tall | No — a 4Runner is 29.5–31 in floor to ceiling |
| One module | 18 in tall | Yes, leaving 11.5–13 in of headroom |

**Rotating the module 90° is what makes two-across possible in an SUV.** It costs
4 inches of width and buys the second module. That is the single most useful thing
the solver found.

## The headroom ceiling — the finding that changes the product

An 18-inch module in a 31-inch bay leaves **13 inches**. In a 6th-gen 4Runner
(29.5 in) it leaves **11.5 inches**. Every module that opens upward has to fit its
lid, tray or worktop inside that.

| Module | Needs above it | 4Runner 5th (13 in) | 4Runner 6th (11.5 in) |
|---|---|---|---|
| BN-M01 Cook | 10 in | fits | fits |
| BN-M04 Sink | 12 in | fits | **does not fit** |
| BN-M03 Fridge | 14 in | **does not fit** | **does not fit** |
| BN-M09 Field Office | 14 in | **does not fit** | **does not fit** |

**BN-M03, the fridge, does not fit any 4Runner measured.** Not "is tight" — the
solver rejects every placement, in both generations, on lid clearance alone. Same
for BN-M09. That is a product decision waiting to happen, and it has three possible
answers:

1. Reduce the module height below 18 in — breaks the family's defining dimension
   and the 8 × 18 in cut list. Expensive.
2. Change BN-M03 to a front-opening fridge — changes the primary component, and
   the whole point of a chest fridge is that cold air does not fall out.
3. Accept that BN-M03 and BN-M09 are van- and truck-class modules, and say so on
   the product page. Cheapest, and honest.

Nothing in this plan decides that. It is Conor's call, and it belongs next to the
C-02 decision.

## What actually fits

| Vehicle | Status | Bay (W × D × H) | Between wells | Max modules |
|---|---|---|---|---|
| Toyota 4Runner 5th gen | sourced | 47 × 59 × 31 | 43 | **2** |
| Toyota 4Runner 6th gen | sourced | 45 × 59 × 29.5 | 40 | **2** |
| Ford Transit low roof | sourced | 54.8 × 100 × 56.9 | 54.8 | **5+** |
| Mercedes Sprinter | sourced | 53.1 × 100 × 68 | 53.1 | **5+** |
| Bronco, Wrangler, Tacoma, Outback | **UNVERIFIED** | — | — | solver refuses to answer |

Every sourced figure carries a URL and a date in `VEHICLE-ENVELOPES.json`, and
several individual fields inside those entries are still marked UNVERIFIED — the
wheel-well heights are assumed, and the van floor lengths are deliberately
conservative placeholders. Treat the table as design guidance, not as measurements
to cut a bracket against. `C-02-vehicle-queue.json` makes that rule explicit and it
applies here unchanged.

## The named configurations

All six are solver-validated. The vehicle list is exactly the set the solver found
a valid arrangement for.

| Configuration | Modules | Fits |
|---|---|---|
| **Weekend Base** | Cook + Fresh Water | 4Runner 5th, 4Runner 6th, Transit, Sprinter |
| **Trail Kitchen** | Cook + Dry Pantry | 4Runner 5th, 4Runner 6th, Transit, Sprinter |
| **Recovery Day** | Pantry + Recovery | 4Runner 5th, 4Runner 6th, Transit, Sprinter |
| **Wash Up** | Cook + Sink | 4Runner 5th, Transit, Sprinter |
| **Basecamp** | Cook + Pantry + Fridge + Water | Transit, Sprinter |
| **Expedition** | Cook + Pantry + Recovery + Hot Water + Furniture | Transit, Sprinter |

Example placement, Basecamp in a Transit — origin at the tailgate edge, driver side,
`+y` forward:

```
BN-M01 @ (0,0,0)   BN-M02 @ (24,0,0)   BN-M03 @ (0,20,0)   BN-M05 @ (24,0,18)
```

## What the solver checks, and what it does not

Checks: envelope fit including the wheel-well pinch, module overlap, stack support,
top-opening headroom, and whether anything sits between a front-opening module and
the tailgate.

Does **not** check, and will say so rather than guess:

- **Payload.** Every module mass in `module-deployment.json` is `UNVERIFIED`, so
  `payload_note()` refuses to return a load figure. Populate the masses before
  quoting one.
- **Centre of gravity and load distribution.** Not modelled at all.
- **Restraint.** Whether the arrangement can actually be tied down is the C-02
  question, and it is still open.
- **Reach.** Whether a human can operate the rear module of a deep van stack.

## Reproducing

```bash
python3 config_solver.py --vehicle 4runner-5th --set M01,M03 --explain
```

`--explain` prints the rejection reasons with counts, which is the fastest way to
see *why* something does not fit rather than just that it does not.
