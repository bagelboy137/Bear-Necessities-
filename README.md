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

## Connecting Claude to Fusion

There are two Fusion MCP servers, and which one a session can use depends on
where it runs.

**Desktop Fusion, on the Mac.** `.mcp.json` registers `fusion-desktop`, which
runs `Fusion CAD Agent/bridge/fusion_mcp_proxy.py` in front of the MCP server
built into Fusion. The proxy finds Fusion's port (it moves), reconnects after a
relaunch, refuses the script patterns that hang Fusion, logs every change, and
adds `bn_snapshot` (a before/after inventory) and `bn_fusion_status`. To use
it: open Fusion with a design, tick Preferences > General > API > Fusion MCP
Server, start Claude Code (the CLI or the desktop app) in this folder, and
approve `fusion-desktop` when asked. Claude Desktop's own Autodesk Fusion
connector reaches the same server without the proxy.

**Fusion Compute, from anywhere, including cloud sessions.** Autodesk runs
headless Fusion as a public-beta MCP server at
`https://developer.api.autodesk.com/da/v3/mcp/fusion`. It needs an Autodesk
sign-in, a Fusion licence and a Fusion Team hub, and works on files in Fusion
Team. For cloud sessions, add it as a custom connector at
claude.ai/customize/connectors and sign in; on the Mac,
`claude mcp add --scope user --transport http fusion-compute https://developer.api.autodesk.com/da/v3/mcp/fusion`.

In a cloud session `fusion-desktop` still starts, and its `bn_fusion_status`
explains why desktop Fusion is out of reach. How Claude should work in either
one is in `.claude/skills/fusion-cad/SKILL.md`. The research behind it is in
`Fusion CAD Agent/reference/ai-cad-best-practices.md`.

## Running it on the Mac

Unchanged from before: see `Bear Necessities/cad/README.md` and
`Mac Mini Setup/Setup-Checklist.md` §7d. On macOS, bncad uses `sandbox-exec`.
