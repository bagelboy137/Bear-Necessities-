# Local Qwen revision and Mac mini replication framework

This directory records thirty family-wide local-model cycles: ten design,
ten manufacturing, and ten combined. Every cycle reviews all ten modules, so a
complete run contains 300 independently keyed module reviews.

The primary proposer is `qwen/qwen2.5-coder-14b` through LM Studio's
OpenAI-compatible API at `http://127.0.0.1:1234/v1`. On machines with 24 GB or
less, `run_revision_profile.sh auto` selects the installed
`qwen2.5-coder-7b-instruct` MLX model and records a low-memory continuation
policy. Qwen cannot directly edit
or release CAD. Its JSON is accepted only after the runner proves exact module
coverage, schema fields, source IDs, and prohibited-claim rules. `REVISE`
findings become prototype requirements in the append-only ledger; `RETAIN`
findings preserve the already validated visible baseline.

## Run or resume

```bash
./run_revision_profile.sh auto
```

Existing validated cycles are rechecked and resumed by default. Use `--force`
only when intentionally replacing a cycle with a newly hashed model response.
The profile runner preloads one model with a 6,144-token context, one prediction
slot, speculative decoding disabled, a bounded output, a pressure/load guard,
and a per-cycle cool-down. It selects 7B on this 16 GB laptop and 14B on the
32–64 GB Mac mini. See `LM-STUDIO-SAFE-PROFILES.md` for the measured rationale.

`run_mac_mini_replication.sh` executes the complete resumed cycle, BOM,
learning, Fusion build, deterministic validation, and Gemma visual-review path.
It materializes and visually reviews a separate Fusion family after the design
stage (100 reviews), manufacturing stage (200 cumulative reviews), and combined
stage (300 cumulative reviews), then leaves the 300-review family as the final
exports.
Before running it on the Mac mini:

1. Copy the shared Claude folder and run `tools/local-ai/bootstrap-mac-mini.sh`.
2. In LM Studio, expose `qwen/qwen2.5-coder-14b`,
   `qwen2.5-coder-7b-instruct`, and `google/gemma-4-e4b` on port 1234.
3. Open Fusion, enable its local MCP server on port 27182, and keep the user
   logged into the desktop session.
4. Run this script from Terminal. It uses only the Python standard library.

## Persistent learning, accurately described

LM Studio model weights are not retrained by these reviews. Learning is made
reproducible through prompt-time retrieval: the raw responses, validated cycle
records, catalog/source digests, `iteration-ledger.json`, and
`LOCAL-MODEL-ITERATION-LEARNINGS.md` travel with the framework and are injected
into later cycles. This is auditable and portable without pretending the model
has acquired new weights.

## Evidence and purchase boundary

- `review-criteria.json` defines the fixed 30-cycle protocol.
- `module-review-context.json` defines current CAD cues and module constraints.
- `comparable-products.json` contains visual precedents and design lessons.
- `ots-components.json` is the only supplier/SKU vocabulary Qwen may cite.
- `boms/BN-M##-prototype-bom.csv` provides a separate order-linked BOM.
- `boms/all-modules-prototype-bom.csv` is the combined purchasing view.

These are prototype BOMs. Custom-cut panels still need released drawings, and
joint loads, vehicle anchors, exact hardware suffixes, wiring, plumbing, heat,
fit, motion, leak, thermal, vibration, and road tests remain human engineering
gates. A link is not authorization to buy a production quantity.
