# 01 — Frame cut list and bill of materials

For **one** module frame: a 24 × 20 × 18 in outside cube in 1 × 1 in
("10 Series") aluminium T-slot extrusion.

All part numbers below were checked on 2026-08-20 against 8020.net and
tnutz.com. **Prices are intentionally blank — request a live quote.** Do not fill
them in from memory or estimate.

See `00-status-and-limitations.md` §3b before ordering the brackets: the joint
design is an engineering-hold concept, not a tested joint.

---

## The cut list — two lengths only

| Cut length | Qty | Role in the frame |
|---|---:|---|
| **18 in** | 8 | 4 vertical corner posts + 4 depth rails (2 top, 2 bottom) |
| **22 in** | 4 | 4 width rails (2 top, 2 bottom) |

**Why the depth rails and posts are the same length:** the frame is 18 in tall,
and the 20 in depth minus two 1 in profiles at the ends leaves an 18 in rail. So
8 of the 12 pieces are one length. The 22 in width rail is 24 in minus two 1 in
profiles.

- Total extrusion per frame: **232 in = 19.33 ft**.
- Distinct cut lengths: **2**. Preserve this in any change to the design — it is
  the cheapest orderable cut list and the project treats it as a hard invariant.

### Cut geometry

```
            22" width rail  (x4: 2 top, 2 bottom)
        ┌──────────────────────┐
        │                      │
 18"    │                      │  18" vertical post (x4)
 depth  │                      │
 rail   │                      │
 (x4)   └──────────────────────┘
        outside footprint 24" x 20", height 18"
```

Every member is a plain length of profile. **No machining, no end taps, no
drilled holes in the extrusion** in this concept — the corner brackets and
T-nuts do all the joining from inside the slots. (An alternative concealed-anchor
joint would require counterbored ends; it is carried at quantity zero and is not
part of this pack.)

---

## Bill of materials — one frame

| # | Part number | Alt. part | Description | Vendor | Qty | Unit | Status |
|---|---|---|---|---|---:|---|---|
| 1 | `1010-S` (cut to 18 in) | `EX-1010` | 1 × 1 in smooth-surface T-slot profile, four open slots | 80/20 Inc (alt: TNUTZ) | 8 | pc | Orderable |
| 2 | `1010-S` (cut to 22 in) | `EX-1010` | 1 × 1 in smooth-surface T-slot profile, four open slots | 80/20 Inc (alt: TNUTZ) | 4 | pc | Orderable |
| 3 | `4132` | — | 10 Series 2-hole **gusseted** inside corner bracket | 80/20 Inc | 24 | pc | **Engineering hold** — joint not load-tested |
| 4 | `3393` | — | 1/4-20 × 0.500 in bolt + slide-in economy T-nut assembly, for the `4132` bracket (2 per bracket) | 80/20 Inc | 48 | pc | **Engineering hold** — torque/vibration retention unverified |

**Bracket count logic:** three members meet at each of the 8 corners (one post,
one width rail, one depth rail). One 2-hole bracket joins each adjacent pair →
3 brackets per corner × 8 corners = 24. Two fastener assemblies per bracket → 48.

### Notes on each line

- **Lines 1–2 (extrusion).** TNUTZ `EX-1010` is stated 100% compatible with 80/20
  `1010-S` and is sold cut to any length 1–96 in from the product-page dropdown
  in 1/16 in steps, ~48 h turnaround, no separate cut fee shown on the page.
  Order URL: `https://www.tnutz.com/product/ex-1010/`. Most 80/20 distributors
  drop-ship and take margin, so going direct to a cutting distributor is likely
  cheaper and faster. **Not yet confirmed:** whether a cut fee appears at
  checkout, volume pricing, and whether 80/20's own `1010-S` offers the same
  any-length ordering or only mill lengths — worth one phone call before a real
  order.
- **Line 3 (`4132` bracket).** Gusseted (heavy-duty) chosen over the lighter
  `4108` because the modules are designed to carry a loaded fridge and be lifted
  by their corners. Order URL: `https://8020.net/4132.html`. **This is an
  engineering-hold item:** you can put it in a cart today, but the project has
  not load-tested this joint. If you are carrying anything heavy, get your own
  engineering sign-off on the bracket type and count.
- **Line 4 (`3393` fastener).** Order URL: `https://8020.net/3393.html`. The
  project's older BOM files and the CAD provenance file name `3395` (a 10-32
  anchor fastener) instead; the current procurement BOM and the
  production-readiness audit both specify `3393` as the correct hardware for the
  `4132` bracket, with `3395` at quantity zero. **Confirm the correct fastener
  with 80/20 when you order the bracket** — they will tell you what `4132` takes.
- **Install torque is not specified anywhere in the source design.** Use 80/20's
  published torque spec for the `3393` fastener (request it from the vendor). Do
  not guess a torque value for a joint that carries load in a vehicle.

---

## Ordering for more than one frame

The ten-module family scales linearly:

| Frames | 18 in pieces | 22 in pieces | `4132` brackets | `3393` fasteners | Total extrusion |
|---:|---:|---:|---:|---:|---:|
| 1 | 8 | 4 | 24 | 48 | 232 in |
| 10 | 80 | 40 | 240 | 480 | 2320 in (193 ft) |

---

## What this BOM does not include

- **The vehicle mount (C-02).** Not designed. See `00-status-and-limitations.md`
  §3a.
- **The module anchor plate (C-01).** Covered separately in
  `03-anchor-plate-C-01.md` — it's a custom laser-cut part, not catalog.
- **Panels / skins, handles, feet, gasket, tread, drawer slides, latches.**
  These appear in the module concepts (`04-module-concepts.md`) and the parts
  catalog (`05-off-the-shelf-parts-catalog.md`) but are not part of the bare
  frame and several are not yet sourced to a specific part number.
- **Fasteners to attach panels or accessories to the frame** — depends on the
  panel design, which isn't drawn.

## Reference files

- `drawings/base-frame-ots.step` — 3D model of the frame (see units caveat,
  `00-status-and-limitations.md` §5).
- `drawings/base-frame-ots-ISO.svg` — projected line drawing.
- `drawings/base-frame-ots.stl` — mesh, for quick viewing.
