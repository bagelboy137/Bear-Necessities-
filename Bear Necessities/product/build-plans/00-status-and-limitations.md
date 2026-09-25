# 00 — Status and limitations

**This is the most important file in the pack.** Everything else assumes you have
read it. It is written to the same standard the project holds itself to: no
invented numbers, and every gap named rather than papered over.

---

## 1. The one-line summary

The **frame geometry and its catalog parts list are real and internally
verified**. The **frame joint design, every load rating, the vehicle mount, and
the module interiors are not** — they are concepts pending engineering and a
physical build that has not happened.

---

## 2. What is actually verified

| Item | Status | Evidence it traces to |
|---|---|---|
| Frame outside envelope 24 × 20 × 18 in | **Verified in CAD** | Ten native Fusion assemblies measured 24.0016 × 20.0016 × 18.0016 in, inside a 0.01 in concept tolerance. Deterministic geometry gates pass. |
| Two cut lengths only: 8 × 18 in + 4 × 22 in (12 members, 232 in / 19.33 ft total) | **Verified in CAD + BOM** | `bom-reconciliation-report.json` confirms 80 × 18 in and 40 × 22 in across the ten-module family (8 + 4 per frame). |
| Frame profile: 1 × 1 in "10 Series" T-slot extrusion | **Verified against vendor pages** | 80/20 part `1010-S`; TNUTZ `EX-1010` stated 100% compatible, cut to length from the product page in 1/16 in steps, ~48 h. Part numbers checked 2026-08-20 against 8020.net and tnutz.com. |
| Clear internal volume 22 × 18 × 16 in (1 in inset each face) | **Verified in CAD** | `clearance-report.json`, 0.125 in six-face free-clearance rule. |
| C-01 anchor plate geometry (4.000 × 1.500 × 0.250 in, hole pattern) | **Verified in CAD** | Built in CadQuery, independently re-measured in Autodesk Fusion at 4.0000 × 1.5000 × 0.2500 in, volume 1.4417 in³ — agrees to four decimals. |
| The ten module concepts exist as distinct CAD assemblies with renders | **Verified as concept models** | `DELIVERY-README.md`: ten `.f3d`/STEP/STL sets, 33/33 completion audit, 300 schema-validated model reviews. Explicitly "visually complete product-concept assemblies, not fabrication-release drawings." |
| The six configurations fit the vehicles they claim | **Verified by solver** | `config_solver.py --validate-all`, 6 configurations, 0 with no fitting vehicle. |

---

## 3. What is NOT resolved — and why it is left out of v1

### 3a. The vehicle mount (part "C-02") — deferred entirely

This is the single most important exclusion. The frame has a lock feature (part
C-01, a plate on the module) that is meant to pin to a matching bracket bolted to
the vehicle floor. **That vehicle-side bracket is not designed.**

- Factory cargo tie-down spacing is **not published** by the manufacturers for
  any of the target vehicles (4Runner, Bronco, Wrangler, Sprinter, Tacoma,
  Transit, Gladiator, ProMaster, GX/Land Cruiser, Outback). The project checked.
- A generated or estimated hole pattern produces a bracket that does not bolt to
  the vehicle — the project's own notes call this "the single most expensive
  error this project can make," and the design queue is deliberately gated to
  refuse to run without real measurements.
- Even the "universal L-track" version of the bracket has **pin diameter and
  plate thickness recorded as assumptions until a load case is defined.**

**A load attached to a moving vehicle is a safety item.** There is no honest way
to ship guidance for it from the current design. v1 covers the frame; the
vehicle attachment is your engineering problem until Bear Necessities publishes a
measured, load-cased C-02. If you need the module restrained for transport now,
use rated cargo straps to the vehicle's own anchor points and treat the module
as unsecured cargo, not as a fixed installation.

### 3b. Frame joint design — concept only

The cut list is firm. **How the twelve members bolt together is not released.**

- The current concept uses 80/20 `4132` gusseted inside-corner brackets (24 per
  frame) with `3393` fastener assemblies (48 per frame). Those are real catalog
  parts and the pack lists them.
- But the project marks this joint **`ENGINEERING_HOLD`**: "joint release
  requires dynamic test." The bracket type and count are an engineering
  assumption, not a tested result. A concealed-anchor alternative (`3395` /
  TNUTZ `AF-010`) is carried at quantity zero as an unevaluated option.
- Source files disagree on the exact fastener SKU (`3393` vs `3395`). This pack
  uses `3393` because that is what the current procurement BOM and the
  production-readiness audit specify for the `4132` bracket; both are 80/20
  catalog parts and you should confirm the correct one with 80/20 when you order.

