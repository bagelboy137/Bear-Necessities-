# Hardware Requirements — for `Mac Mini Setup`

What this project needs from the mini. **`Mac Mini Setup` owns the purchase decision; this file is input to it, not a competing plan.**

## The change this project forces

`Mac Mini Setup` currently targets **32GB**, sized on the assumption that the mini runs *a local coding model* plus Claude Dispatch. This project puts **Autodesk Fusion on the same machine at the same time**, which the 32GB math did not account for.

| Resident at once | Rough footprint |
|---|---|
| Coding model, 30B-class at Q4 (e.g. Qwen3-Coder-30B) | ~19GB (**estimate was high — see measured table below**) |
| Coding model, 24B-class at Q4 (e.g. Devstral-24B) | ~14GB |
| Autodesk Fusion 360, non-trivial assembly open | several GB, grows with model complexity |
| macOS + Dispatch + the rest | a few GB |

**Verdict: 32GB is the floor, not the target.** It works with a 24B model and a simple part. It gets tight with a 30B model and a real assembly. If the budget stretches, **48–64GB** is the config that makes this comfortable — and per `Mac Mini Setup`, unified memory is *not* upgradeable after purchase, so this is a one-shot decision.

This does not by itself justify jumping to a Mac Studio. It does mean: re-run the 32-vs-64 comparison before buying, with this workload in the model.

## Measured update, 2026-08-26 — cores matter more than the memory math suggested

The marketing-render sweep was built and run, and it measures the Fusion side of
this machine directly. Full evidence in
`Mac Mini Setup/tools/cad-product-agent/production/ten-modules/visual/HARDWARE-FROM-THIS-JOB.md`.

The memory reasoning above is unchanged and still correct **for the coding
model**. But for rendering:

- **Rendering is core-bound, not memory-bound.** Fusion's ray tracer runs at
  ~900–975% CPU — about 9 of 10 cores — while free memory sits at 75–81% of
  16 GB. The whole render path peaks around 3 GB.
- **A render takes 120–240 s** at 2400 × 1800, quality 75. The full ten-cycle
  sweep is ~13.5 h on 10 cores, ~10 h on 14. Overnight either way.
- **Fusion and a local model cannot share the GPU.** Both are Metal-based; with a
  3 B model resident, renders fire and never complete. This is scheduling, not
  capacity — **more unified memory does not fix it**, so do not buy RAM expecting
  to run Fusion and a model concurrently. The sweep sequences them instead.

**Revised recommendation: M4 Pro with the 14-core CPU upgrade, 48 GB.** The core
upgrade is what shortens this job; the 48 GB is still for the coding model, as
argued above. 32 GB remains the floor. This does not change the "not a Mac
Studio" verdict.

## Measured model footprint, 2026-08-26 — the estimates above were high

Read from the actual MLX 4-bit repo rather than estimated. This file said ~19GB
and `Software-Requirements.md` said ~17GB; they disagreed and both were high.

| Item | Real number |
|---|---|
| `Qwen3-Coder-30B-A3B-Instruct-MLX-4bit` weights | **16.0 GiB** |
| KV cache @ 8k / 16k / 32k ctx (fp16) | 0.75 / 1.50 / **3.00** GiB |
| KV cache @ 128k ctx (fp16) | 12.0 GiB |

Architecture: `qwen3_moe`, 48 layers, 128 experts with 8 active per token,
4 KV heads. All experts stay resident — 30B-sized in memory, 3B-sized in compute.
The narrow KV cache (4 KV heads) is why long context is affordable here.

**Coding model at 32k context = ~19 GiB total.** Against ~45 GiB addressable on
a 64GB machine, memory is not the binding constraint for this workload.

### What this means for 48GB vs 64GB

The "Fusion and the model are co-resident" framing overstates the case, because
the GPU-contention finding below means they must be **sequenced** for rendering
anyway — and sequenced, peak memory is `max(model, Fusion)`, not the sum.

The real 64GB argument is model-plus-model, not model-plus-Fusion:

| Scenario | Need | 48GB (~34 GiB) | 64GB (~45 GiB) |
|---|---|---|---|
| Coder @ 32k + vision | ~26 GiB | fits | fits |
| Coder @ 128k + vision | ~35 GiB | **exceeds** | fits |

64GB buys long-context agentic coding with the vision model co-resident, and
headroom that cannot be added later. That is a narrower claim than this file
previously made, and it is the one that survives the measurements.

### Still unmeasured: Fusion *open* but not rendering

The contention below was measured against Fusion's **ray tracer**. The actual
CAD agent loop — Fusion executing Python API scripts, viewport only — has never
been tested with a model resident. That is the case that matters most for daily
use and it is still an assumption. Testable on the laptop today with
`bonsai-27b` (7.94 GiB, known to load) and a real assembly open, no rendering.

## Non-memory requirements

- **GUI session, always logged in.** Fusion has no headless mode on macOS — it must be running in a real desktop session. Already compatible with the existing decisions (FileVault off, auto-login, unattended reboot recovery).
- **Network access.** Fusion requires periodic Autodesk sign-in and defaults to cloud storage. An air-gapped mini cannot run Fusion for long. The *model* is offline; the CAD app is not.
- **Disk.** Fusion plus its cache, plus a local model library, plus exported geometry. The existing plan (512GB internal + external Thunderbolt SSD as needed) still holds, but Fusion pushes toward using that external sooner.
- **Display.** Fusion wants a display attached or a virtual one; a fully headless mini may need a display emulator dongle for the GPU/window server to behave. **Still unverified, and now load-bearing:** the render sweep cannot run unattended at all if a headless mini will not drive the window server. Test this on day one.

## Action for October
Before buying, re-check: 32GB vs 48/64GB pricing, whether the M5 mini has landed (it may offer a better memory tier at the same price), and whether Fusion runs acceptably on a mini with no physical display.
