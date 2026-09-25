# Running the visual sweep on the Mac mini

The ten-cycle marketing-render sweep, packaged to run unattended on the mini.
Written 2026-08-26 from a laptop run that found every fault listed below the hard
way. Nothing here is theoretical — each guard exists because something broke.

## What the job is

```
10 cycles  x  10 modules  x  2 views (hero + alpha)  =  200 ray-traced renders
```

Each cycle renders every module, scores the images with a model-free gate, asks a
local vision model a fixed checklist, and adjusts one global scene parameter.
Completed work is recorded, so the sweep resumes rather than restarting.

## Prerequisites on the mini

| Requirement | Why |
|---|---|
| A **real GUI session, logged in** | Fusion has no headless mode on macOS. This is already in the `Mac Mini Setup` plan (auto-login, FileVault off). |
| Fusion installed and **signed in** | It phones home; a signed-out Fusion cannot render. |
| Fusion MCP server enabled | Preferences → General → API → Fusion MCP Server. |
| LM Studio installed with `lms` on PATH | The sweep drives it directly to load and unload models. |
| `qwen2.5-vl-3b-instruct` downloaded | The vision checklist. Bigger is fine on the mini — see the spec note. |
| The CadQuery venv | `python3 "Bear Necessities/cad/preflight.py" --for cad` prints the command if missing. |

Do **not** pre-load models. The sweep unloads them itself before rendering; see
"GPU contention" below.

## Run it

```bash
cd "Bear Necessities/cad" && python3 preflight.py --for visuals
```

Then:

```bash
cd "Mac Mini Setup/tools/cad-product-agent/production/ten-modules/visual" && ./run.sh
```

`run.sh` is a thin wrapper that logs to a timestamped file and survives logout.
To resume after any interruption, run the same command — finished renders are
skipped.

## The five faults this job hit, and the guard for each

Every one of these was diagnosed on the laptop. They are properties of Fusion and
of this workload, not of that machine, so expect them on the mini too.

**1. Fusion wedges if you touch the render environment too early.**
Assigning `sceneSettings.backgroundEnvironment` for the first time while a
freshly imported 113-component design is open hangs Fusion permanently — alive at
0% CPU, every later API call blocking. *Guard:* the render stack is warmed on an
empty document first, which costs about a second and makes the same assignment
instant. Cold-then-heavy wedged 6 times out of 6; warm-first has never wedged.

**2. The MCP port is not stable.** After a crash-relaunch Fusion came back on
27180 rather than the documented 27182, and every tool pinned to the old number
reported Fusion missing while it was running fine. *Guard:* `bridge/fusion_port.py`
asks the OS which ports Fusion holds and confirms each with a real MCP handshake.
Nothing anywhere names a port.

**3. Killing Fusion orphans a nine-core process.** The local render worker lives
under `Contents/Libraries`, not `Contents/MacOS`, and does not die with its
parent. One was found reparented to init at 888% CPU, 12 minutes in, producing
nothing. *Guard:* shutdown takes the whole `Contents` tree and sweeps survivors.

**4. LM Studio and Fusion contend for the GPU.** Fusion's renderer is Metal-based
and so is LM Studio with `--gpu max`. With a model resident, renders fire and
never complete. *Guard:* the sweep unloads all models before rendering and loads
the vision model back only for the review phase. **This is why you must not
pre-load models.**

**5. Never close a document.** `Document.close(False)` on a never-saved import
raises a modal save prompt, and a modal dialog blocks every API call. *Guard:*
documents are never closed; Fusion is recycled instead, which discards them
silently. A graceful quit is attempted first so the crash reporter stays quiet —
its dialog is modal too, and would wedge the next launch.

## Watching it

The driver's output is streamed, not captured, so the log shows per-module
progress, Fusion memory and every recycle. A silent log means a stall.

```bash
tail -f visual/sweep-*.log
```

Per-render health goes to `render-telemetry.json`; the Fusion-side step trace to
`render-trace.log`. If something hangs, the trace names the exact line.

## Expected wall clock

Measured on a 10-core M1 Pro: **35–240 s per render**, mean 104 s over 16
successful renders. The spread is framing, not noise — the early wide framing ran
35–75 s, the final closer framing 120–240 s, because the subject and the
ray-traced ground fill far more of the frame.

At the final framing, budget **~180 s per render**:

```
200 renders x 180s              = 10.0 h
Fusion recycles (~4/cycle)      =  1.0 h
vision review, 100 modules      =  2.5 h
                                  -------
                                  ~13.5 h on a 10-core M1 Pro
```

See `HARDWARE-FROM-THIS-JOB.md` for what that implies for the mini, and for the
levers that shorten it.

## If you only want the images, not the iteration

Ten cycles is for convergence. One pass over the family is:

```bash
python3 render_module.py --all --views hero front detail
```

That is 40 renders, roughly 2 hours, and produces the full deliverable set at the
current scene settings without any model in the loop.
