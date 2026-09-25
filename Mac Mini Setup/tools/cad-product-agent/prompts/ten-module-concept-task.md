Design ten distinct modules for the Bear Necessities Modular Overland Camp System.

Reference image facts: the product family uses interchangeable 24 inch wide x
20 inch deep x 18 inch high rectangular frames made from silver 1 x 1 inch
T-slot aluminum extrusion. The image shows cook, storage, fridge, sink, water,
and gear/utility examples, with dark infill panels, drawers/shelves, carry
handles, and vehicle locking pins. Modules slide into an SUV and are removable.

Hard manufacturing constraints:
- Preserve the common 24 W x 20 D x 18 H external envelope.
- Preserve the frame cut strategy: 1010-compatible extrusion, eight 18 inch
  pieces and four 22 inch pieces per outer frame. Do not invent part numbers.
- Prefer supplier cut-to-length extrusion and commercially orderable hardware.
- Custom fabricated parts must be flat laser/waterjet-cut sheet with no bends,
  welds, or machining unless explicitly flagged as a production blocker.
- Catalog part numbers will be independently curated; name component categories,
  performance requirements, dimensions, and quantities instead of guessing SKUs.
- Account for rough-road vibration, tie-downs, ventilation, water containment,
  hot surfaces, payload, center of gravity, service access, and lift-out weight.
- Do not claim structural or regulatory approval.

Return strict JSON with one top-level object containing:
- `family_assumptions`: array
- `modules`: exactly 10 objects, each with `id`, `name`, `customer_job`,
  `configuration`, `frame_extrusion` (18-inch quantity and 22-inch quantity),
  `off_the_shelf_components` (name, quantity, key_specification),
  `custom_parts` (name, quantity, flat_sheet_possible, reason),
  `critical_interfaces`, `safety_checks`, `estimated_payload_lb`,
  `estimated_empty_weight_lb`, and `production_blockers`
- `shared_components`: array
- `design_rules_learned`: array of concise rules suitable for adding to an
  automated CAD planning prompt
- `recommended_build_order`: all ten module IDs in test priority order

Make the ten concepts meaningfully different and commercially useful. Include
the six pictured functions but improve them where appropriate, then add four
complementary products. Keep every claim conservative and manufacturable.
