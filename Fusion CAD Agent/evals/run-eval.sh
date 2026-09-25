#!/usr/bin/env bash
# Run one eval task against a local LM Studio model.
#
#   ./run-eval.sh <task-file> [model-id]
#   ./run-eval.sh tasks/01-plate.md qwen2.5-coder-14b-instruct
#
# Output lands in results/<model>__<task>.py

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROJ="$(cd "$HERE/.." && pwd)"
BRIDGE="$PROJ/../Mac Mini Setup/tools/lm_studio_bridge.py"
RULES="$PROJ/prompts/fusion-cad-agent-rules.md"

TASK="${1:?usage: run-eval.sh <task-file> [model-id]}"
MODEL="${2:-}"

task_name="$(basename "$TASK" .md)"
model_name="${MODEL:-loaded}"
out="$HERE/results/${model_name//\//_}__${task_name}.py"

mkdir -p "$HERE/results"

args=(--file "$TASK" --system "$(cat "$RULES")" --max-tokens 4096 --temperature 0.2 --output "$out")
[ -n "$MODEL" ] && args+=(--model "$MODEL")

echo "task : $task_name"
echo "model: $model_name"
echo "out  : $out"
echo

time python3 "$BRIDGE" "${args[@]}"

echo
echo "--- wrote $out ---"
