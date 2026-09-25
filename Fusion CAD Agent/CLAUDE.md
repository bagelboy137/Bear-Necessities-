# Claude.md — Fusion CAD Agent

Working memory for **Fusion CAD Agent**: a local, offline LLM that authors real
CAD geometry, headless, with Autodesk Fusion as the finishing environment.

*Folder created 2026-08-20 under the standing scaffolding rule.*

## Goal
Describe a part in plain language → a local model writes CAD code → a real solid
appears → errors feed back for another pass. No Anthropic API in the loop.

**Status 2026-08-27: this works end to end.** A spec goes in, a local 7B writes
CadQuery, the solid is built in a sandbox, measured, repaired until it matches
its spec, and imported into live Fusion where Fusion's own kernel confirms the
same dimensions.

## Scope boundary vs. other projects
| Project | Owns |
|---|---|
| **Mac Mini Setup** | The machine — purchase, RAM target, always-on config, the LM Studio toolkit |
| **Fusion CAD Agent** (here) | The CAD side — model choice, the bridges, prompts, part specs, evals |
| **Bear Necessities** | The product these parts are for; its `cad/` is the build front door |
| **Escalade Work** | The most likely first real consumer of parts made here |

## Architecture — two tiers, decided 2026-08-27

```
part spec (JSON)  →  local model  →  CadQuery script
                                          ↓
                            AST guard + sandbox-exec
                                          ↓
                     millimetre STEP/STL  →  measure  →  check
                                          ↓                ↓
                                   PASS: deliver     numeric errors → repair
                                          ↓
                           live Fusion (optional): import + cross-check
```

**CadQuery is the workhorse; Fusion is the finisher.** Not a downgrade — a
division of labour forced by facts:

| | CadQuery | Fusion |
|---|---|---|
| Headless | yes | **no**, none exists |
| Runs unattended at 3am | yes | only while the app is up and signed in |
| Survives an hour at full tilt on 16 GB | yes | **no** — crashed mid-batch 2026-08-26 |
| Parametric feature tree | no | yes |

Fusion's MCP server is still the right live bridge, and is used both for the
handoff and for an independent measurement. It just cannot be the thing that
runs all night.

### This answers the old open question
The 2026-08-20 note asked whether to script Fusion's API directly or generate a
neutral format, with 7B evidence favouring neutral. **Settled: neutral format,
via CadQuery.** Both paths are kept — CadQuery builds, Fusion receives.

## The hard constraint nobody should discover later
**Fusion is not an offline application.** It needs an Autodesk sign-in and
phones home; Autodesk supports only a limited offline stretch before demanding
re-authentication. **The model is offline. Fusion is not.** The headless path
exists partly so a network-flaky day does not stop work.

## The units trap — the most expensive bug found here
**CadQuery always stamps `SI_UNIT(.MILLI.,.METRE.)` into a STEP.** No exporter
option changes it, and OCCT's `write.step.unit` silently does nothing. A part
authored as `4.0 × 1.5 × 0.25` inches therefore describes **millimetres** to
every reader.

The first Fusion handoff proved it: a fully validated C-01 anchor plate imported
as **0.157 × 0.059 × 0.010 in** — 25.4× too small. CadQuery was right about the
geometry; the file lied about its units, and a supplier's CAM would have read it
exactly the same way.

`bncad` now converts to real millimetres before anything is measured, so the
file that gets validated is the file that gets delivered. The test suite
guards it in both directions, and the guard was mutation-tested: swapping the
two files turns the suite red.

## Fusion MCP gotchas, found the hard way — still true
- Handshake needs `initialize` **then** a `notifications/initialized`
  notification. Without the second, everything returns "Session not
  initialized". Session id comes back in the `MCP-Session-Id` response header.
- Entry point is `def run(_context: str):` — underscore and type hint.
- **The port moves.** Documented 27182; observed 27180 after a crash-relaunch,
  and 27180 again on 2026-08-27. `bridge/fusion_port.py` asks the OS rather than
  trusting a literal, and it earned its keep today.
- **Fusion wraps script stdout in a JSON envelope** — `{"message": "...",
  "success": true}` — so scanning for a line that *starts with* your marker
  finds nothing. `bncad/fusion.py` handles both shapes.
- **Fusion's API is centimetres** regardless of document units.
- **`rootComponent.name` cannot be set** — it raises.
- **Deleting bodies does not clear a parametric design**; the timeline
  regenerates them. Add a fresh document per run instead.
- Never close a document from a script — the save prompt is modal and blocks the
  API.

## Key paths on this machine
| What | Path |
|---|---|
| **Fusion app** | `~/Library/Application Support/Autodesk/webdeploy/production/Autodesk Fusion.app` — **not** in `/Applications` |
| Fusion MCP | discovered, not assumed; 27180 today |
| LM Studio | `http://127.0.0.1:1234/v1` (8 models) |
| Ollama | `http://127.0.0.1:11434/v1` (qwen3:8b) |
| CadQuery venv | `.venv-cq/` — Python 3.12.14, cadquery 2.8.0 |

