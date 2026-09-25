# Visual marketing brief — Bear Necessities module family

Supersedes nothing. `VISUAL-DESIGN-BRIEF.md` sets the **completion** bar: is the
equipment recognizable from an isometric screenshot. That bar is met and stays met.
This document adds the **presentation** bar: would a customer believe this is a
photograph of a real product.

Both bars apply. A beautiful render of an unrecognizable box fails, and so does a
legible flat CAD capture.

## Why this exists

Measured on 2026-08-26 across all ten current `-iso.png` renders:

| Signal | Measured | What it means |
|---|---|---|
| Peak foreground luminance | 170–180 of 255 (one outlier 230) | Nothing in the frame is a specular highlight. Metal cannot read as metal. |
| Fraction above luminance 235 | **0.0000 on all ten** | Literally zero highlight pixels in the family. |
| Luminance spread within the aluminium mask | σ ≈ 12.7, near-identical on nine of ten | Faces are flat-filled, not lit. |
| Background variance | 0.00 | Fully transparent. No ground, therefore no contact shadow, therefore the module floats. |
| Distinct alpha values | 5 | Hard cut-out edge. |

The consistency is the tell: nine modules landing within 1.0 of the same σ is a
renderer signature, not ten independent lighting choices.

## Family visual language

Everything in `VISUAL-DESIGN-BRIEF.md` carries over verbatim — twelve silver
extrusion members with visible slot lines, dark charcoal infill, black hardware,
rounded pull handles, visible fasteners, the front module ID plate, the 24 × 20 × 18
frame, and the per-module required-visible-content list for BN-M01 … BN-M10.

Added on top:

**Materials.** Brushed aluminium must read as metal: an anisotropic highlight that
travels along the extrusion axis, not a uniform grey fill. Charcoal panels matte,
with enough falloff across a face to show its orientation. Rubber, glass, fabric and
painted steel each visibly distinct from the panels — currently they differ only in
albedo.

**Light.** Three-point: a key establishing form, a fill keeping the shadow side
readable rather than black, and a rim separating the frame from the background. The
key must produce a specular hit on the aluminium.

**Ground.** The module sits on a surface. A contact shadow directly beneath the
frame rails is the single strongest cue that this is an object rather than a
drawing, and it is the one thing a transparent-background capture can never have.

**Background.** A neutral gradient or seamless ground for hero use. Ship an
`-alpha` cut-out variant alongside for web compositing — that variant is exempt from
the background and contact-shadow gates and from nothing else.

**Camera.** One focal length and one horizon height across all ten modules, so a
grid reads as one product line. Three views per module:

| View | Purpose | Minimum |
|---|---|---|
| `hero` | 3/4 isometric, the primary marketing image | 2400 × 1800 |
| `front` | straight-on, for spec sheets and the comparison grid | 1600 × 1200 |
| `detail` | crop on the module's defining feature | 1600 × 1200 |

Subject fills 25–75 % of the frame and sits within 8 % of frame centre. A module
photographed as a speck in the corner fails regardless of how well it is lit.

## The gate

`visual_quality.py` measures all of the above deterministically — no model, no
tokens. Thresholds live in `visual-quality-thresholds.json` so they are data, not
code. The current renders fail it, which is the point.

| Metric | Threshold | Baseline |
|---|---|---|
| `tonal_p99` | ≥ 215 | 151 |
| `specular_fraction` | ≥ 0.0008 | 0.0000 |
| `metal_modulation` | ≥ 22.0 | 12.7 |
| `panel_modulation` | ≥ 14.0 | iso 18.7–30.1 ✓ · front 8.7–15.0 ✗ |
| `edge_density` | ≥ 0.055 | 0.065–0.112 ✓ |
| `subject_coverage` | 0.25 – 0.75 | iso 0.52–0.55 ✓ · front 0.820 ✗ |
| `subject_centering` | ≤ 0.08 | ✓ |
| `background_class` | not `transparent` (hero/front/detail) | transparent ✗ |
| `contact_shadow` | present | absent ✗ |
| resolution | per view, above | 1600 × 1200 |

Measured 2026-08-26: **0 of 20 legacy renders pass.**

`edge_density` is the only floor every current render clears. It is in the gate to
stop a lighting change from *destroying* detail that currently works — the common
failure mode when someone chases a highlight and blows out the fine geometry.

Two findings the baseline surfaced that are camera work, not lighting:

- **Every front view is framed at 0.820 coverage** — cropped so tight the module
  touches the frame edge. Reframe to the 0.25–0.75 band.
- **Front-view `metal_modulation` is roughly half the iso value** (7.1–15.0 against
  12.0–20.7). A straight-on camera puts every extrusion face at the same angle to
  the single light, so they all shade identically. Even with better materials, the
  front view needs its own key-light angle rather than inheriting the iso setup.

## Visual QA process

1. Deterministic gate — `visual_quality.py`. Primary judge, runs on every image.
2. Local VLM checklist — a fixed yes/no list per module, one image per request.
   Second opinion, never the sole gate.
3. One Claude confirmation pass over the finished contact sheet.

A render that passes the numbers and loses a required visible cue still fails. The
completion bar was never optional.
