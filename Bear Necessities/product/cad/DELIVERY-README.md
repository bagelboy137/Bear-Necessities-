# Bear Necessities native Fusion module delivery

Delivered 2026-08-25 after three separate live Autodesk Fusion build/export
checkpoints and a 33/33 completion audit.

## Separate CAD assemblies

| Module | Product concept | Named components |
|---|---|---:|
| BN-M01 | Cook Station | 143 |
| BN-M02 | Dry Pantry | 139 |
| BN-M03 | Fridge Freezer | 126 |
| BN-M04 | Sink Wash | 125 |
| BN-M05 | Fresh Water | 131 |
| BN-M06 | Recovery Utility | 208 |
| BN-M07 | Power Hub | 140 |
| BN-M08 | Hot Water Shower | 174 |
| BN-M09 | Field Office Camera | 174 |
| BN-M10 | Camp Furniture Soft Goods | 133 |

Every module directory contains a distinct native `.f3d` assembly plus STEP,
STL, OBJ/MTL, front/isometric PNGs, and its machine-readable build report. All
ten measured envelopes are 24.0016 × 20.0016 × 18.0016 inches and pass the
24 × 20 × 18 target within the 0.01-inch concept gate.

## Review evidence

- 30 validated family cycles: 10 design, 10 manufacturing, 10 combined.
- 300 schema-validated module reviews with local-model provenance.
- 120 reviews used Qwen2.5 Coder 14B MLX 4-bit; after repeated IOGPUFamily
  kernel panics on the 16 GB laptop, the remaining 180 used the approved 7B
  MLX low-memory continuation profile.
- All 30 Fusion checkpoint renders were directly inspected and bound to their
  SHA-256 values. The triple visual gate combines deterministic part/cue checks,
  hash-bound image inspection, and current comparable/OTS web evidence.
- Ten native `.f3d` hashes are distinct and the final completion audit passes
  33/33 requirements.

The local model proposed and dispositioned revisions. Autodesk Fusion's Python
API built and exported the deterministic geometry; the language model was not
allowed to write arbitrary Fusion code directly or self-certify release.

## BOM and procurement boundary

`bom/modules/` contains one linked prototype BOM per module and a combined CSV.
Rows marked `HOLD_*`, `SOLD_OUT`, or `*_VERIFY` require engineering or
procurement confirmation. In BN-M03, the sold-out Engel MD-14 has quantity zero;
the MHD13F-DM alternate has quantity one and must be dimension/use/warranty
verified before purchase.

## Mac mini replication

The evidence bundle includes the revision ledger, retrieval learnings, OTS and
comparable catalogs, safe LM Studio profiles, and the one-command Mac mini
replication script. The script unloads the coding model before Fusion/vision so
they do not compete for unified memory. The 16 GB laptop profile does not run a
full local-VLM batch after a canary exposed duplicate JIT model loading.

## Release boundary

These are visually complete product-concept assemblies, not fabrication-release
drawings. Structural loads, vehicle attachment, slide ratings, panel gauges,
fastener torque, plumbing/electrical safety, tolerances, and physical testing
remain human engineering gates.
