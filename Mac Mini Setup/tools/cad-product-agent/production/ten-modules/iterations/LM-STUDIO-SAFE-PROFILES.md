# LM Studio safe execution profiles

## Why the laptop profile exists

On 2026-08-25 the 16 GB M1 Pro MacBook kernel-panicked twice while LM Studio's
14B MLX Node/Metal worker was generating consecutive review cycles. Both panic
logs reported `completeMemory() prepare count underflow` in `IOGPUMemory.cpp`
with `IOGPUFamily` in the backtrace and `node` as the panicked task. Compressor
and swap status were reported as healthy, so the framework treats this as a GPU
memory-lifecycle failure rather than an ordinary Python exception.

LM Studio's own estimates at a 6,144-token context were:

- Qwen2.5 Coder 14B MLX 4-bit: 10.86 GiB GPU/total memory.
- Qwen2.5 Coder 7B MLX 4-bit: 5.60 GiB GPU/total memory.

The measured review workload peaked at 2,850 prompt tokens, 1,596 completion
tokens, and 4,446 total tokens across the first twelve completed cycles. A
6,144-token context and 1,800-token output cap therefore retain practical
headroom without the 8,192-token default allocation.

## Profiles

`laptop-safe` (24 GB RAM or less): 7B MLX, 6,144 context, one prediction,
speculative decoding off, 1,800 output-token cap, 30-second cool-down, load
average ceiling 20, and pressure-aware free-memory floor 30 percent.

`mac-mini` (more than 24 GB): primary 14B MLX, 6,144 context, one prediction,
speculative decoding off, 2,000 output-token cap, five-second cool-down, load
ceiling 32, and free-memory floor 20 percent.

The 16 GB laptop does **not** run the full local-VLM release batch. Gemma was
estimated at 8.95 GiB and Qwen3.5 9B at 7.79 GiB, so both were rejected for the
laptop. A Qwen2.5-VL 3B MLX canary loaded at 2.88 GiB and completed one image,
but LM Studio's native endpoint silently created a second parallel-4 instance;
free memory fell from 74 to 32 percent. Its JSON was also contradictory: PASS
with populated blocking findings. Both instances were immediately unloaded.

Laptop visual evidence therefore uses direct inspection of every render,
bound to each current image SHA-256, plus deterministic geometry cues and
current comparable/OTS web evidence. The full local-VLM batch remains in the
Mac mini profile, using `google/gemma-4-e4b`, reasoning off, a 3,072-token
request context, one stage at a time, and resource guards. The replication
script unloads the coder before Fusion/vision and unloads all models at the end.

Run `./run_revision_profile.sh auto`. Validated files are resumable, and every
ledger record retains its actual model ID. A mixed 14B/7B run is accepted only
under the explicit `documented_low_memory_continuation` policy; model weights
are never described as retrained.
