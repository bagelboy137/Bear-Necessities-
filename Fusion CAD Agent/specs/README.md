# specs/

One file per part: the brief the model works from. A vague brief is the #1 cause of a wrong model, and a local model will not push back — it will confidently build the wrong thing.

## Template — copy this

```markdown
# Part: <name>

**Purpose:** what it does and what it mounts to
**Project:** e.g. Escalade Work
**Status:** draft | modelled | printed/fabricated | installed

## Envelope
- Overall max: L × W × H
- Material: e.g. 6061 aluminium, 6 mm plate / PETG print
- Process: 3D print | laser cut | CNC | hand-fabricated

## Interfaces (the dimensions that must be exact)
| Feature | Dimension | Tolerance | Why |
|---|---|---|---|
| Bolt pattern | 2 × M8 @ 60 mm centres | ±0.2 mm | matches existing chassis holes |

## Loads / constraints
- What it carries, in what direction, and what it must not interfere with.

## Explicitly free
- Everything the model may decide on its own (fillet radii, cosmetic chamfers, rib layout).

## Reference
- Photos, measurements, links to the parent project's notes.
```

## Rule of thumb
If a dimension matters, it goes in **Interfaces** with a tolerance. If it doesn't, put it in **Explicitly free** so the model stops guessing at what it's allowed to touch.
