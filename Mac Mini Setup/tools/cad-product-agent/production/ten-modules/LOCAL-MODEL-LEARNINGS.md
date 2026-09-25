# Local-model learning record — ten-module study

## Model and evidence

- Model: `qwen/qwen2.5-coder-14b`, MLX 4-bit, run locally through LM Studio.
- Raw concept result: `../../ten-module-local-model-output.json`.
- Raw CAD result: `local-model-cad-response.md`.
- Validated implementation: `build_ten_modules.py`.

## Failures observed

1. “JSON only” was insufficient: the concept result omitted quotes around several
   keys and therefore was not valid JSON.
2. The model invented product requirements and safety claims (for example
   arbitrary wattages and UL statements) without sources.
3. It treated commercially plausible components as packageable without checking
   the frame's true internal clear region.
4. Generated CadQuery used nonexistent instance export methods and nested a
   compound with Workplanes instead of making one compound from Shapes.
5. It duplicated the module table rather than defining one reusable data source.
6. The inherited BOM combined 4132 external brackets with 3395 internal anchor
   fasteners. Manufacturer evidence showed 4132 calls for two 3393 assemblies;
   3395/AF-010 is a separate counterbored joint architecture.

## Repairs promoted into the framework

- Planning and review prompts now require six-face checks against the internal
  clear envelope, not merely the outside bounding box.
- BOM items require explicit dispositions and rejected candidates remain visible
  at quantity zero.
- The family validator checks ten unique IDs, the two-length extrusion invariant,
  internal clearance, every STEP/STL/SVG/JSON artifact, BOM vocabulary, and
  rejected-item zero quantities.
- CAD prompts retain copyable member-table scaffolding because local models apply
  spatial patterns reliably but do not derive them reliably.
- Supplier SKUs and compliance claims remain curated human/web inputs; the model
  is never allowed to invent them.
- The geometry generator now reads `module-family.json` directly, eliminating its
  duplicated hard-coded module table.
- Ten generated jobs and separate clearance/BOM evidence reports make each
  prototype independently gateable.

## Native Fusion/API pass — 2026-08-25

- Fusion's built-in MCP server at `http://127.0.0.1:27182/mcp` is now the
  authoritative execution path. The reusable client performs initialize plus
  `notifications/initialized`, verifies Execute/Read/Update availability, and
  preserves server exceptions.
- Every module is created in a fresh direct-design document and exported as a
  separate F3D/STEP/STL/OBJ package. Product geometry is organized as named
  native components; a monolithic body or one anonymous envelope cannot pass.
- Stable Fusion appearances are copied from locale-independent library IDs and
  assigned to bodies. This preserved silver aluminum, dark panels, controls,
  water colors, straps, screens, and soft goods in F3D and OBJ/MTL.
- ViewCube-relative `Front` and `IsoTopRight` views looked at the closed rear of
  the product on this installation. The framework now uses explicit camera eye,
  target, and up vectors from the open customer-facing side.
- The current OBJ API requires `createOBJExportOptions(geometry, filename)`;
  constructing it without a filename failed before any partial family could be
  accepted. Component evidence is counted from the persisted part registry,
  not the nonexistent `rootComponent.allComponents` property.
- Visual QA must be iterative. The first native files were structurally detailed
  but hid burners, drawers, and the sink behind panels/countertops. Direct image
  inspection drove explicit camera correction, an open sink well, an open pantry
  divider tray, readable geometric module badges, visible shower connectors,
  contrasting straps, and exposed water/office service equipment.
- LM Studio's Gemma vision model does not accept this server's optional
  `json_object` response-format parameter. The reviewer uses ordinary chat output,
  parses answer or reasoning channels, retries malformed responses, hashes every
  image, and remains advisory to the deterministic gate.
- Final evidence requires three independent views of completion: named-feature
  and file/dimension checks, direct visual inspection against current comparable
  products, and a local-VLM pass over all ten current image hashes.

## Next evals before production use

1. Require valid output against a JSON Schema on three repeated passes.
2. Test a repair loop seeded with the exact CadQuery traceback from this run.
3. Add collision/access envelopes for lids, drawers, hoses and wiring.
4. Extend the now-working native multi-component assemblies with engineering
   joints, interference/motion envelopes, and parameterized fabrication features.
5. Benchmark the 30B-class Mac mini model on this exact ten-module fixture and
   compare first-pass schema validity, API correctness, and packaging rejections.
