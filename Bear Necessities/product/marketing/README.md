# Marketing image set — ten modules + six configurations

Generated 2026-08-26. **These are ours** — unlike `../reference/competitors/`, this
folder is safe to publish, commit, and put on the website.

Open `index.html` to review the whole set:

```bash
open "$HOME/Claude/Bear Necessities/product/marketing/index.html"
```

## What these are, and what they are not

Every image here is composed from the **native Fusion CAD exports** — the same F3D
assemblies that pass the four deterministic gates. Nothing is illustrated, painted,
or AI-generated. If you see a burner, a strap, a drawer slide or a water tank in one
of these, it exists in the model with a part number behind it.

The presentation layer — background, contact shadow, brand type — is added by
`visual/make_module_cards.py`. It does presentation only and invents no geometry.

What they are *not*: photographs. There is no prototype yet, so there is no photo to
take. These read as clean studio CAD, which is the honest register for a pre-prototype
product — and it is the same register Goose Gear uses for its module pages.

## Contents

### `modules/` — 10 modules × 3 files

| File | Size | Use |
|---|---|---|
| `BN-MXX-card.png` | 1600×1200 | Product page hero, 4:3 |
| `BN-MXX-square.png` | 1200×1200 | Site grid tiles, social |
| `BN-MXX-alpha.png` | 1240×1098 | Transparent cutout — compositing source |

The alphas are also the input to the configuration boards, so do not delete them.

| ID | Module | ID | Module |
|---|---|---|---|
| BN-M01 | Cook Station | BN-M06 | Recovery/Utility |
| BN-M02 | Dry Pantry | BN-M07 | Power Hub |
| BN-M03 | Fridge/Freezer | BN-M08 | Hot Water/Shower |
| BN-M04 | Sink/Wash | BN-M09 | Field Office/Camera |
| BN-M05 | Fresh Water | BN-M10 | Camp Furniture/Soft Goods |

Every module is 24" W × 20" D × 18" H.

### `configurations/` — 6 solver-validated boards

2400×1600 each. Plan view, side elevation, bay dimensions, and the real product
cutouts for the modules involved. Placements come from `config_solver.py` — none is
drawn by hand, and `configuration-render-report.json` carries the exact origins plus
a SHA-256 per image.

| Board | Modules | Class |
|---|---|---|
| `weekend-base.png` | M01 + M05 | SUV |
| `trail-kitchen.png` | M01 + M02 | SUV |
| `recovery-day.png` | M02 + M06 | SUV |
| `wash-up.png` | M01 + M04 | 5th-gen 4Runner or van — sink lid needs the headroom |
| `basecamp.png` | M01 + M02 + M03 + M05 | Van |
| `expedition.png` | M01 + M02 + M06 + M08 + M10 | Van |

The class column is not marketing copy — it comes from the deployment classification
in `OTS-AUDIT.md`. Keep it on the site; it is the honest constraint.

## Regenerating

```bash
cd "$HOME/Claude/Mac Mini Setup/tools/cad-product-agent/production/ten-modules"
"$HOME/Claude/Fusion CAD Agent/.venv-cq/bin/python3" visual/make_module_cards.py
"$HOME/Claude/Fusion CAD Agent/.venv-cq/bin/python3" configurations/render_configurations.py
```

Then re-copy both output folders here. `make_module_cards.py --selfcheck` verifies the
background keying still preserves interior highlights.

## Putting these on the website

The site currently ships placeholder CAD viewport captures at
`website/public/modules/BN-MXX.png`. Swapping in the squares is one command:

```bash
for i in 01 02 03 04 05 06 07 08 09 10; do cp "$HOME/Claude/Bear Necessities/product/marketing/modules/BN-M$i-square.png" "$HOME/Claude/Bear Necessities/website/public/modules/BN-M$i.png"; done
```

That has **not** been done — the website sync command refuses to publish until the
10-cycle/100-review ledger, the 40-image gate and a final confirmation all pass, and
that gate is Conor's to clear. The swap above only changes local files; publishing is
still a separate, gated step.

## Known limitation

The camera is identical across all ten modules — same angle, same distance. Good for
a comparison grid, repetitive as a set of individual hero images. A second camera
angle per module would fix it and needs Fusion, whose local render queue is wedged
(see `Memory.md`, 2026-08-26).
