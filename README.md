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
OpenAI-compatible API. There are two ways to get one.

**Run one in the cloud container.** `cloud-model.sh` installs Ollama, starts it
and pulls a coder model, then prints the build command:

```bash
cd "Bear Necessities/cad"
./cloud-model.sh                 # qwen2.5-coder:7b by default, about 4.7 GB
BN_LM_STUDIO_URL=http://127.0.0.1:11434/v1 \
BN_REVIEWER_MODEL=qwen2.5-coder:7b \
./build.sh parts
```

Ollama itself installs from GitHub releases, which the default network policy
allows. The model weights need `registry.ollama.ai` and the Cloudflare storage
it redirects to (`*.r2.cloudflarestorage.com`) allowed in the environment's
Network access settings. Network changes take effect in new sessions. The
container is CPU-only, so expect minutes per part rather than the Mac's ~30 s.

**Or point it at a server you run elsewhere**, via LM Studio's variable
(Ollama's `/v1` endpoint works there too), naming a model it has loaded:

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
