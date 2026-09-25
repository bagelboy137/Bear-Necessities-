# Competitor reference — modular vehicle camp systems

Collected 2026-08-26 for private design reference.

**Copyright:** every image here is third-party product photography and remains the
property of the brand that shot it. Use it to inform BN designs and to argue about
proportions and mechanisms. **Do not** put any of it on the Bear Necessities website,
in a deck, or in anything published. The marketing render pipeline in
`../../../../Mac Mini Setup/tools/cad-product-agent/production/ten-modules/visual/`
exists to produce our own imagery for that.

Open `index.html` in a browser to review everything at once:

```bash
open "$HOME/Claude/Bear Necessities/product/reference/competitors/index.html"
```

Regenerate that page after adding or deleting images with `./make-index.sh`.

---

## The starting reference (Conor, 2026-08-26)

The Instagram photo Conor supplied is a Coastal Mountain Vanworks–style fridge
module: a **Dometic CFX chest fridge** carried on a **tilt/slide mount** with visible
gas-strut or lift arms, a **bamboo counter** above it, and a **drawer below**, all in a
black frame bolted to wall L-track.

That photo is not saved here — it arrived in chat, not as a file. Drop it in as
`_reference-conor-instagram.jpg` if you want it in the contact sheet.

The mechanism in it is the single most useful thing in this whole folder, so it gets
its own section below.

---

## The finding that matters: nobody reserves headroom above a chest fridge

BN-M03 and BN-M09 are currently classified van/truck-class because their top openings
need 14in of clear space above an 18in frame, and neither measured 4Runner has it
(`OTS-AUDIT.md`, `configurations/CONFIGURATIONS.md`).

**Every competitor here solves that by moving the fridge out of the bay instead of
reserving space above it.** Not one of them designs in overhead lid clearance:

| Brand | Mechanism |
|---|---|
| Coastal Mountain Vanworks | Fridge on lock-in/lock-out slides, cam-strapped; counter above lifts clear |
| Goose Gear | "Icebox 1/2 with top drawer" — fridge slides out from under a fixed deck |
| Tembo Tusk | Jumbo **side-pull** slide — fridge exits sideways out the rear door |
| Front Runner | Cargo/fridge slide tray, ~100% extension, mounts to any flat surface |
| Trail Kitchens | Galley with integrated fridge slide |

This is worth revisiting before accepting the van/truck-class classification as
final. A slide-out or tilt-out tray inside the existing 24×20×18 frame could pull
BN-M03 back into SUV class without breaking the family frame or swapping the chest
fridge — both of which `CLAUDE.md` explicitly forbids. It costs drawer-slide hardware
and rear-door swing clearance instead of vertical space.

Not a recommendation yet — it needs the fridge envelope checked against slide travel
and a real 4Runner tailgate measurement. But it's a route the current audit doesn't
consider.

## The second finding: Goose Gear's plate system is a third answer to C-02

C-02, the vehicle floor bracket, is framed in `CLAUDE.md` as a binary: ten per-vehicle
SKUs, or one universal L-track part that pushes an install step onto the customer.

Goose Gear ships a third shape. **One vehicle-specific "Plate System" per vehicle**, a
flat deck that bolts to that vehicle's factory tie-downs — and then *every* module in
their catalog is vehicle-agnostic and bolts to the plate. The per-vehicle engineering
is isolated in a single flat part; the modules never go obsolete.

That is very close to what BN already does well — flat plates cuttable from sheet —
and it means the per-vehicle part count is one plate, not one bracket per module per
vehicle. Adventure Wagon's L-track/A-frame system (also in this folder) is the
comparison case for the universal route.

---

## Brands captured

### coastal-mountain-vanworks
Closest competitor. Modular bolt-in cabinetry, extrusion frame with colored infill panels, bamboo tops, recessed round drawer pulls. Pullout cooler galley, powered cooler stand, 4-drawer galley, over-wheel water cabinet, drop-down outside table, countertop extension. — https://cmvanworks.com/campervan-products/

### goose-gear
The sharpest comp for SUV-class: modules sized to specific 4Runner generations. Flat cut-sheet panels with lightening holes, aluminum extrusion corners, per-vehicle rear plate system. Module footprints run 19in and 22in wide by 25/28/30/31.5in deep — BN's 24W × 20D is wider and much shallower. — https://www.goose-gear.com/

### trail-kitchens
Galley with integrated fridge slide, sink and faucet detailing. — https://trailkitchens.com/products/galley-with-fridge-slide

### adventure-wagon
The universal-mount thesis proven commercially: steel A-frame plus aluminum L-track, everything reconfigurable, sold as a DIY-installable kit. The comparison case for the C-02 L-track route. — https://adventurewagon.com/pages/interiorsystem

### alu-cab
Canopy camper and shadow awning; useful for opening-height and bamboo-surface detailing. — https://www.alu-cab.com/products/canopy-camper

### kanz-outdoors
Modular field kitchen with a leg system — the closest thing here to a free-standing deployed cook module. — https://kanzoutdoors.com/

### roam-adventure
Rugged cases with MOLLE panels, rigid mounts, and lid organizers. Reference for how a case-based system handles mounting and internal organization. — https://roamadventureco.com/

### tembo-tusk
Skottle cook system and the Jumbo **side-pull** fridge slide — the sideways-exit variant of the clearance solution. — https://tembotusk.com/

### drifta
Australian chuck-box / car-back camp kitchens. Thin capture — their site resisted scraping. — https://www.drifta.com.au/

---

## Gaps

Four brands could not be captured — their product pages are JavaScript-rendered and
returned only navigation chrome or 404s to a plain fetch:

- **Decked** (truck-bed drawer systems)
- **Front Runner Outfitters** (drawer systems, Wolf Pack, cargo/fridge slides)
- **Vandoit** (galley and storage modules)
- **BOXIO** (German bolt-together cube system — conceptually the closest of the four)

Front Runner's slide and BOXIO's cube stacking are the two worth going back for. They
need a real browser session rather than curl; say the word and I'll drive one.
