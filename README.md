# Bear-Necessities-
Repo for code for the CAD and business to start up Bear Necessities

A Modular Overland Camp System: bolt-together 1" aluminium extrusion modules
(24"W × 20"D × 18"H) for vehicle camping. Product notes, BOM and build plans are
in `Bear Necessities/`; its `CLAUDE.md` is the best place to start.

## Layout

The three folders keep the same layout they have on the Mac, because the build
finds them relative to each other:

| Folder | What it holds |
|---|---|
| `Bear Necessities/` | The product: build-plans pack, BOM, custom parts, marketing images, and `cad/`, the build front door |
| `Fusion CAD Agent/` | `bncad`, the spec → local model → CadQuery → measure → repair framework, plus part specs and the Fusion bridge |
| `Mac Mini Setup/tools/cad-product-agent/` | The ten-module study: jobs, exports, and the deterministic gates |

## Running it in the cloud (Claude Code on the web)

`.claude/hooks/session-start.sh` runs at the start of every cloud session. It
installs `bubblewrap` (the Linux sandbox for model-written code) and builds the
CadQuery venv at `Fusion CAD Agent/.venv-cq` with `uv`. Once that's done:

```bash
cd "Bear Necessities/cad"
python3 preflight.py --for cad   # readiness check
./build.sh test                  # framework tests + bncad self-tests
./build.sh validate              # all four deterministic gates
```

Both run fully in the cloud: no model, no Fusion, no network.

`./build.sh parts` (building parts from specs) needs an LLM server with an
OpenAI-compatible API. The cloud container has none and can't download one
under the default network policy, so point it at a server you run, via
LM Studio's variable (Ollama's `/v1` endpoint works there too), and name a
model that server has loaded:

```bash
BN_LM_STUDIO_URL=http://your-host:1234/v1 \
BN_REVIEWER_MODEL=qwen2.5-coder-7b-instruct \
./build.sh parts
```

The environment's network policy must allow that host. Anything using Fusion
(`native`, `visuals`, `--fusion`) needs the desktop app and only runs on the Mac.

## Running it on the Mac

Unchanged from before: see `Bear Necessities/cad/README.md` and
`Mac Mini Setup/Setup-Checklist.md` §7d. On macOS, bncad uses `sandbox-exec`.
