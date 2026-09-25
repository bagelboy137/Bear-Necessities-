#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
NATIVE_DIR=${SCRIPT_DIR:h}/fusion_native
LEDGER="$SCRIPT_DIR/runs/iteration-ledger.json"
CATALOG="$SCRIPT_DIR/ots-components.json"
PROFILE=${BN_LM_PROFILE:-auto}

"$SCRIPT_DIR/run_revision_profile.sh" "$PROFILE"

# Do not keep the coding model resident while Fusion and the visual reviewer
# compete for unified memory. The completed ledger is already on disk.
lms unload --all || true

python3 "$NATIVE_DIR/run_native_pipeline.py" \
  --revision-ledger "$SCRIPT_DIR/runs/design-ledger.json" \
  --ots-catalog "$CATALOG" \
  --output-root "$SCRIPT_DIR/checkpoints/design/exports" \
  --expected-reviews 100 \
  --vision-reasoning off --vision-context-length 3072 \
  --vision-cooldown-seconds 10 --vision-max-load 32 \
  --vision-min-free-percent 20

python3 "$NATIVE_DIR/run_native_pipeline.py" \
  --revision-ledger "$SCRIPT_DIR/runs/manufacturing-ledger.json" \
  --ots-catalog "$CATALOG" \
  --output-root "$SCRIPT_DIR/checkpoints/manufacturing/exports" \
  --expected-reviews 200 \
  --vision-reasoning off --vision-context-length 3072 \
  --vision-cooldown-seconds 10 --vision-max-load 32 \
  --vision-min-free-percent 20

python3 "$SCRIPT_DIR/validate_revision_ledger.py" "$LEDGER"
python3 "$SCRIPT_DIR/generate_module_boms.py"
python3 "$SCRIPT_DIR/summarize_iteration_learnings.py" --ledger "$LEDGER"
python3 "$NATIVE_DIR/run_native_pipeline.py" \
  --revision-ledger "$LEDGER" \
  --ots-catalog "$CATALOG" \
  --expected-reviews 300 \
  --vision-reasoning off --vision-context-length 3072 \
  --vision-cooldown-seconds 10 --vision-max-load 32 \
  --vision-min-free-percent 20

lms unload --all || true

echo "MAC_MINI_REPLICATION_PASS"
