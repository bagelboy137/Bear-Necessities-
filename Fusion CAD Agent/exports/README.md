# exports/

Output geometry from the agent's runs — `.f3d`, `.step`, `.stl`, `.dxf`.

## Notes
- Fusion defaults to saving into the **cloud hub**, not the local disk. Exports must be written here deliberately via `design.exportManager`.
- Binary CAD files don't diff. Keep this folder small — the *spec* and the *script* are the real source of truth and both are text. Geometry here is a build artifact.
- If this folder grows large, add it to `.gitignore` rather than committing revision after revision of the same body.
