# Bear Necessities — CAD build front door

This folder is the entry point for building the module family. It holds no
geometry of its own; it resolves where everything lives and drives it.

Run `./build.sh` from here on **either machine**. Nothing in this folder assumes
a home directory or a machine — every machine-specific value comes from
`runtime.json` or a `BN_*` environment variable.

## Where the pieces actually live

| Thing | Path | Owner |
|---|---|---|
| Product decisions, BOM, custom parts | `Bear Necessities/product/` | this project |
| Ten-module study, jobs, exports, gates | `Mac Mini Setup/tools/cad-product-agent/production/ten-modules/` | Mac Mini Setup |
| Orchestration framework | `Mac Mini Setup/tools/cad-product-agent/` | Mac Mini Setup |
| CadQuery/Fusion bridges, specs, venvs | `Fusion CAD Agent/` | Fusion CAD Agent |
| Local model roster and roles | `Mac Mini Setup/tools/local-ai/model-profiles.json` | Mac Mini Setup |

The study currently lives under `Mac Mini Setup` even though it is Bear
Necessities product data. That is backwards, but moving ~200 tracked binary
artifacts is a separate decision — this front door exists so the location can
change without every command changing with it.

## Commands

```bash
python3 preflight.py            # what would fail if I built right now?
./build.sh test                 # framework test suites (19 tests)
./build.sh validate             # deterministic gates only: no model, no Fusion
./build.sh parts                # build parts from JSON specs (needs a local model)
./build.sh revision             # local-model review cycles (needs LM Studio)
./build.sh native               # rebuild native Fusion family (needs Fusion + LM Studio)
./build.sh all                  # revision, then native, then validate
```

`preflight.py --for cad|revision|native|all` scopes the check to what a given
stage actually needs, and `--json` makes it machine-readable for a scheduled run.

## The three build paths, by what they require

| Path | Needs | Runs unattended |
|---|---|---|
| `test` | the project CadQuery venv | yes |
| `validate` | Python only | yes |
| `parts` | a local model (LM Studio or Ollama) | yes |
| `revision` | LM Studio + the `cad-review` model | yes |
| `native` | the above **plus** Fusion running with its MCP server | no — Fusion must be signed in and open |

`validate`, `revision` and `parts` are the overnight-safe paths - `parts` builds
real solids headlessly through CadQuery, which is why it does not need Fusion.
Framework and part specs live in `../Fusion CAD Agent/bncad/`; read its README's
units section before sending any STEP to a supplier. `native` is not: Fusion's
MCP server at `127.0.0.1:27182` only exists while the app is running, which is
the single biggest constraint on making the mini fully autonomous.

## Running on the Mac mini

The same checkout works unchanged if the layout is preserved. If it is not:

```bash
export BN_CLAUDE_ROOT=/path/to/Claude
export BN_REVIEWER_MODEL=qwen/qwen3-coder-30b   # only after it beats the 14B on this fixture
./build.sh all
```

Preflight prints the models LM Studio actually has loaded when a required one is
missing, so a roster mismatch is a one-line diagnosis rather than a stack trace.

## Which interpreter

`build.sh test` uses the project venv (`Fusion CAD Agent/.venv-cq`, Python 3.12)
because the suites import `cadquery` and `ezdxf`. Running them with the system
`python3` — 3.9 from Xcode on this laptop — drops the drawing tests to an import
error that reads like a skip. `preflight.py --for cad` checks that venv exists and
prints the exact command to create it if it does not.

## Resumability

The revision loop writes one validated file per cycle and reuses it on the next
run. An interrupted 30-cycle sweep resumes where it stopped — it does not restart.
That matters: a full sweep is 300 module reviews through a local model.
