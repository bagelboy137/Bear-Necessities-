# Production-readiness audit

Date: 2026-08-25

| Objective requirement | Evidence | Verdict |
|---|---|---|
| Run the best suitable local model available here | LM Studio raw outputs identify `qwen/qwen2.5-coder-14b`; installed metadata shows MLX 4-bit, 14B | Proven |
| Create ten modules like the reference image | `module-family.json`; ten STEP/STL/SVG/JSON sets; combined family STEP | Proven as packaging prototypes |
| Use orderable aluminum-extrusion lengths | Common cut list is 8x18in + 4x22in; TNUTZ EX-1010 page supports both cut lengths | Proven for extrusion ordering |
| Permit drop shipment to customers | Supplier sells custom cut lengths online | Partially proven; commercial drop-ship-to-end-customer terms not yet obtained |
| Flag components that cannot be ordered online | `procurement-bom.csv` has explicit source/custom/hold/rejected dispositions | Proven |
| BOM lets purchasing begin | `prototype-buy-list.csv` gives bounded sample quantities and manufacturer links | Proven for prototype purchases, not production quantity |
| Feed learnings into local models/framework | Updated planner/reviewer prompts, family validator, ten generated jobs, clearance/BOM evidence, test, and `LOCAL-MODEL-LEARNINGS.md` | Proven |
| Ready for production | Requires load cases, native assembly joints/interference, custom panel drawings, vehicle anchor resolution, moving/service envelopes, supplier terms, physical fit/load/vibration/leak/thermal tests | Not proven |

## Hard release blockers

1. Define module mass limits and crash/rough-road load cases; approve a safety factor.
2. Select and test frame joinery. The 4132/3395 counts are an engineering hold.
3. Resolve the vehicle-side anchor and prove installation on target vehicles.
4. Source the remaining containers, plumbing, handles, feet, panels, retainers,
   hinges/latches, wiring protection, cargo nets, and straps.
5. Create toleranced flat-pattern drawings for every custom panel/retainer.
6. Model moving/service envelopes and run native Fusion interference checks.
7. Build at least one common frame and execute static load, vibration, retention,
   leak, thermal/ventilation, hot-use, corrosion and usability tests as applicable.
8. Obtain supplier commercial terms for blind/end-customer drop shipment, packaging,
   returns, substitutions, lead-time reporting and cut-tolerance acceptance.

## 2026-08-25 framework hardening addendum

- Replaced the Pelican 1535's 0.02-inch nominal side clearance with a smaller
  Pelican 1485 envelope and regenerated all CAD artifacts.
- Added a 0.125-inch six-face free-clearance gate, with explicit permitted mount
  contacts such as a component resting on the lower support plane.
- Added BOM reconciliation proving 80x18-inch and 40x22-inch EX-1010 demand.
- Corrected joint hardware: 4132 brackets pair with 3393 assemblies. The 3395 /
  TNUTZ AF-010 counterbored anchor option remains quantity zero.
- Generated ten production-framework job files. None can become `RELEASED`
  automatically and every one carries sourcing, physical-test and human gates.

The automated system must keep every module at `AWAITING_HUMAN_REVIEW` until
these items have objective evidence. No model output can waive them.

## External-evidence handoff

The exact remaining requests and tests are now executable artifacts:

- `SUPPLIER-RFQ-DRAFT.md` asks the extrusion supplier for written cut tolerance,
  kit packaging, blind drop-ship, labeling, lead-time, substitution and claims terms.
- `PHYSICAL-TEST-PLAN.md` defines incoming inspection, frame geometry, static load,
  handle cycling, vibration/retention, module safety and fulfillment tests while
  leaving unapproved load magnitudes blank.
- `RELEASE-EVIDENCE-CHECKLIST.md` maps supplier, CAD, BOM, physical and human
  evidence required for each of the ten jobs.

These artifacts close the framework/process gap. They do not substitute for the
supplier's written response, purchased sample frame or measured test results.
