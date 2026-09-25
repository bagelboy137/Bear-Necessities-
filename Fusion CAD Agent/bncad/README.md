# bncad — local-model CAD, headless first, Fusion when it's open

Describe a part in a JSON spec, and a model running on this machine writes
CadQuery, builds a real solid, gets measured, and repairs itself until the
numbers match. No Anthropic API in the loop. No cloud.

```bash
cd "Fusion CAD Agent"
.venv-cq/bin/python -m bncad doctor           # what works right now
.venv-cq/bin/python -m bncad build P01-plate  # generate, validate, export
```

## Why CadQuery is the workhorse and Fusion is the finisher

Fusion is the preferred design environment and that has not changed. It just
cannot be the thing that runs unattended:

| | CadQuery | Fusion |
|---|---|---|
| Headless | yes | **no** — no headless mode exists |
| Needs a GUI session | no | yes, signed in |
| Available at 3am | yes | only if the app is still up |
| Survives an hour at full tilt on 16 GB | yes | **no** — crashed mid-batch 2026-08-26 |
| Parametric feature tree | no | yes |

So CadQuery builds and measures the geometry unattended, and Fusion picks up the
STEP when it is running. `bncad build --fusion` does the handoff and, usefully,
**measures the same STEP in both kernels** — if CadQuery and Fusion disagree
about a file, the file is the problem, not either kernel.

## The loop

```
part spec (JSON)
      ↓
local model (LM Studio or Ollama)  →  CadQuery script
      ↓
AST guard          rejects dangerous code with a message the model can fix
      ↓
sandbox-exec/bwrap writes confined to the run dir, network denied
      ↓
STEP on disk  →  measure  →  check against the spec
      ↓                            ↓
      ↓                    errors with real numbers
      ↓                            ↓
   PASS: export           model repairs those specific numbers, retries
```

The repair signal is the whole design. `"Volume is 0.2255 in^3, expected 0.1963
in^3 (+0.0291 off, tolerance +/-0.0040). Too much material..."` converges.
`"invalid"` does not — a 30-cycle sweep in this project once died because a
check said only "length/type invalid" and the model, not knowing it was 27
characters over, guessed and came back longer. **Every failure message here
carries the measured value, the wanted value and the delta**, and a test
enforces that.

## Units - read this before trusting any file

**CadQuery always writes `SI_UNIT(.MILLI.,.METRE.)` into a STEP.** There is no
exporter option for it, and setting OCCT's `write.step.unit` silently does
nothing. So a part authored with the numbers `4.0 x 1.5 x 0.25` inches produces
a file that every correct reader interprets as **4.0 x 1.5 x 0.25 millimetres**.

This is not theoretical. The first Fusion handoff imported a validated C-01
anchor plate and Fusion reported it as **0.157 x 0.059 x 0.010 in** - the part
25.4x too small. CadQuery said the geometry was perfect, and it was; the file
just claimed the wrong units. A supplier's CAM would have read it the same way,
and nothing else in the pipeline would have objected.

So bncad separates *authoring* from *delivery*:

| File | Units | Role |
|---|---|---|
| `_work-<id>/<id>-authored.step` | the spec's numbers, mislabelled | what the model wrote |
| `<id>.step`, `<id>.stl` | **real millimetres** | the deliverable, and what gets measured |
| `<id>-REJECTED.step` | millimetres | the closest attempt of a run that **failed**. Never send this |

A file named `<id>.step` exists only when that part passed. A failed run writes
`-REJECTED` instead, and a later passing run clears it — so a name without a
suffix always means "this met its spec".

`measure(step, scale=25.4)` reads the millimetre file and returns inches, so the
checks compare like with like. **The file that is validated is the file that
leaves the building** - the alternative is validating one artefact and shipping
another, which is how this project ended up with a green report over a stale
gate once already.

`bncad check` applies the spec's units automatically; pass `--raw` to check an
authored file whose numbers are already in the spec's units.

A spec's `"units"` may be `in`, `mm`, `cm` or `m`. An unknown unit is refused
rather than assumed.

## Part specs

