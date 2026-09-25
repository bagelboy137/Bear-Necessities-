#!/usr/bin/env bash
# bncad launcher - runnable from anywhere, including cron and launchd.
#
# Picks the interpreter that actually has CadQuery. Running bncad under the
# system python3 (3.9 from Xcode on the laptop) fails at import with a message
# that reads like a missing package rather than a wrong interpreter.
#
#   ./bncad.sh doctor
#   ./bncad.sh build P01-plate --model qwen2.5-coder-7b-instruct
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/.venv-cq/bin/python"

if [ ! -x "$PY" ]; then
  echo "No CadQuery interpreter at $PY" >&2
  echo "Create it with uv, which fetches the interpreter as well:" >&2
  echo "  uv venv --python 3.12 '$HERE/.venv-cq'" >&2
  echo "  uv pip install --python '$PY' cadquery" >&2
  echo "(A fresh Mac has no system python3.12, so uv is the reliable path -" >&2
  echo " this venv was built that way.)" >&2
  exit 1
fi

cd "$HERE"
exec "$PY" -m bncad "$@"
