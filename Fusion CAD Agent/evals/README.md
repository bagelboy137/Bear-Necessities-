# evals/

The purpose of this folder is to answer **one question with evidence instead of vibes: is a given local model good enough to be worth a $1,000+ machine?**

Run the same fixed set of prompts against each candidate model, score them the same way, and record it. Do this **before** October's purchase — the result decides both the model and the RAM tier.

## How to run one
```bash
python3 "../../Mac Mini Setup/tools/lm_studio_bridge.py" \
  --file eval-set.md \
  --model <model-id> \
  --output "results/<model>-<task>.py"
```
Then run the produced script in Fusion and score it.

## Scoring — per task
| Score | Meaning |
|---|---|
| 3 | Runs first try, geometry correct |
| 2 | Runs first try, geometry wrong or off-dimension |
| 1 | Errors, but self-corrects when handed the traceback |
| 0 | Errors and cannot recover, or hallucinates API methods |

**The bar that matters is not "can it write Python."** It's whether it knows the *Fusion API* specifically — most models write fluent Python and invent Fusion method names that don't exist. Score 0 is the expected failure mode.

## What to record per model
Model + quant, RAM used while loaded, tokens/sec, score per task, and total. Write it into `../Memory.md` so the purchase decision has real numbers behind it.

## Also run the control
Run the same set asking for **OpenSCAD** or **CadQuery** instead of Fusion API. If those score materially higher — likely, given training-data volume — the whole architecture should change to generate-and-import. That comparison is the single highest-value thing in this folder.