One JSON file per part in `specs/parts/`. The same file feeds the prompt *and*
the validator, which is why adding a part no longer means writing a program.

```json
{
  "id": "P01-plate",
  "name": "two-hole flat plate",
  "units": "in",
  "description": "A flat rectangular plate ... two mounting holes ...",
  "constants": {"LENGTH": 4.0, "WIDTH": 1.5, "THICKNESS": 0.25},
  "checks": {
    "bbox": [4.0, 1.5, 0.25], "bbox_tol": 0.01,
    "volume": 1.45558, "volume_tol": 0.01,
    "solids": 1, "valid": true,
    "holes": [{"d": 0.281, "count": 2}], "holes_exact": true
  },
  "notes": "Hole centres at x = -1.000 and x = +1.000, both at y = 0."
}
```

Available checks: `bbox` (exact overall size) and `bbox_tol`; `size_max` (must
fit inside an envelope) and `size_min`; `volume` and `volume_tol`; `solids`;
`valid`; `watertight`; `faces`; `center` and `center_tol`; `holes` and
`holes_exact`.

**An unknown key is refused, not ignored.** A spec written with `volumne` for
`volume` used to lose that gate in silence — a solid of 99 in³ with no holes at
all passed a spec that meant to check both, reporting zero errors. Loading now
fails and names the offending key.

A `holes` entry takes `d`, `count`, `tol`, `at`, `at_tol`, and either `through`
or `depth`:

```json
"holes": [{"d": 0.281, "count": 2, "at": [[-1.0, 0.0], [1.0, 0.0]], "through": true}]
```

`at` is the position **in the plane the hole's axis is normal to** — for a hole
drilled down Z, that is (x, y). Include it: two holes of the right diameter in
the wrong place change volume by exactly zero, leave the bounding box untouched
and satisfy `holes_exact`, so a mirrored or mis-spaced bolt pattern is invisible
to every other gate. It went unchecked until an audit found it, on a product
whose open blocker is a bolt pattern.

`through` compares the hole's depth to the bounding box along its axis, so it
only means anything where the material is **uniform** along that axis — a plate,
not an L-bracket, whose bounding box is the whole part. Use an explicit `depth`
for anything else. `bncad reference` picks the right one for you.

`size_max`/`size_min` are deliberately *not* called `bbox_max`/`bbox_min`:
`measure()` returns a `bbox_min` of its own meaning the minimum corner
**coordinate**, and a shared name would let a measured `[-2.0, -0.75, 0.0]` be
pasted into a spec as a "minimum size" that passes anything.

**Target numbers must be measured, not calculated in your head.** Every spec here
was checked against a reference solid built in `specs/reference/`, and a test
asserts each spec still validates its own reference. A spec with a wrong target
volume can never converge, and the model gets blamed for it.

### Adding a part

1. Write the spec's `id`, `name`, `description`, `units` and `notes`. Give
   `checks` a placeholder — `{"solids": 1}` is enough to load.
