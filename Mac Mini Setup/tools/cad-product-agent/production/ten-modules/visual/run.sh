#!/usr/bin/env bash
# Launch the visual sweep on the Mac mini. See RUN-ON-MAC-MINI.md.
#
# Resumable: finished renders are recorded in render-progress.json and skipped,
# so re-running after any interruption continues rather than restarting.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CYCLES="${1:-10}"
STAMP="$(date +%Y%m%d-%H%M%S)"
LOG="$HERE/sweep-$STAMP.log"

# The CadQuery venv has PIL and numpy; the system python does not.
ROOT="$HERE"
while [ "$ROOT" != "/" ] && [ ! -d "$ROOT/Fusion CAD Agent" ]; do
  ROOT="$(dirname "$ROOT")"
done
PY="$ROOT/Fusion CAD Agent/.venv-cq/bin/python"
if [ ! -x "$PY" ]; then
  echo "missing CadQuery venv at $PY" >&2
  echo "run: python3 \"$ROOT/Bear Necessities/cad/preflight.py\" --for cad" >&2
  exit 1
fi

echo "sweep: $CYCLES cycle(s), logging to $LOG"
echo "watch with: tail -f $LOG"

# -u so the log is written as it happens; a silent log must mean a stall, not
# buffering. nohup so the run survives the session that started it.
nohup "$PY" -u "$HERE/run_visual_cycles.py" --cycles "$CYCLES" > "$LOG" 2>&1 &
echo "started pid $!"
