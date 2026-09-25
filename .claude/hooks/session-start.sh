#!/bin/bash
# SessionStart hook for Claude Code on the web: makes the Bear Necessities CAD
# build runnable in a fresh Linux cloud container. Idempotent; local runs skip it.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
VENV="$ROOT/Fusion CAD Agent/.venv-cq"

# bncad runs model-written code under bubblewrap on Linux (sandbox-exec on
# macOS). It refuses to run generated code unconfined, so this is required.
if ! command -v bwrap >/dev/null 2>&1; then
  SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
  $SUDO apt-get install -y -qq bubblewrap >/dev/null 2>&1 \
    || { $SUDO apt-get update -qq >/dev/null 2>&1 && $SUDO apt-get install -y -qq bubblewrap >/dev/null; }
fi

# The CadQuery venv, built the same documented way as on the Mac: uv fetches
# Python 3.12 as well, so the system interpreter version does not matter.
if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install -q --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi
if [ ! -x "$VENV/bin/python" ]; then
  uv venv -q --python 3.12 "$VENV"
fi
uv pip install -q --python "$VENV/bin/python" cadquery ezdxf

echo "Bear Necessities CAD environment ready: $("$VENV/bin/python" -c 'import cadquery; print("cadquery", cadquery.__version__)'), $(command -v bwrap)" >&2
