#!/usr/bin/env bash
# Local model server for './build.sh parts' in Claude Code on the web.
#
# The cloud container has no LM Studio, so this installs Ollama, starts it, and
# pulls a coder model. Idempotent: re-running reuses whatever is already there.
#
#   ./cloud-model.sh                    # qwen2.5-coder:7b (the default)
#   ./cloud-model.sh qwen2.5-coder:14b  # any Ollama model tag
#
# Then build with the lines it prints. CPU only, so expect minutes per part,
# not the ~30 s the Mac manages.
#
# Network: the program comes from GitHub releases, which the default policy
# allows. The model weights come from registry.ollama.ai, which redirects to
# Cloudflare storage (*.r2.cloudflarestorage.com); both must be allowed.
set -euo pipefail

MODEL="${1:-qwen2.5-coder:7b}"
PREFIX="${BN_OLLAMA_PREFIX:-/opt/ollama}"
OLLAMA="$PREFIX/bin/ollama"
HOST="127.0.0.1:11434"
LOG="${TMPDIR:-/tmp}/bn-ollama.log"

SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"

if [ ! -x "$OLLAMA" ]; then
  echo "==> installing Ollama into $PREFIX"
  command -v zstd >/dev/null 2>&1 || $SUDO apt-get install -y -qq zstd >/dev/null
  tmp="$(mktemp -d)"
  curl -fSL --progress-bar -o "$tmp/ollama.tar.zst" \
    https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64.tar.zst
  $SUDO mkdir -p "$PREFIX"
  $SUDO tar --use-compress-program=unzstd -xf "$tmp/ollama.tar.zst" -C "$PREFIX"
  rm -rf "$tmp"
fi

if ! curl -fsS -m 2 "http://$HOST/api/version" >/dev/null 2>&1; then
  echo "==> starting Ollama on $HOST (log: $LOG)"
  # bncad's system prompt plus a repair round's previous script and errors
  # outgrow Ollama's default context, and truncation fails silently - it
  # looks exactly like a model too weak for the job.
  OLLAMA_HOST="$HOST" OLLAMA_CONTEXT_LENGTH="${BN_OLLAMA_CONTEXT:-16384}" \
    nohup "$OLLAMA" serve >"$LOG" 2>&1 &
  for _ in $(seq 1 30); do
    curl -fsS -m 2 "http://$HOST/api/version" >/dev/null 2>&1 && break
    sleep 1
  done
  curl -fsS -m 2 "http://$HOST/api/version" >/dev/null \
    || { echo "Ollama did not start; see $LOG" >&2; exit 1; }
fi

if ! OLLAMA_HOST="$HOST" "$OLLAMA" list | awk 'NR>1 {print $1}' | grep -qx "$MODEL"; then
  echo "==> pulling $MODEL"
  if ! OLLAMA_HOST="$HOST" "$OLLAMA" pull "$MODEL"; then
    echo >&2
    echo "Could not download $MODEL. If the error says Forbidden, the network" >&2
    echo "policy blocks it: allow registry.ollama.ai and *.r2.cloudflarestorage.com" >&2
    echo "in the environment's Network access settings, then start a new session." >&2
    exit 1
  fi
fi

echo
echo "Ollama is serving $MODEL. Build parts with:"
echo
echo "  BN_LM_STUDIO_URL=http://$HOST/v1 BN_REVIEWER_MODEL=$MODEL ./build.sh parts"
