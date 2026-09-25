#!/bin/zsh
set -euo pipefail

SCRIPT_DIR=${0:A:h}
MAC_PROJECT=${SCRIPT_DIR:h:h:h:h:h}
CLAUDE_ROOT=${MAC_PROJECT:h}
BEAR_CAD="$CLAUDE_ROOT/Bear Necessities/cad"
PROFILE=${1:-auto}

PRIMARY_MODEL="qwen/qwen2.5-coder-14b"
LOW_MEMORY_MODEL="qwen2.5-coder-7b-instruct"
RAM_BYTES=$(sysctl -n hw.memsize)
RAM_GIB=$((RAM_BYTES / 1073741824))

if [[ "$PROFILE" == "auto" ]]; then
  if (( RAM_GIB <= 24 )); then
    PROFILE="laptop-safe"
  else
    PROFILE="mac-mini"
  fi
fi

case "$PROFILE" in
  laptop-safe)
    MODEL="$LOW_MEMORY_MODEL"
    CONTEXT=6144
    MAX_TOKENS=1800
    COOLDOWN=30
    MAX_LOAD=20
    MIN_FREE=30
    ;;
  mac-mini)
    MODEL="$PRIMARY_MODEL"
    CONTEXT=6144
    MAX_TOKENS=2000
    COOLDOWN=5
    MAX_LOAD=32
    MIN_FREE=20
    ;;
  *)
    echo "usage: $0 {auto|laptop-safe|mac-mini}" >&2
    exit 2
    ;;
esac

echo "LM_PROFILE profile=$PROFILE ram_gib=$RAM_GIB model=$MODEL context=$CONTEXT parallel=1 max_tokens=$MAX_TOKENS cooldown=${COOLDOWN}s"

python3 "$SCRIPT_DIR/run_revision_cycles.py" \
  --guard-only --max-load "$MAX_LOAD" --min-free-percent "$MIN_FREE"

lms unload --all >/dev/null 2>&1 || true
lms load "$MODEL" \
  --context-length "$CONTEXT" \
  --parallel 1 \
  --ttl 600 \
  --no-speculative-draft-mtp \
  --identifier "$MODEL" \
  --yes

BN_REVIEWER_MODEL="$MODEL" \
BN_ALLOWED_REVIEW_MODELS="$PRIMARY_MODEL,$LOW_MEMORY_MODEL" \
BN_REVISION_MAX_TOKENS="$MAX_TOKENS" \
BN_REVISION_COOLDOWN_SECONDS="$COOLDOWN" \
BN_REVISION_MAX_LOAD="$MAX_LOAD" \
BN_REVISION_MIN_FREE_PERCENT="$MIN_FREE" \
  "$BEAR_CAD/build.sh" revision --skip-preflight

echo "REVISION_PROFILE_PASS profile=$PROFILE model=$MODEL"
