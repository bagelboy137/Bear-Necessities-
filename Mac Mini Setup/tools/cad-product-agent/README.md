# Professional offline CAD product agent

Portable orchestration layer for the existing `Fusion CAD Agent` project. It turns a product brief into an auditable overnight **release candidate**, never an automatically released manufacturing package.

## Architecture

```text
Bear Necessities product requirements
        ↓ schema + source + tolerance gates
MLX planning/review model
        ↓ explicit feature/member plan
MLX coding model → CadQuery preflight → numeric validator
        ↓ best attempt preserved
MLX coding model → Fusion MCP → fresh document → numeric verification
        ↓ screenshot + exports
MLX vision review → visual defect report (advisory only)
        ↓
artifact/release gate → AWAITING_HUMAN_REVIEW
        ↓ human checks fit/load/tolerances/drawing
RELEASED manually
```

The model is never the source of truth for measurements, tolerances, loads, materials, catalog part numbers, or release approval. Those are structured inputs with provenance.

## Why two geometry passes

- **CadQuery first:** headless, deterministic, fast, and strong numeric validation. It can run overnight even if Fusion is signed out or unavailable.
- **Fusion second:** builds the native design through Fusion's local MCP server, checks the live document, captures screenshots, and provides traceback-driven repair.
- **Drawing draft:** the existing ezdxf loop remains the deterministic 2D path. Fusion's `DrawingManager.createDrawing` API is Preview as of July 2026, so it is not a dependable unattended production dependency.

## Commands

```bash
python3 professional_pipeline.py validate templates/bear-base-frame.job.json
python3 professional_pipeline.py run templates/bear-base-frame.job.json --dry-run
python3 professional_pipeline.py run templates/bear-base-frame.job.json
python3 professional_pipeline.py release-check runs/BN-MCS-BASE-001/<timestamp>
```

By default the pipeline discovers sibling projects under the shared Claude folder. Override with `--fusion-root` and `--mac-mini-root` after migration.

## Job states

- `DRAFT`: incomplete; no model calls.
- `BLOCKED_NEEDS_MEASUREMENT`: measured interfaces missing; no model calls.
- `READY_PROTOTYPE`: may build and validate prototypes, but cannot be released.
- `READY_RELEASE_CANDIDATE`: engineering inputs complete; may build a candidate.
- `AWAITING_HUMAN_REVIEW`: automated gates passed; human inspection required.
- `RELEASED`: set manually outside this runner after signoff.

## Professional quality gates

1. Every critical interface has a value, tolerance, source type, and source reference.
2. Material, process, units, and design envelope are explicit.
3. Release candidates require a defined load case and safety-factor target.
4. A part-specific deterministic validator must exist before the job is READY.
5. Solid validation checks dimensions, volume/mass proxy, solid count, and validity.
6. Assemblies require an interference check and BOM reconciliation. A joined-body
   `geometry_proxy` is acceptable for prototypes only; release candidates must
   declare a native assembly, expected component count, and executable validators.
7. Drawings require orthographic views, dimensions, tolerances, material/process notes, revision, and title-block data.
8. Visual-model review can flag omissions but cannot override numeric validation.
9. No result overwrites the best prior attempt or a released artifact.
10. Human review is always required before fabrication, purchase, or publication.

Release validator contract: both validator scripts accept `--job`,
`--fusion-root`, and `--out-name`, return nonzero on failure, and write their
evidence beside the other exports for archival.

## Installation

`install-framework.sh` copies this source into `Fusion CAD Agent/professional/`. The Mac mini bootstrap can run that installer after the shared Claude folder is migrated.