2. Build the shape once by hand in CadQuery and export an **authored** STEP
   (numbered in the spec's units) anywhere outside `specs/reference/`.
3. `python -m bncad reference <id> /path/to/authored.step`

   This converts it into the millimetre reference solid and prints the
   measurements **back in the spec's units**, ready to paste into `checks`.
4. Paste them in, re-run step 3 — it should say the spec matches.
5. `python -m bncad build <id>` — let the model reproduce it from the prose.

Use `reference`, not `check`, for step 3. Measuring a hand-exported STEP as
though it were a delivery divides every number by 25.4, which is the same units
trap in a new coat. `reference` also refuses to convert a file onto itself,
because doing so would rescale the reference by 25.4 on every run.

Step 5 is the real test of the *description*: if the model cannot get there from
the prose, a supplier will not either.

Add the hand-written builder to `specs/reference/build_references.py` as well.
That script rebuilds every reference solid from source and re-checks it against
its spec, so the references stay reproducible instead of becoming binaries
nobody can regenerate or adjust:

```bash
.venv-cq/bin/python specs/reference/build_references.py
```

## Providers

LM Studio (`:1234`) and Ollama (`:11434`), auto-discovered, both OpenAI-shaped.

```bash
python -m bncad models                       # everything live, on both
python -m bncad build P01-plate --model qwen2.5-coder-7b-instruct
python -m bncad build P01-plate --model ollama/qwen3:8b
```

`--model` takes a bare id or `provider/model`. `BN_MODEL` sets a default. A typo
fails immediately against the real roster instead of 90 seconds later with a 404.

Reasoning models (`qwen3`) return a scratchpad that often contains a *draft* code
fence. It is stripped before extraction, and the extractor takes the **last**
fenced block, because models sketch before they answer.

## Safety

Generated code is model-written Python running on a personal machine, so it gets
both a static guard and a real sandbox:

- **AST allowlist** — only `cadquery`, `math`, `json`, `OCP`. `subprocess`,
  `socket`, `shutil`, `os`, `eval`, `exec`, `open` and friends are refused *with
  a message the model can act on*, which is the point of having it as well as
  the sandbox.
- **`sandbox-exec`** — writes confined to that run's directory, network denied,
  enforced by the kernel. The child gets a `TMPDIR` inside its run directory so
  the profile never has to open up the shared system temp root. It did once, and
  the test suite escaped through it within a minute.
  On Linux (Claude Code on the web) the same guarantee comes from **`bwrap`**
  (bubblewrap): the filesystem is bound read-only, the run directory read-write,
  and every namespace — including the network — is unshared. There is no
  unconfined fallback on either platform; `doctor` blocks if the tool is missing.
- **Timeout** — a runaway boolean is killed and reported as a timeout, not a hang.

## Commands

| Command | Does |
|---|---|
| `doctor` | what works right now, and the exact fix for what does not |
| `models` | every model on every live provider |
| `specs` | the part library |
| `build <spec>` | the loop. `--fusion` hands off, `--attempts`, `--model`, `--keep` |
| `check <spec> <step>` | validate an existing STEP against a spec. `--raw` for an authored file |
| `reference <spec> <step>` | turn a hand-built STEP into the spec's reference solid, and print paste-ready measurements |
| `fusion <step>` | import into the live Fusion session and cross-check. `--units` |
| `bench` | score models across the spec library. `--repeat N` exposes variance |
| `selftest` | every module demo plus the suite — no model, no Fusion, no network |

## Running unattended

Verified against the conditions a scheduler actually imposes, not just a login
shell. What was found and fixed while checking:

- **`lsof` is not on a cron PATH.** It lives in `/usr/sbin`, so Fusion's
  port-discovery fallback silently returned nothing under a scheduled run - the
  exact failure the discovery exists to prevent, reappearing only where nobody
  was watching. It is now called by absolute path.
- **Two builds of the same part raced.** They share `_work-<id>`, which is
  cleared on entry, so the second run deleted the first run's files and the
  first died with `FileNotFoundError`. A lock now refuses the second run rather
  than letting them race.

  The lock is an **`flock`, held by the kernel** - not a pid written in a file.
  The first attempt at this did track a pid and "take over" when that pid looked
  dead, which had three separate problems on a machine that runs for months: two
  processes could both judge a lock stale, and the second would then unlink the
  first's *live* lock; a recycled pid made a dead lock look alive forever; and a
  SIGKILL or reboot left a file nothing would clear. `flock` has none of them -
  the OS drops it when the process dies, however it dies. Verified by SIGKILLing
  a build mid-run and immediately rebuilding the same part.
- **A relative interpreter path** failed with `execvp() ... No such file or
  directory` and was reported to the model as though it had written bad code.
- **`Path.resolve()` on a venv interpreter leaves the venv.** A uv venv's
  `bin/python` is a symlink to the base interpreter, so resolving it turned
  every `import cadquery` into `ModuleNotFoundError`. `abspath`, never
  `resolve`, for an interpreter.

### Exit codes

A wrapper can branch on these without parsing messages:

| Code | Means |
|---|---|
| `0` | success |
| `1` | the build ran and did not meet the spec, or a gate failed |
| `2` | configuration: no such model, no provider answering, unknown spec, unwritable output directory |
| `3` | busy: another build of this part is running in that output directory |

`3` is deliberately distinct from `1` — a scheduled run that collided with a
manual one has not failed, it has declined to race. `bench` re-raises rather
than scoring a busy part as a model failure: a scoreboard should never contain a
result for a part that was never built.

### What is bounded

- **Disk.** Each part's deliverables are overwritten by name on every run, so
  building the same parts nightly does not accumulate — measured constant across
  repeated runs. A failing run's `_work-<id>` survives for inspection and is
  cleared by that part's next build.
- **The per-run JSON.** ~2.7 KB for a two-attempt run, ~8 KB for a six-attempt
  one. It is capped by `--attempts`, not by how long the machine has been up.
- **Time.** Every model call and every sandboxed script has a timeout that
  actually fires — verified against a server that accepts a connection and never
  answers. Worst case for one part is `attempts × timeout`, so with the defaults
  (8 × 900s) a wedged model server costs two hours per part before the run gives
  up. **For a scheduled job, pass a short `--timeout`** — a healthy call takes
  seconds, so `--timeout 180` still leaves an enormous margin and caps a wedged
  night at 24 minutes a part. There is no separate total-budget flag: the two
  knobs already bound it, and a third would just be another number to get wrong.
- **CPU, even if this process dies.** The sandboxed child sets its own
  `ulimit -t` before exec. A subprocess timeout only works while the parent is
  alive; kill the loop mid-execution — jetsam under memory pressure is the
  realistic way — and the child was orphaned and spun at 100% CPU forever.
  Reproduced, then fixed, then re-tested by abandoning a child deliberately.

### Cron and launchd

Give it an absolute path and let it find everything else:

```bash
/path/to/Claude/Fusion\ CAD\ Agent/bncad.sh build C-01-anchor-plate >> /tmp/bncad.log 2>&1
```

Verified working under `env -i PATH=/usr/bin:/bin` with no TTY: doctor, a full
build, and Fusion port discovery. Output is line-buffered so a log file shows
progress rather than appearing hung.

## Running on the Mac mini

Nothing here hard-codes a home directory. The package resolves paths relative to
itself and takes machine-specific values from the environment:

| Variable | Default |
|---|---|
| `BN_SPEC_DIR` | `Fusion CAD Agent/specs/parts` |
| `BN_OUT_DIR` | `Fusion CAD Agent/exports/bncad` |
| `BN_MODEL` | first available model |
| `BN_LMSTUDIO_URL` | `http://127.0.0.1:1234/v1` |
| `BN_OLLAMA_URL` | `http://127.0.0.1:11434/v1` |
| `BN_FUSION_MCP_URL` | discovered — Fusion's port moves, so it is asked for, not assumed |

First build the CadQuery environment. **Use uv** - it fetches the interpreter as
well, and a fresh Mac has no system `python3.12` for the plain `venv` command to
run. This is how the working venv here was actually built:

```bash
uv venv --python 3.12 "Fusion CAD Agent/.venv-cq"
uv pip install --python "Fusion CAD Agent/.venv-cq/bin/python" cadquery
```

After that, the change is the model, not the code:

```bash
export BN_MODEL=qwen/qwen3-coder-30b
python -m bncad bench          # prove it beats the 14B on this fixture first
```

`bench` is how that claim gets settled with numbers rather than assumed from
parameter count.

### What is different on this laptop

16 GB, and macOS lets the GPU address only ~70% of it, so this is effectively an
11 GB machine for weights. The 14B (~8.3 GB) is the ceiling here. Fusion and a
large model should not be resident at once — the headless path avoids the
question entirely, which is the main reason it is the default.

## Tests

```bash
.venv-cq/bin/python -m bncad selftest
```

No model, no Fusion, no network — it runs unattended. What it covers:

- every spec validates its own reference solid
- every check is shown **rejecting** bad geometry as well as accepting good
- the units conversion, in both directions and on volume as well as length
- the guard refuses dangerous imports and calls
- the sandbox is proven to actually block an escape and deny the network,
  rather than merely intending to
- a harness fault is distinguished from a model error, in both directions

The count is deliberately not written down here — it went stale twice already.