## What's built (reuse, don't rebuild)
| Thing | Does |
|---|---|
| `bncad/` | **The framework.** Spec → model → sandbox → measure → repair → deliver. See its README |
| `bncad.sh` | Launcher that picks the interpreter with CadQuery. Cron-safe |
| `bridge/fusion_mcp.py` | Minimal MCP client for the live Fusion session |
| `bridge/fusion_port.py` | Finds the port Fusion is really on |
| `bridge/cq_loop.py`, `cad_loop.py` | The earlier single-part loops that bncad generalises |
| `specs/parts/*.json` | Six part specs, each validated against a reference solid |
| `Mac Mini Setup/tools/local-ai/` | LM Studio config, autostart, health checks |

## Benchmark, 2026-08-27 (16 GB M1 Pro, six parts)

**Read the second table before the first.** The first sweep ran while other
things held memory, and it produced a conclusion that later turned out to be
wrong.

| Model | Passed | Median | Conditions |
|---|---|---|---|
| qwen2.5-coder-7b-instruct | 9/12 runs | 28 s | 2 runs per part |
| qwen/qwen2.5-coder-14b | 5/6 | **933 s** | 1 run per part, older prompt, memory contended |
| ollama/qwen3:8b | 1/5 | ~1200 s | general reasoning model |

7B detail, two runs each: BN-FRAME, C-01, P01, P05 all **2/2**; C-02-U **1/2**
(genuinely marginal); P06 **0/2**.

### Then the same 14B, with memory free and the improved prompt

| Part | 14B | 7B, for comparison |
|---|---|---|
| C-02-U-floor-bracket | **6/6**, ~30 s, first attempt each time | 1/2 |
| P06-l-bracket | **5/7**, ~31 s when it lands | 0/2 |

Everything else builds first attempt in about thirty seconds. `P06-l-bracket`
is genuinely marginal on the 14B — not solved, not impossible — which is what a
benchmark part is for.

**Two earlier conclusions were wrong, and this is the correction:**

1. **P06 is not a capability ceiling.** It failed 0/2 on the 7B and 6/6 on the
   14B *under the old prompt*, and that looked like a model limit. With the
   selector, cut-a-cylinder and box-orientation rules added, the 14B builds it
   in about thirty seconds. **The prompt was the ceiling, not the model.**
2. **The 14B was never slow, it was starved.** 933 s median under contention
   became **29–51 s** with memory free — a 20–30× swing from nothing but
   available RAM. It is simultaneously the faster *and* the more accurate model
   here once it can breathe.

So: **all six parts are buildable.** The 7B is the right pick when something
else needs the memory; the 14B is better in every way when it does not — which
is the normal condition on a mini with more RAM.

**Model class still beats model size.** qwen3:8b is a general *reasoning* model:
it imported `FreeCAD`, invented `fillet(segments=4)`, and returned unparseable
output on parts the smaller **coder** models build first try. Do not choose by
parameter count or reasoning ability - run `bncad bench --repeat` and read the
pass *rate*.

**And repeats are not optional.** C-02-U passing 1/2 on the 7B, and P06 passing
3/4 on the 14B, are facts a single run reports as a clean yes or a clean no.
Both readings would have been wrong.

## Production readiness (verified 2026-08-28)

Checked against the conditions a mini imposes, not a login shell: a relocated
checkout, a venv built from the documented command, cron's minimal environment,
overlapping runs, SIGKILL, unwritable output. Every defect was reproduced before
being fixed, and each reproduction is now a test.

The full sequence was run end to end from a clean `git archive` of HEAD:
preflight blocks without a venv → the documented `uv` command fixes it →
preflight passes → 67 self-tests pass under `env -i PATH=/usr/bin:/bin` → all
six reference solids rebuild and match → all four deterministic gates pass →
the part library builds 5/6 under that same cron environment.

What that shook out, beyond the benchmark: `lsof` is not on a cron PATH (Fusion
port discovery silently died there); overlapping builds destroyed each other
(now an `flock`, kernel-released on death); a SIGKILLed run orphaned a child at
100% CPU forever (the child now carries its own `ulimit -t`); and three gates
were *measured and never enforced* — a misspelled check key silently deleted its
gate, and hole position and depth were never checked at all, so a mirrored bolt
pattern or a blind hole passed everything.

Setup day is covered in `Mac Mini Setup/Setup-Checklist.md` §7d.

## Open questions
1. ~~Direct Fusion API or neutral format?~~ **Answered: neutral (CadQuery).**
2. ~~Manual run or watcher add-in?~~ **Neither** — Fusion's MCP server is the
   bridge, and the headless path removes the need for unattended Fusion.
3. **Which model on the mini?** Run `bncad bench` there before believing any
   parameter count. The 14B's poor showing here is a memory artefact.
4. **What's the first real part?** An Escalade bracket remains the obvious
   candidate — a real need with a measurable pass/fail.
5. **Does P06 pass on a bigger model?** Untested; the laptop cannot feed one
   fast enough to find out cheaply.

## Next steps
1. Run `bncad bench` on the mini once it exists; settle the model question.
2. Add the first Escalade part as a spec and build it.
3. Consider retiring `bridge/cq_loop.py` and its three hand-written
   `cq_validate_*.py` files now that bncad covers them.
