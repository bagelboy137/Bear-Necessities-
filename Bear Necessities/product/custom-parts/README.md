# Custom Parts — keep this list as short as possible

**Design rule: every custom part must be a FLAT plate cuttable on a laser or waterjet from sheet stock.** No machining, no bends, no welds. Flat 2D parts are the cheapest custom parts that exist, they quote instantly from a DXF, and dozens of shops can make them. The moment a part needs a bend or a milled pocket, cost and lead time jump and the drop-ship model gets harder.

## What is genuinely custom — and why

Everything structural is off-the-shelf 80/20 (see `../bom/`). The only thing with no catalog equivalent is the **LOCK** step from the product sheet: securing a module to the vehicle and to other modules. That is also the actual IP.

| # | Part | Why it can't be off-the-shelf | Process |
|---|---|---|---|
| C-01 | Module anchor plate | Bolts into the T-slot on the module base and presents a pin hole at a known position. No catalog part does this. | Laser cut, 1/4" 5052 aluminium |
| C-02 | Vehicle floor bracket | Mates to the anchor plate and bolts to vehicle tie-down points. Vehicle-specific hole pattern. | Laser cut, 1/4" 5052 aluminium |

**The pin itself is NOT custom.** Use an off-the-shelf 1/4" ball-lock or detent quick-release pin. Do not design a pin.

## Deliberately NOT custom
| Item | Use instead |
|---|---|
| Panels | Order cut-to-size from the panel supplier (HDPE / ACM). Cut-to-size is a standard service, not custom fabrication. |
| Handles | Off-the-shelf recessed pull |
| Drawer slides | Off-the-shelf 20" full-extension |
| Corner joints | 80/20 4132 gusseted brackets |
| Levelling feet | Off-the-shelf T-slot glides |

## Open questions before tooling anything
- **C-02 is vehicle-specific.** Every vehicle has a different tie-down pattern. Either ship it undrilled and let the customer drill, offer a few vehicle-specific SKUs, or use a universal slotted pattern. This is a product decision, not a CAD one — and it is the biggest unresolved issue in the drop-ship model.
- Material thickness and pin diameter are assumptions until a load case is defined. What is the worst-case load — a loaded fridge module in a hard stop?
