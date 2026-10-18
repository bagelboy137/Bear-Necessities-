// snapshot.ts - read-only inventory of the active design, for Fusion Compute's
// MCP.ExecuteTypeScript. A port of "Fusion CAD Agent/bridge/fusion_snapshot.py"
// (the desktop proxy's bn_snapshot): same JSON shape, fewer sections.
//
// UNTESTED against Fusion Compute. Written from Autodesk's API reference and the
// Python original. First use: run it on a part whose numbers you know (C-01 or
// P01 - their specs are in "Fusion CAD Agent/specs/parts/") and compare. If a
// section reports an error, look the member up with fusion_api_index, fix it
// here, and delete this paragraph once it has run clean.
//
// Set UNITS, then send the whole file as the script. It is a bare script: no
// import or export, `adsk` is already in scope, and the result leaves through
// `adsk.result`, which must be spelled exactly like that.

type Design = import("@adsk/fusion").adsk.fusion.Design;

const UNITS = "in"; // "in" | "mm" | "cm"
// Fusion's API is centimetres whatever the document displays.
const SCALE = UNITS === "in" ? 1 / 2.54 : UNITS === "mm" ? 10 : 1;
const LIMIT = 400;
const len = (v: number) => Math.round(v * SCALE * 1e4) / 1e4;
const vol = (v: number) => Math.round(v * SCALE * SCALE * SCALE * 1e4) / 1e4;

const out: { [key: string]: unknown } = { units: UNITS };

// Each section stands alone, so one renamed member costs one section.
function section(name: string, fn: () => unknown): void {
  try {
    out[name] = fn();
  } catch (e) {
    out[name] = { error: String(e) };
  }
}

const app = adsk.core.Application.get();
const design = app.activeProduct as Design;

section("document", () => {
  const doc = app.activeDocument;
  const data = doc.dataFile;
  return {
    name: doc.name,
    modified: doc.isModified,
    id: data ? data.id : null,
    version: data ? data.versionNumber : null,
  };
});

if (!design || !design.rootComponent) {
  out["error"] = "the active product is not a Fusion design";
} else {
  const root = design.rootComponent;

  section("bodies", () => {
    const rows: unknown[] = [];
    const add = (selector: string, b: any) => {
      const lo = b.boundingBox.minPoint;
      const hi = b.boundingBox.maxPoint;
      rows.push({
        selector,
        visible: b.isVisible,
        solid: b.isSolid,
        volume: vol(b.volume),
        bbox: {
          min: [len(lo.x), len(lo.y), len(lo.z)],
          max: [len(hi.x), len(hi.y), len(hi.z)],
          size: [len(hi.x - lo.x), len(hi.y - lo.y), len(hi.z - lo.z)],
        },
      });
    };
    for (let i = 0; i < root.bRepBodies.count; i++) {
      const b = root.bRepBodies.item(i);
      add("root::" + b.name, b);
    }
    const occs = root.allOccurrences;
    for (let i = 0; i < occs.count; i++) {
      const occ = occs.item(i);
      for (let j = 0; j < occ.bRepBodies.count; j++) {
        const b = occ.bRepBodies.item(j);
        add(occ.fullPathName + "::" + b.name, b);
      }
    }
    return { count: rows.length, items: rows.slice(0, LIMIT), truncated: rows.length > LIMIT };
  });

  if (design.designType === adsk.fusion.DesignTypes.ParametricDesignType) {
    section("timeline", () => {
      const tl = design.timeline;
      const unhealthy: unknown[] = [];
      let suppressed = 0;
      for (let i = 0; i < tl.count; i++) {
        const item = tl.item(i);
        if (item.isSuppressed) suppressed++;
        const entity: any = item.entity;
        if (entity && entity.healthState !== undefined &&
            entity.healthState !== adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState) {
          unhealthy.push({ name: item.name, message: entity.errorOrWarningMessage });
        }
      }
      return { count: tl.count, marker: tl.markerPosition, suppressed, unhealthy };
    });
  }

  section("user_parameters", () => {
    const rows: unknown[] = [];
    const params = design.userParameters;
    for (let i = 0; i < params.count; i++) {
      const p = params.item(i);
      rows.push({ name: p.name, expression: p.expression, unit: p.unit, comment: p.comment });
    }
    return rows;
  });

  section("joints", () => ({
    count: root.allJoints.length,
    as_built: root.allAsBuiltJoints.length,
    rigid_groups: root.allRigidGroups.length,
  }));
}

adsk.result = JSON.stringify(out);
