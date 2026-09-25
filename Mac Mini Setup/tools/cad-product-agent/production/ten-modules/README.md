# Ten-module local-model production study

This package began as a validated packaging study and now also contains a native,
visually complete Fusion concept family. It is not a fabrication-released family.
Qwen2.5-Coder-14B ran locally in LM Studio and produced the initial ten-module
concept JSON and CadQuery implementation. The raw outputs are preserved. The
CAD script was repaired only in response to executable validation failures:
CadQuery export API misuse, nested compounds, and missing inner-frame clearance.

## Outputs

- `fusion_native/`: self-contained Fusion MCP builder, client, one-command runner,
  deterministic native-file validator, and local-VLM family reviewer.
- `fusion-native/exports/`: ten separate F3D/STEP/STL/OBJ module files, matching
  1600×1200 isometric/front PNGs, per-module build reports, and family QA evidence.
- `VISUAL-DESIGN-BRIEF.md` and `local-model-visual-review.md`: comparable-product
  cues and the preserved Qwen2.5-Coder-14B local design review.

- `module-family.json`: sourced component envelopes, disposition, and blockers.
- `procurement-bom.csv`: buy/source/custom/rejected list. Zero-quantity rejected
  rows are deliberate warnings against buying plausible components that do not fit.
- `prototype-buy-list.csv`: deliberately small first-purchase list; it avoids
  committing to ten frames before one physical frame and payload fit check pass.
- `SUPPLIER-RFQ-DRAFT.md`: ready-to-send commercial/cut-tolerance inquiry.
- `PHYSICAL-TEST-PLAN.md` and `RELEASE-EVIDENCE-CHECKLIST.md`: objective path
  from packaging prototype to manually released product.
- `build_ten_modules.py`: validator-repaired local-model geometry generator.
- `exports/BN-M01.step` through `BN-M10.step` and matching STL/SVG/JSON files.
  These are the original package-envelope prototypes and are superseded for
  visual use by `fusion-native/exports/`.
- `exports/BN-family-10-modules.step`: all ten modules spaced 30 inches apart.
- `local-model-cad-response.md`: untouched local model response.
- `jobs/`: ten machine-readable framework jobs with sourcing and release gates.
- `clearance-report.json` and `bom-reconciliation-report.json`: deterministic
  evidence consumed by the family validator.

All ten frames use 8 × 18-inch and 4 × 22-inch extrusion. Across the family,
that is 80 × 18-inch and 40 × 22-inch pieces (2,320 inches / 193.33 feet total).

The packaging gate uses the true 22 × 18 × 16-inch clear region inside the
1-inch frame, not merely the 24 × 20 × 18 outside envelope. This rejected both
22.1-inch-wide Milwaukee PACKOUT candidates even though they look like an easy
fit from outside dimensions alone.

## Production boundary

Do not place production orders yet. Extrusion sample quantities and one of each
candidate component are reasonable for fit prototypes, but frame joinery,
vehicle anchoring, dynamic loads, ventilation, plumbing, hot-use behavior,
electrical routing, and custom panel drawings remain engineering gates.

The native Fusion files are suitable for website concept presentation, but that
visual completion does not waive the engineering and physical-release boundary.
