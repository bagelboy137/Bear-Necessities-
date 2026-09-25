# Software Requirements — laptop trial

Audited on this machine (Apple M1 Pro, 16GB, macOS 25.5) on 2026-08-20.

## Already installed — nothing to do

| Software | State |
|---|---|
| **Autodesk Fusion 360** | Installed. Versions `2703.1.20` / `2704.1.36` in the add-in cache. `API/Scripts/` and `API/AddIns/` exist and are empty |
| **LM Studio** | Installed, service runs, server live on port `1234` |
| **`lms` CLI** | `~/.lmstudio/bin/lms`, already on PATH via line 3 of `~/.zshrc` |
| **Python 3** | 3.9.6 at `/usr/bin/python3`. Enough — `lm_studio_bridge.py` is stdlib-only |
| **The bridge** | `../Mac Mini Setup/tools/lm_studio_bridge.py`, working |

## Being added

| Software | Why |
|---|---|
| **Qwen2.5-Coder-14B-Instruct (MLX 4-bit, ~8.3GB)** | The coding model. See "Model choice" below |

## Recommended — one manual install

**OpenSCAD** — https://openscad.org/downloads.html (free, drag to Applications).

Not required to make Fusion work. It exists to run the **control test**: the same parts, asked for in OpenSCAD instead of the Fusion API. Model training data contains far more OpenSCAD than Fusion API code, so this is the fastest way to find out whether direct Fusion scripting is the right architecture at all. It also has a headless CLI, so results can be rendered without opening the GUI:

```bash
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o out.stl in.scad
```

## Deliberately skipped for the trial

- **CadQuery** — the other neutral-format candidate, but system Python here is 3.9 and CadQuery wants 3.10+, so it needs `uv` or miniforge and its own environment. Higher setup cost than OpenSCAD for the same question. Revisit only if OpenSCAD wins the control test and you want a Python-native version of it.
- **Homebrew** — not installed. Nothing here needs it; OpenSCAD ships as a normal `.app`.
- **The watcher add-in** — unattended execution is a mini-era concern. For the trial, run scripts by hand from Fusion's Scripts and Add-Ins dialog.

## RESOLVED 2026-08-20 — the 14B runs, and setup is now scripted

The 14B was initially blocked by LM Studio's memory guardrail, which **over-estimated it at 10.86 GiB when it actually loads at 7.75 GiB**. Fixed by setting `modelLoadingGuardrails.mode: "off"`.

The whole LM Studio setup is now a tested toolkit at `../Mac Mini Setup/tools/local-ai/` — config, autostart, model downloads, and a 13-point health check, all replicable onto the mini. Don't hand-configure LM Studio; run those scripts.

## Model choice — why Qwen2.5-Coder-14B

**The binding constraint is not the 16GB.** macOS only lets the GPU address roughly **70% of unified memory**, so this is effectively an **~11GB machine** for model weights unless `iogpu.wired_limit_mb` is raised (currently `0`, i.e. default).

Catalog options checked against that ceiling:

| Model | ~Size @ 4-bit | Fits ~11GB? |
|---|---|---|
| **qwen/qwen2.5-coder-14b** | ~8.3GB | ✅ **chosen** — comfortable, leaves headroom |
| mistralai/devstral-small-2-2512 | ~13GB | ❌ over the cap; would need the sysctl raised and leaves nothing for Fusion |
| qwen/qwen3-coder-30b | **16.0 GiB measured** (was ~17GB est.) | ❌ |
| qwen/qwen2.5-coder-32b | ~18GB | ❌ |
| qwen/qwen3-coder-next (80B MoE) | ~45GB | ❌ |

The three models already on disk (`qwen3.5-9b`, `llama-3.1-8b`, `gemma-4-e4b`) are general-purpose, not coding models — none is a fair test of this workload.

**Run the model and Fusion sequentially, not simultaneously.** Generate the script, `lms unload` the model, then run it in Fusion. That sidesteps the memory contention entirely on this machine and is fine for a trial — it is only the *unattended* mini that needs both resident at once.

## What this trial cannot tell you
Qwen2.5-Coder-14B is the ceiling for 16GB, and it is **two tiers below** what the mini would run (Qwen3-Coder-30B / Devstral). If 14B scores poorly, that is not proof the approach fails — it is a floor, not a verdict. If 14B scores *well*, that is a strong buy signal.
