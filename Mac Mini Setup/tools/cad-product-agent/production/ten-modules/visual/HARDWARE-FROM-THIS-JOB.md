# Mac mini specs, verified against this job

Input to `Fusion CAD Agent/Hardware-Requirements.md`, which owns the requirement
and `Mac Mini Setup` owns the purchase. This file adds **measurements** where
that file has estimates, and it changes the conclusion in one respect.

Measured 2026-08-26 on the laptop: **Apple M1 Pro, 10 cores, 16 GB, macOS 26.5.2.**

## The headline correction

`Hardware-Requirements.md` sizes the mini on **memory**, on the assumption that a
30B-class coding model and Fusion are resident together. That reasoning is sound
for the *coding* workload and unchanged.

**For this rendering job, memory is not the binding constraint. Cores are.**

| Signal | Measured | What it means |
|---|---|---|
| Fusion `RenderProcess` CPU | **~900–975%** | The ray tracer saturates ~9 of 10 cores. Wall clock scales with core count almost linearly. |
| Free memory during a render | **75–81% of 16 GB** | Never close to pressure. Rendering is not what fills RAM. |
| Fusion app resident | 1.0–1.5 GB | Modest, and it went *down* across modules (1.50 → 1.03 GB) — no leak. |
| `RenderProcess` resident | ~1.5 GB | Modest. |
| Peak for the whole render path | **~3 GB** | Fusion + worker + macOS overhead. |

A 16 GB machine renders this job comfortably. What it does *not* do is render it
quickly, and it cannot host a large local model at the same time.

## Measured render cost

Sixteen successful renders at 2400 × 1800, quality 75:

```
min 35s   max 240s   mean 104s   n=16
```

The spread is framing, not variance. The early wide framing (`distance_factor`
1.35) ran 35–75 s; the final framing (0.95, subject filling ~33% of frame with
ray-traced ground below it) ran **120–240 s**. Budget the higher number.

**One caveat on these numbers.** Several apparent "slow renders" of 9–12 minutes
were not renders at all — they were orphaned workers spinning at ~900% CPU after
their driver was killed, producing nothing and starving the real work. Only runs
whose driver stayed alive are counted above. The whole-tree shutdown now in
`render_module.py` prevents the orphan; it is worth knowing the failure mode
exists because it makes a healthy machine look overloaded.

## What the full sweep costs

```
200 renders x 180s              = 10.0 h
Fusion recycles (~4 per cycle)  =  1.0 h
vision review, 100 modules      =  2.5 h
                                  -------
                                  ~13.5 h  on 10 cores
```

Scaling by cores, holding clock roughly equal:

| Mac mini config | CPU cores | Est. sweep | Notes |
|---|---|---|---|
| M4 | 10 | ~13.5 h | Same core count as the laptop. No improvement on this job. |
| M4 Pro | 12 | ~11.5 h | |
| M4 Pro (upgraded) | **14** | **~10 h** | Best current mini for this workload. |
| M5 Pro / M6 mini | unknown | — | Expected before end of 2026; re-check in October. |

Even at 14 cores this is an overnight job. That is fine — it is designed to run
unattended and to resume — but no mini turns it into an interactive loop.

## The requirement this job adds: GPU contention

Fusion's renderer is Metal-based. So is LM Studio with `--gpu max`. **With a
model resident, renders fire and never complete.** Measured: modules that
rendered in 120–185 s with LM Studio stopped produced nothing in 12 minutes with
a 3 B model loaded.

The sweep now unloads models before rendering and reloads the vision model only
for review. That works on any machine, and it means:

- **More unified memory does not remove this constraint.** It is GPU scheduling,
  not capacity. Do not buy RAM expecting to run Fusion and a model concurrently.
- If you want the model resident *while* Fusion renders, that is a second machine
  question, not a bigger-mini question.

## Recommendation

**M4 Pro, 14-core CPU, 48 GB.**

- **14-core** because this job is core-bound and nothing else on the mini's
  roadmap benefits as directly. It is the single spec that shortens the sweep.
- **48 GB** for the reason `Hardware-Requirements.md` already gives — the 30B
  coding model, not this job. This job would be happy with 24 GB. Unified memory
  is not upgradeable, so size it for the coding workload and let rendering
  benefit from the cores.
- 32 GB remains the floor. It runs everything here; it is tight with a 30B model
  and a real assembly, exactly as the existing doc says.

Two things this job does **not** justify:

- **Jumping to a Mac Studio.** The render is core-bound, but not so bound that
  the price step pays for itself on a job that runs overnight anyway.
- **Buying past 48 GB for rendering.** Peak render-path usage is ~3 GB.

## Still unverified before purchase

- **Display requirement.** `Hardware-Requirements.md` flags this and it is still
  open. Fusion needs a window server; whether a mini with no physical display
  renders correctly, or needs an HDMI emulator dongle, is untested. **This job
  cannot run headless if it does not.** Test it on day one.
- **Whether the M5 Pro / M6 mini lands before October**, and what its core counts
  are. If a higher core count arrives at the same price, this job says take it.
- **Render quality vs. time.** Everything above is at quality 75 and 2400 × 1800.
  Dropping quality for iteration cycles and reserving 75 for final images is the
  obvious lever and has not been measured. It may matter more than core count.
