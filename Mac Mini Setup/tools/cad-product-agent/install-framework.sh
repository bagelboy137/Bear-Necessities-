#!/usr/bin/env bash
# Install/update the portable professional layer in the sibling Fusion project.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_ROOT="$(cd "$HERE/../../.." && pwd)"
DEST="${1:-$CLAUDE_ROOT/Fusion CAD Agent/professional}"

mkdir -p "$DEST"
for item in README.md job.schema.json cad_plan.py drawing_quality.py professional_drawing_loop.py professional_pipeline.py vision_review.py prompts templates tests; do
  cp -R "$HERE/$item" "$DEST/"
done
chmod +x "$DEST/professional_pipeline.py"
chmod +x "$DEST/cad_plan.py" "$DEST/professional_drawing_loop.py" "$DEST/vision_review.py"
echo "Installed professional CAD framework at $DEST"