### 3c. No load ratings, torque specs, or safety factor

None exist. The project's physical test plan leaves every load magnitude blank
"until Conor approves intended payload and vehicle deceleration cases."
Specifically undefined:

- Fastener install torque (get 80/20's published spec for the `3393` fastener
  from the vendor — do not guess).
- Frame payload limit and the crash / rough-road load cases.
- Carry-handle load rating (the handles are "not authorized for a loaded lift
  until tested").
- Drawer-slide load ratings (the Accuride `3832` family is a "verify exact
  suffix, load" placeholder).
- Tie-down strap working load applied through the module (the NRS strap has a
  published 500 lb WLL, but "the module anchor / load path still requires
  engineering").

### 3d. Panels and skins — not drawn

The side/back panels are specified as "cut-to-size polymer sheet from a released
DXF." **Those DXFs do not exist.** Panel thickness is called "module-specific"
and unengineered. v1 gives you the frame; the enclosure is not documented.

### 3e. Module interiors — concept, with open SKUs

Every one of the ten modules has unresolved items — a custom worktop, a sourced
container, plumbing SKUs, ventilation calcs, electrical labelling. `04-module-
concepts.md` lists them per module. Treat the module sheets as design direction,
not as parts kits you can order complete.

---

## 4. No prototype has been built

This has to be stated plainly to any buyer. The frame in this pack has never been
cut, bolted, loaded, driven, or lived with. The CAD is internally consistent and
the parts are real, but **nothing here is build-verified.** The first person to
build it will find things the CAD did not — bracket access, T-nut fit, real
squareness after assembly, whether a 24 in module actually clears their wheel
wells.

**How to frame this honestly to a customer:**

- Sell it as what it is: *"validated geometry and a catalog parts list for a
  frame we designed but have not yet built — priced accordingly."*
- Do not use "tested," "proven," "field-tested," "rated," or "engineered for" in
  the listing. Use "designed," "modelled," "concept," "starting point."
- Put the no-prototype disclosure and the C-02 exclusion **above the buy button**,
  not buried in terms.
- Price it as a design reference (tens of dollars), not as an engineered product
  (hundreds). The revenue analysis for this project put the realistic figure at
  $20–80 per pack.
- Offer a refund policy that survives someone reading this file after purchase.

---

## 5. The CAD file units caveat

The STEP and DXF files in `drawings/` were exported before a unit-handling fix
landed in the project's CAD toolchain. They carry a **millimetre unit tag, but
the geometry is in inch values** (a 4.000 in plate reads as "4.0" with a
millimetre label — i.e. 25.4× too small if imported blindly).

**Before sending any file here to a shop or a CAM program:** set the import units
to **inches**, or scale by 25.4. The dimensioned drawing in
`03-anchor-plate-C-01.md` is the authoritative definition — the files are
reference geometry. A clean, correctly-tagged release DXF is a pre-sale to-do
for Bear Necessities.

---

## 6. What a buyer will still need that this pack does not provide

1. **A vehicle-mount solution** (C-02) — measured to their vehicle, with a load
   case. The biggest gap.
2. **Fastener torque and a joint that's been load-tested** — or their own
   engineering sign-off on the `4132` bracket concept.
3. **Panel drawings** — dimensions and hole patterns for the side/back skins.
4. **A finished parts list for whichever module interior they want** — the
   module sheets get them ~70% there; the last 30% is sourcing and small custom
   parts.
5. **Live prices and lead times** — everything in the BOM is quote-on-request.
6. **Their own fit check** — that a 24 in-wide module clears their wheel wells
   and passes through their tailgate opening. The project's own worksheet
   (`MEASUREMENT-WORKSHEET.md`) is the tool for this; a Subaru Outback in
   particular may not fit.

---

## 7. Recommended pre-sale checklist for Bear Necessities

Before this pack goes on sale, in rough priority order:

- [ ] Re-export the C-01 and base-frame CAD with correct inch unit tags, or
      replace them with a clean release DXF.
- [ ] Decide and write the licence / no-warranty / buyer-responsibility terms
      (§1 of the README is a placeholder).
- [ ] Get one live quote for the frame BOM so the listing can state a real
      "parts cost from ~$X" figure instead of "get a quote."
- [ ] Confirm the `3393` vs `3395` fastener question with 80/20.
- [ ] Build one frame. Even an unloaded bench build closes most of §4 and lets
      the assembly guide be written from reality instead of from CAD.
- [ ] Trademark search on "Bear Necessities" before putting it on a storefront.
