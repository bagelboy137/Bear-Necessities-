# Native Fusion ten-module pipeline

This is the API-driven replacement for the earlier box-envelope prototypes. It
creates ten separate, editable Fusion archives with colored, named components
and customer-facing visual detail, then blocks success until deterministic,
hash-bound visual, and web-evidence checks pass.

## One-command run

Fusion must be open with **Preferences > General > API > Fusion MCP Server**
enabled on port 27182. LM Studio must serve the OpenAI-compatible API on port
1234 with `qwen/qwen2.5-coder-14b` and `google/gemma-4-e4b` available. The
30-cycle runner in `../iterations/` must have produced a 300-review PASS ledger.

```bash
python3 run_native_pipeline.py --probe
python3 run_native_pipeline.py
```

The runner is self-contained and uses only Python's standard library. It:

1. Initializes a real MCP session and proves the Execute/Read/Update tools exist.
2. Verifies the configured vision model is exposed by LM Studio.
3. Injects the selected output path, validated Qwen revision ledger, and curated
   OTS catalog, then executes `build_native_modules.py` inside live Fusion.
4. Creates a fresh Fusion document for each module and exports it before closing.
5. Runs `validate_native_family.py` against files, dimensions, named components,
   frame members, OTS traceability, 300-review provenance, materials, image
   dimensions, and distinct F3D hashes.
6. On the Mac mini, runs `review_native_family.py` over all ten isometric views
   using the local vision model and records each input image hash. A PASS with
   any blocking or missing finding is rejected as contradictory.
7. Runs `validate_visual_completion.py`, requiring three current checks per
   module: deterministic cues, a hash-bound local-VLM or independent Codex
   inspection PASS, and a cited comparable-product or selected OTS-product
   page. The 16 GB laptop uses the independent path because its local-VLM
   canary exposed duplicate JIT loading; see `../iterations/LM-STUDIO-SAFE-PROFILES.md`.

Use `--skip-build` to re-run gates on existing files or `--skip-vision` for a
fast numeric/file-only development pass. The normal release-evidence run skips
neither.

## Output contract

Each `fusion-native/exports/BN-M##/` directory contains:

- `.f3d` — native multi-component Fusion archive
- `.step` — neutral assembly exchange file
- `.stl` — single visualization/reference mesh
- `.obj` + `.mtl` — colored visualization mesh and material library
- `-iso.png` and `-front.png` — transparent 1600×1200 views
- `-build.json` — dimensions, part registry, visual cues, and export evidence

Family-level evidence:

- `family-build-report.json`
- `native-validation-report.json`
- `local-vlm-visual-review.json`
- `native-pipeline-run.json` when the one-command runner is used end to end
- `triple-visual-validation-report.json` — 30/30 visual completion checks
- `../iterations/runs/iteration-ledger.json` — 30 Qwen cycles / 300 module reviews
- `../iterations/boms/` — ten separate order-linked prototype BOMs and combined BOM

For handoff, `fusion-native/Bear-Necessities-Native-Fusion-Modules.zip` bundles
all ten separate module directories plus the final visual and machine evidence.

## Quality boundary

These files are visually complete product-concept CAD suitable for website
concept imagery and design review. They are not fabrication release: structural
loads, joints, panel gauges, slide ratings, anchors, plumbing/electrical safety,
tolerances, and physical testing remain governed by the existing release gates.
