# Vehicle Measurement Worksheet — unblocking the C-02 queue

Every vehicle job in `C-02-vehicle-queue.json` is blocked on this data. Fill one per vehicle, set that job's `status` to `READY`, add a `spec` file, then run:

```bash
python3 "../../../Fusion CAD Agent/bridge/run_queue.py"
```

## Why this is gated rather than estimated
Factory cargo tie-down spacing is **not published** for these vehicles — I checked. A model asked to guess will produce confident, wrong numbers, and the result is a bracket that does not bolt to the vehicle. Wrong hole spacing is the most expensive error available to this project, so the queue refuses to run without real measurements.

## Three ways to get the numbers, best first
1. **Measure a real vehicle.** Calipers on the anchor bolts, tape between centres. Highest confidence.
2. **OEM body repair manual / parts diagram.** Often gives anchor locations. Free via dealer parts sites for some brands.
3. **Aftermarket vendor drawings.** Companies selling drawer systems for these vehicles have already solved this. Their published mounting templates are a shortcut — check licensing before copying.

Do **not** source these from forum posts without corroboration.

---

## Worksheet — copy per vehicle

```
VEHICLE: ______________________  YEARS: __________  BODY: ________________
MEASURED BY: __________________  DATE: __________  METHOD: measured / OEM doc / vendor

ANCHOR POINTS (cargo floor)
  Number of usable anchors:        ______
  Spacing, left-right (X):         ______ in   +/- ______
  Spacing, front-back (Y):         ______ in   +/- ______
  Anchor type:   loop / D-ring / threaded boss / L-track / other: __________
  Thread size (if threaded):       __________
  Anchor protrudes above floor by: ______ in
  Load rating (if marked):         ______ lb

CARGO BAY ENVELOPE  (does a 24 x 20 x 18in module even fit?)
  Width between wheel wells:       ______ in     <-- must exceed 24.0
  Width at floor, widest:          ______ in
  Usable length, seats up:         ______ in
  Usable length, seats folded:     ______ in
  Height to window line:           ______ in     <-- must exceed 18.0
  Tailgate/liftgate opening W x H: ______ x ______ in   <-- module must pass through

FLOOR
  Flat / contoured / stepped:      __________
  Removable floor panel?           yes / no
  Anything structural underneath (tank, spare, wiring)?  __________________

NOTES / PHOTOS
  ______________________________________________________________________
```

---

## Suggested order

Do the **Subaru first** — not because it is the biggest market, but because it is the one most likely to **fail the fit check**. A 24" module between Outback wheel wells is genuinely uncertain. If it does not fit, that job leaves the queue entirely and you have saved the effort.

Then **4Runner** (highest overland volume), then **Sprinter** (may already have factory L-track and need no custom part at all).

Two of the ten could disappear on inspection. Confirm before designing.
