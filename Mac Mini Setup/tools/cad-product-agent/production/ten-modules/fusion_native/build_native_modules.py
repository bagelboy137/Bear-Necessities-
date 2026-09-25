"""Build the ten Bear Necessities modules in ten separate Fusion documents.

This file is executed inside a live Autodesk Fusion session through Fusion's
built-in MCP server.  All numeric arguments accepted by the geometry helpers
are inches; they are converted to Fusion's native centimetres at the boundary.

Outputs per module:
  <module>/<module>.f3d   native editable Fusion archive
  <module>/<module>.step neutral assembly exchange file
  <module>/<module>.stl  mesh reference
  <module>/<module>.obj  material-capable visualization mesh
  <module>/<module>-iso.png and <module>-front.png
  <module>/<module>-build.json deterministic build evidence

The geometry is intentionally product-concept CAD, not released engineering.
It represents the visible functional details needed for design review and web
visualization while preserving the fixed 24 x 20 x 18 inch family envelope.
"""

import adsk.core
import adsk.fusion
import json
import math
import os
import traceback


IN = 2.54

# The three absolute paths below are PLACEHOLDERS, not configuration.
# run_native_pipeline.py rewrites each of them (single-line regex, and it raises if
# the line is missing) before shipping this file as text into a live Fusion session,
# so the committed values are only ever the machine they were last generated on.
# Drive this through `Bear Necessities/cad/build.sh native` -- running the file
# straight from Fusion's Scripts dialog on another Mac writes to a path that does
# not exist. Each must stay a single assignment line. (Noted 2026-09-02.)
OUT_ROOT = "/Users/cmken/Claude/Mac Mini Setup/tools/cad-product-agent/production/ten-modules/fusion-native/exports"
REVISION_LEDGER_PATH = "/Users/cmken/Claude/Mac Mini Setup/tools/cad-product-agent/production/ten-modules/iterations/runs/iteration-ledger.json"
OTS_CATALOG_PATH = "/Users/cmken/Claude/Mac Mini Setup/tools/cad-product-agent/production/ten-modules/iterations/ots-components.json"

W, D, H, P = 24.0, 20.0, 18.0, 1.0

PALETTE = {
    "aluminum": (185, 190, 196),
    "aluminum_dark": (105, 112, 120),
    "charcoal": (35, 39, 43),
    "black": (13, 15, 17),
    "rubber": (26, 29, 31),
    "blue": (36, 112, 196),
    "blue_dark": (18, 48, 85),
    "screen": (34, 183, 224),
    "white": (226, 230, 232),
    "red": (198, 42, 47),
    "orange": (224, 116, 34),
    "green": (50, 166, 87),
    "tan": (158, 122, 82),
    "rope": (211, 145, 43),
}

MODULES = [
    ("BN-M01", "Cook Station", "build_cook_station"),
    ("BN-M02", "Dry Pantry", "build_dry_pantry"),
    ("BN-M03", "Fridge Freezer", "build_fridge"),
    ("BN-M04", "Sink Wash", "build_sink"),
    ("BN-M05", "Fresh Water", "build_fresh_water"),
    ("BN-M06", "Recovery Utility", "build_recovery"),
    ("BN-M07", "Power Hub", "build_power"),
    ("BN-M08", "Hot Water Shower", "build_hot_water"),
    ("BN-M09", "Field Office Camera", "build_office"),
    ("BN-M10", "Camp Furniture Soft Goods", "build_furniture"),
]

MODULE_OTS = {
    "BN-M01": ["JETBOIL-GENESIS", "ACCURIDE-3832-C16", "SOUTHCO-E3-57-25"],
    "BN-M02": ["RUBBERMAID-FG350700WHT", "ACCURIDE-3832-C16", "SOUTHCO-E3-57-25"],
    "BN-M03": ["ENGEL-MHD13-ALT", "ACCURIDE-3832-C16", "NRS-HD-STRAP"],
    "BN-M04": ["DOMETIC-VA8005", "SHURFLO-4008", "RELIANCE-AQUATAINER-4G", "NRS-HD-STRAP"],
    "BN-M05": ["RELIANCE-AQUATAINER-7G", "SHURFLO-4008", "NRS-HD-STRAP"],
    "BN-M06": ["PELICAN-1450", "ACCURIDE-3832-C16", "NRS-HD-STRAP"],
    "BN-M07": ["ECOFLOW-RIVER3-PLUS", "SOUTHCO-E3-57-25"],
    "BN-M08": ["JOOLCA-HOTTAP-V2", "NRS-HD-STRAP", "SOUTHCO-E3-57-25"],
    "BN-M09": ["PELICAN-1485", "ACCURIDE-3832-C16", "SOUTHCO-E3-57-25"],
    "BN-M10": ["HELINOX-CHAIR-ONE", "HELINOX-TABLE-ONE", "NRS-HD-STRAP"],
}


def load_optional_json(path, fallback):
    try:
        with open(path, "r") as handle:
            return json.load(handle)
    except Exception:
        return fallback


REVISION_LEDGER = load_optional_json(
    REVISION_LEDGER_PATH,
    {"result": "MISSING", "records": [], "module_review_count": 0},
)
OTS_CATALOG = load_optional_json(
    OTS_CATALOG_PATH,
    {"components": []},
)
OTS_BY_ID = {item.get("id"): item for item in OTS_CATALOG.get("components", [])}


class ModuleBuilder:
    def __init__(self, app, design, module_id, title):
        self.app = app
        self.design = design
        self.root = design.rootComponent
        self.module_id = module_id
        self.title = title
        self.temp = adsk.fusion.TemporaryBRepManager.get()
        self.appearances = {}
        self.parts = []
        self.required = []
        self._name_counts = {}
        self.revision_records = [
            item for item in REVISION_LEDGER.get("records", [])
            if item.get("module_id") == module_id
        ]

    def appearance(self, key):
        """Create a locale-independent colored appearance from Prism-129."""
        if key in self.appearances:
            return self.appearances[key]
        rgb = PALETTE[key]
        name = "BN_%s" % key.upper()
        found = self.design.appearances.itemByName(name)
        if found:
            self.appearances[key] = found
            return found
        lib = self.app.materialLibraries.itemById(
            "BA5EE55E-9982-449B-9D66-9F036540E140"
        )
        generic = lib.appearances.itemById("Prism-129")
        copied = self.design.appearances.addByCopy(generic, name)
        color_prop = copied.appearanceProperties.itemById("opaque_albedo")
        color_prop.value = adsk.core.Color.create(rgb[0], rgb[1], rgb[2], 255)
        roughness = copied.appearanceProperties.itemById("surface_roughness")
        if roughness:
            try:
                roughness.value = 0.28 if key == "aluminum" else 0.52
            except Exception:
                pass
        self.appearances[key] = copied
        return copied

    def _unique(self, name):
        n = self._name_counts.get(name, 0) + 1
        self._name_counts[name] = n
        return name if n == 1 else "%s_%02d" % (name, n)

    def _add_body(self, name, temp_body, color="charcoal", cue=None):
        if not temp_body:
            raise RuntimeError("Fusion failed to create body %s" % name)
        uname = self._unique(name)
        occ = self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = uname
        body = comp.bRepBodies.add(temp_body)
        if not body:
            raise RuntimeError("Fusion failed to persist body %s" % uname)
        body.name = uname
        body.appearance = self.appearance(color)
        self.parts.append({"name": uname, "color": color, "cue": cue or ""})
        if cue and cue not in self.required:
            self.required.append(cue)
        return body

    def box(self, name, x, y, z, lx, ly, lz, color="charcoal", cue=None):
        center = adsk.core.Point3D.create(
            (x + lx / 2.0) * IN,
            (y + ly / 2.0) * IN,
            (z + lz / 2.0) * IN,
        )
        obb = adsk.core.OrientedBoundingBox3D.create(
            center,
            adsk.core.Vector3D.create(1, 0, 0),
            adsk.core.Vector3D.create(0, 1, 0),
            lx * IN,
            ly * IN,
            lz * IN,
        )
        return self._add_body(name, self.temp.createBox(obb), color, cue)

    def cyl(self, name, p1, p2, radius, color="black", cue=None):
        a = adsk.core.Point3D.create(p1[0] * IN, p1[1] * IN, p1[2] * IN)
        b = adsk.core.Point3D.create(p2[0] * IN, p2[1] * IN, p2[2] * IN)
        body = self.temp.createCylinderOrCone(a, radius * IN, b, radius * IN)
        return self._add_body(name, body, color, cue)

    def handle(self, name, x, y, z, width=4.0, rise=0.7, color="black", cue=None):
        # Rounded U-pull on the front face (front is Y=0).
        r = 0.13
        self.cyl(name + "_POST_L", (x, y, z), (x, y - rise, z), r, color, cue)
        self.cyl(name + "_POST_R", (x + width, y, z), (x + width, y - rise, z), r, color)
        self.cyl(
            name + "_GRIP",
            (x, y - rise, z),
            (x + width, y - rise, z),
            r,
            color,
        )

    def front_knob(self, name, x, y, z, radius=0.28, color="black", cue=None):
        return self.cyl(name, (x, y, z), (x, y - 0.35, z), radius, color, cue)

    def vent_rows(self, prefix, x, y, z, count=6, length=2.5, vertical=False, cue="vents"):
        for i in range(count):
            if vertical:
                self.box(
                    prefix + "_SLOT",
                    x + i * 0.42,
                    y,
                    z,
                    0.18,
                    0.08,
                    length,
                    "black",
                    cue if i == 0 else None,
                )
            else:
                self.box(
                    prefix + "_SLOT",
                    x,
                    y,
                    z + i * 0.38,
                    length,
                    0.08,
                    0.16,
                    "black",
                    cue if i == 0 else None,
                )

    def slide_pair(self, prefix, x, y, z, width, depth, cue="locking slides"):
        for sx in (x, x + width - 0.22):
            self.box(prefix + "_SLIDE_OUTER", sx, y, z, 0.22, depth, 0.28,
                     "aluminum_dark", cue if sx == x else None)
            self.box(prefix + "_SLIDE_INNER", sx + 0.04, y - 1.6, z + 0.05,
                     0.14, depth + 1.6, 0.17, "aluminum")

    def drawer(self, prefix, x, y, z, width, depth, height, cue="drawer"):
        self.box(prefix + "_CASE", x, y, z, width, depth, height, "charcoal", cue)
        self.box(prefix + "_FRONT", x + 0.10, y - 0.18, z + 0.10,
                 width - 0.20, 0.25, height - 0.20, "aluminum_dark")
        self.handle(prefix + "_HANDLE", x + width / 2 - 2, y - 0.18,
                    z + height * 0.55, cue="pull handle")
        self.front_knob(prefix + "_LATCH", x + width - 0.65, y - 0.23,
                        z + height * 0.58, 0.20, "black", "compression latch")
        self.slide_pair(prefix, x - 0.18, y, z + 0.12, width + 0.36, depth)

    def hose_path(self, prefix, points, radius=0.16, color="blue", cue="hose route"):
        for i in range(len(points) - 1):
            self.cyl(prefix + "_SEG", points[i], points[i + 1], radius,
                     color, cue if i == 0 else None)

    def fastener(self, name, x, y, z, axis="y"):
        if axis == "y":
            self.cyl(name, (x, y, z), (x, y - 0.10, z), 0.11, "aluminum")
        elif axis == "x":
            self.cyl(name, (x, y, z), (x + 0.10, y, z), 0.11, "aluminum")
        else:
            self.cyl(name, (x, y, z), (x, y, z + 0.10), 0.11, "aluminum")

    def add_frame(self):
        # Twelve independent 1-inch 10-Series members at the exact cut lengths.
        members = []
        for x in (0, W - P):
            for y in (0, D - P):
                members.append(("POST", x, y, 0, P, P, H))
        for y in (0, D - P):
            for z in (0, H - P):
                members.append(("WIDTH_RAIL", P, y, z, W - 2 * P, P, P))
        for x in (0, W - P):
            for z in (0, H - P):
                members.append(("DEPTH_RAIL", x, P, z, P, D - 2 * P, P))
        for idx, (kind, x, y, z, lx, ly, lz) in enumerate(members, 1):
            self.box("FRAME_%s_%02d" % (kind, idx), x, y, z, lx, ly, lz,
                     "aluminum", "12 separate 10-Series extrusion members" if idx == 1 else None)

        # Dark T-slot centerlines on the visible front/right/top faces.
        for x in (0.47, W - 0.53):
            self.box("TSLOT_POST_FRONT", x, 0.0, 0.35, 0.06, 0.04, H - 0.7, "black",
                     "visible T-slot lines")
        for z in (0.47, H - 0.53):
            self.box("TSLOT_WIDTH_FRONT", 1.0, 0.0, z, W - 2.0, 0.04, 0.06, "black")
        for z in (0.47, H - 0.53):
            self.box("TSLOT_DEPTH_RIGHT", W - 0.04, 1.0, z,
                     0.04, D - 2.0, 0.06, "black")
        for x in (0.47, W - 0.53):
            self.box("TSLOT_TOP_DEPTH", x, 1.0, H - 0.04,
                     0.06, D - 2.0, 0.04, "black")

        # Back and left infill panels preserve a clear three-quarter product view.
        self.box("BACK_INFILL_PANEL", 1.05, D - 1.12, 1.05,
                 W - 2.10, 0.10, H - 2.10, "charcoal", "dark infill panels")
        self.box("LEFT_INFILL_PANEL", 1.05, 1.05, 1.05,
                 0.10, D - 2.18, H - 2.10, "charcoal")

        # Visible corner plates and bolt heads.
        for x in (0.92, W - 1.22):
            for z in (0.92, H - 1.92):
                self.box("CORNER_GUSSET", x, 0.04, z, 0.30, 0.12, 1.0,
                         "black", "corner hardware")
                self.fastener("GUSSET_BOLT", x + 0.15, 0.12, z + 0.25)
                self.fastener("GUSSET_BOLT", x + 0.15, 0.12, z + 0.75)

    def add_id_plate(self):
        # Hang the badge just below the top rail so it remains visible without
        # protruding outside the 24 x 20 x 18 envelope.
        self.box("MODULE_ID_PLATE_%s" % self.module_id, 9.2, 0.10, 16.15,
                 5.6, 0.10, 0.72, "black", "module ID plate")
        for x in (9.55, 14.25):
            self.box("ID_PLATE_HANGER", x, 0.10, 16.86, 0.20, 0.10, 0.18,
                     "black")
        # Tiny 3x5 block lettering makes M01..M10 real geometry in every CAD
        # exchange format instead of relying on a viewport-only annotation.
        glyphs = {
            "M": ("101", "111", "111", "101", "101"),
            "0": ("111", "101", "101", "101", "111"),
            "1": ("010", "110", "010", "010", "111"),
            "2": ("111", "001", "111", "100", "111"),
            "3": ("111", "001", "111", "001", "111"),
            "4": ("101", "101", "111", "001", "001"),
            "5": ("111", "100", "111", "001", "111"),
            "6": ("111", "100", "111", "101", "111"),
            "7": ("111", "001", "010", "010", "010"),
            "8": ("111", "101", "111", "101", "111"),
            "9": ("111", "101", "111", "001", "111"),
        }
        text = "M" + self.module_id[-2:]
        cell, gap = 0.12, 0.12
        text_width = len(text) * (3 * cell + gap) - gap
        start_x = 12.0 - text_width / 2.0
        for char_index, char in enumerate(text):
            pattern = glyphs[char]
            for row, pixels in enumerate(pattern):
                for col, pixel in enumerate(pixels):
                    if pixel == "1":
                        self.box("ID_TEXT_%s" % char,
                                 start_x + char_index * (3 * cell + gap) + col * cell,
                                 0.04, 16.23 + (4 - row) * cell,
                                 cell * 0.82, 0.05, cell * 0.82, "white")

    def add_manufacturing_details(self):
        """Represent shared OTS hardware selected by the manufacturing framework.

        These are recognizable product-concept features, not exact supplier CAD.
        Exact holes, grip ranges, load paths and tolerances remain release gates.
        """
        # Two internal carry pulls based on the shared HAN-015-AL family.  They
        # remain inside the outer envelope and are not approved lifting points.
        self.handle("OTS_HAN015AL_FRONT_LEFT", 2.0, 0.82, 15.35, 4.0, 0.55,
                    "black", "two shared OTS carry pulls")
        self.handle("OTS_HAN015AL_FRONT_RIGHT", 18.0, 0.82, 15.35, 4.0, 0.55,
                    "black")

        # Anti-skid tread references along the lower rails.
        self.box("OTS_BUM010TS_FRONT", 1.05, 0.02, 0.02, 21.90, 0.12, 0.08,
                 "rubber", "shared anti-skid tread")
        self.box("OTS_BUM010TS_REAR", 1.05, 19.86, 0.02, 21.90, 0.12, 0.08,
                 "rubber")

        # Visible panel-gasket beads on the rear infill perimeter.
        for x, y, z, lx, ly, lz in (
            (1.10, 18.82, 1.10, 21.80, 0.08, 0.08),
            (1.10, 18.82, 16.82, 21.80, 0.08, 0.08),
            (1.10, 18.82, 1.18, 0.08, 0.08, 15.64),
            (22.82, 18.82, 1.18, 0.08, 0.08, 15.64),
        ):
            self.box("OTS_GAS010A_GASKET", x, y, z, lx, ly, lz, "rubber",
                     "shared panel gasket" if x == 1.10 and z == 1.10 else None)

        # Repeated service fasteners make the removable panel strategy visible.
        for x in (2.0, 6.0, 10.0, 14.0, 18.0, 22.0):
            for z in (2.0, 9.0, 16.0):
                self.fastener("REMOVABLE_PANEL_FASTENER", x, 18.79, z)

    def report(self, export_status, screenshots):
        bb = self.root.boundingBox
        bbox = {
            "width_in": round((bb.maxPoint.x - bb.minPoint.x) / IN, 4),
            "depth_in": round((bb.maxPoint.y - bb.minPoint.y) / IN, 4),
            "height_in": round((bb.maxPoint.z - bb.minPoint.z) / IN, 4),
        }
        return {
            "schema_version": 1,
            "module_id": self.module_id,
            "title": self.title,
            "design_type": "direct-native-multi-component",
            "units": "inch",
            "nominal_envelope": {"width": W, "depth": D, "height": H},
            "measured_bbox": bbox,
            "component_count": self.root.allOccurrences.count,
            "body_count": len(self.parts),
            "required_visual_cues": self.required,
            "part_names": [p["name"] for p in self.parts],
            "parts": self.parts,
            "exports": export_status,
            "screenshots": screenshots,
            "local_model_revision_evidence": {
                "required_model": REVISION_LEDGER.get("required_model"),
                "allowed_models": REVISION_LEDGER.get("allowed_models", []),
                "model_counts": REVISION_LEDGER.get("model_counts", {}),
                "module_models": sorted({
                    item.get("model") for item in self.revision_records
                    if item.get("model")
                }),
                "ledger_path": REVISION_LEDGER_PATH,
                "ledger_result": REVISION_LEDGER.get("result", "MISSING"),
                "family_review_count": REVISION_LEDGER.get("module_review_count", 0),
                "module_review_count": len(self.revision_records),
                "adopted_requirement_count": sum(
                    item.get("gate_decision") == "ADOPT_AS_PROTOTYPE_REQUIREMENT"
                    for item in self.revision_records
                ),
                "record_ids": [item.get("record_id") for item in self.revision_records],
            },
            "represented_ots_catalog_ids": [
                "TNUTZ-EX1010-18", "TNUTZ-EX1010-22", "8020-4132",
                "8020-3393", "TNUTZ-HAN015AL", "TNUTZ-GAS010A",
                "TNUTZ-BUM010TS", "TAP-HYPACT-PANEL"
            ] + MODULE_OTS.get(self.module_id, []),
            "release_scope": "visual product-concept CAD; engineering release pending",
        }


def add_common(builder):
    builder.add_frame()
    builder.add_id_plate()
    builder.add_manufacturing_details()


def build_cook_station(b):
    add_common(b)
    b.box("UPPER_PREP_SURFACE", 2.0, 13.65, 14.75, 20.0, 3.95, 0.35,
          "aluminum_dark", "upper prep surface")
    b.slide_pair("STOVE", 2.4, 2.2, 9.65, 19.2, 12.8, "locking stove slides")
    b.box("PULL_OUT_STOVE_TRAY", 2.6, 0.55, 9.92, 18.8, 13.5, 0.35,
          "charcoal", "pull-out stove tray")
    b.box("STOVE_DECK", 4.0, 1.0, 10.30, 16.0, 11.2, 0.45, "aluminum_dark")
    for x in (8.0, 16.0):
        b.cyl("BURNER_OUTER", (x, 6.6, 10.78), (x, 6.6, 11.03), 2.05,
              "black", "two burners")
        b.cyl("BURNER_RING", (x, 6.6, 11.04), (x, 6.6, 11.18), 1.52,
              "aluminum")
        for ang in range(0, 360, 45):
            a = math.radians(ang)
            b.cyl("BURNER_GRATE", (x + math.cos(a) * 0.4, 6.6 + math.sin(a) * 0.4, 11.19),
                  (x + math.cos(a) * 1.9, 6.6 + math.sin(a) * 1.9, 11.19),
                  0.08, "black")
    for x in (8.0, 16.0):
        b.front_knob("STOVE_CONTROL_KNOB", x, 0.78, 10.65, 0.36,
                     "black", "control knobs")
        b.box("KNOB_INDEX", x - 0.04, 0.39, 10.82, 0.08, 0.05, 0.17, "white")
    # Raised three-sided sheet-metal wind guard.
    b.box("WIND_GUARD_BACK", 3.8, 11.9, 10.74, 16.4, 0.18, 3.3,
          "aluminum", "three-sided wind guard")
    b.box("WIND_GUARD_LEFT", 3.8, 2.1, 10.74, 0.18, 9.8, 3.3, "aluminum")
    b.box("WIND_GUARD_RIGHT", 20.02, 2.1, 10.74, 0.18, 9.8, 3.3, "aluminum")
    b.drawer("COOKWARE_DRAWER", 2.3, 2.2, 2.0, 19.4, 14.5, 6.7,
             "lower cookware drawer")


def build_dry_pantry(b):
    add_common(b)
    heights = [(2.0, 4.0), (6.35, 4.6)]
    for idx, (z, h) in enumerate(heights, 1):
        b.drawer("PANTRY_DRAWER_%d" % idx, 2.0, 1.75, z, 20.0, 15.9, h,
                 "three graduated drawers" if idx == 1 else None)
    # The upper tray is partially extended and open so the divider system is
    # readable from the website isometric view.
    b.slide_pair("PANTRY_DRAWER_3", 1.82, 2.0, 11.34, 20.36, 14.8)
    b.box("PANTRY_DRAWER_3_BOTTOM", 2.0, 0.90, 11.30, 20.0, 15.9, 0.25,
          "charcoal", "open upper pantry tray")
    b.box("PANTRY_DRAWER_3_SIDE_L", 2.0, 0.90, 11.55, 0.28, 15.9, 4.55,
          "charcoal")
    b.box("PANTRY_DRAWER_3_SIDE_R", 21.72, 0.90, 11.55, 0.28, 15.9, 4.55,
          "charcoal")
    b.box("PANTRY_DRAWER_3_BACK", 2.28, 16.52, 11.55, 19.44, 0.28, 4.55,
          "charcoal")
    b.box("PANTRY_DRAWER_3_FRONT", 2.10, 0.68, 11.40, 19.80, 0.28, 4.70,
          "aluminum_dark")
    b.handle("PANTRY_DRAWER_3_HANDLE", 10.0, 0.70, 13.9, 4.0, 0.50,
             "black", "upper drawer handle")
    b.front_knob("PANTRY_DRAWER_3_LATCH", 21.15, 0.70, 13.9, 0.20,
                 "black", "upper compression latch")
    b.box("PANTRY_DIVIDER_LONG", 11.92, 1.35, 11.55, 0.16, 14.5, 3.9,
          "aluminum", "internal dividers")
    for y in (5.0, 10.0):
        b.box("PANTRY_DIVIDER_CROSS", 2.30, y, 11.55, 19.4, 0.16, 3.9,
              "aluminum")
    # Full right side skin while retaining drawer-front readability.
    b.box("RIGHT_SIDE_PANEL", 21.85, 1.1, 1.1, 0.10, 17.75, 15.8,
          "charcoal", "full side and back panels")


def build_fridge(b):
    add_common(b)
    b.slide_pair("FRIDGE", 3.0, 2.1, 2.0, 18.0, 14.8, "low locking slide tray")
    b.box("FRIDGE_SLIDE_TRAY", 3.15, 0.72, 2.24, 17.7, 15.7, 0.42,
          "aluminum_dark")
    b.box("FRIDGE_BODY", 4.0, 1.05, 2.72, 16.0, 14.3, 10.7,
          "charcoal", "top-opening fridge body")
    b.box("FRIDGE_LID", 3.75, 0.85, 13.43, 16.5, 14.7, 1.15,
          "white", "lid and seam")
    b.box("LID_SEAM_FRONT", 3.85, 0.72, 13.35, 16.3, 0.12, 0.18, "black")
    b.handle("FRIDGE_CARRY_HANDLE", 10.0, 0.90, 11.3, 4.0, 0.75,
             "black", "front carry handle")
    b.vent_rows("COMPRESSOR", 15.8, 0.93, 4.2, 8, 2.4, False,
                "compressor vent array")
    for x in (6.1, 17.1):
        b.box("RESTRAINT_STRAP", x, 0.62, 3.3, 0.72, 0.20, 10.5,
              "orange", "two restraint straps" if x == 6.1 else None)
        b.box("STRAP_BUCKLE", x - 0.12, 0.38, 7.8, 0.96, 0.35, 1.15,
              "black")
    b.front_knob("FRIDGE_DRAIN_ACCESS", 5.15, 0.96, 3.8, 0.25,
                 "blue", "drain and service access")


def build_sink(b):
    add_common(b)
    # Four counter strips create a true visible opening instead of hiding the
    # basin below a solid slab.
    b.box("SINK_COUNTER_LEFT", 2.0, 2.0, 12.35, 3.2, 15.8, 0.45,
          "aluminum_dark", "counter and splash panel")
    b.box("SINK_COUNTER_RIGHT", 17.6, 2.0, 12.35, 4.4, 15.8, 0.45,
          "aluminum_dark")
    b.box("SINK_COUNTER_FRONT", 5.2, 2.0, 12.35, 12.4, 2.1, 0.45,
          "aluminum_dark")
    b.box("SINK_COUNTER_REAR", 5.2, 12.9, 12.35, 12.4, 4.9, 0.45,
          "aluminum_dark")
    # Open stainless tub: floor plus four walls around the recessed blue well.
    b.box("BASIN_FLOOR", 6.0, 4.9, 10.65, 10.8, 7.2, 0.22,
          "blue_dark", "recessed basin")
    b.box("BASIN_WALL_LEFT", 5.2, 4.1, 10.65, 0.8, 8.8, 1.70, "aluminum")
    b.box("BASIN_WALL_RIGHT", 16.8, 4.1, 10.65, 0.8, 8.8, 1.70, "aluminum")
    b.box("BASIN_WALL_FRONT", 6.0, 4.1, 10.65, 10.8, 0.8, 1.70, "aluminum")
    b.box("BASIN_WALL_REAR", 6.0, 12.1, 10.65, 10.8, 0.8, 1.70, "aluminum")
    b.cyl("BASIN_DRAIN", (12.0, 8.5, 10.84), (12.0, 8.5, 11.02),
          0.46, "black", "visible drain")
    # Foldable gooseneck silhouette: riser, arm, outlet.
    b.cyl("FAUCET_RISER", (18.8, 10.8, 12.78), (18.8, 10.8, 16.2),
          0.25, "aluminum", "raised foldable faucet")
    b.cyl("FAUCET_ARM", (18.8, 10.8, 16.2), (16.0, 9.2, 16.2),
          0.25, "aluminum")
    b.cyl("FAUCET_OUTLET", (16.0, 9.2, 16.2), (16.0, 9.2, 15.15),
          0.29, "aluminum")
    b.box("SPLASH_PANEL", 3.0, 16.55, 12.8, 18.0, 0.16, 3.65, "charcoal")
    b.box("GREY_WATER_TANK", 3.2, 6.2, 2.0, 11.3, 8.5, 6.9,
          "charcoal", "grey-water tank")
    b.front_knob("GREY_DRAIN_CAP", 5.0, 6.05, 4.6, 0.45, "black")
    b.box("PUMP_SERVICE_BAY", 15.0, 7.0, 3.2, 5.8, 6.6, 4.9,
          "aluminum_dark", "pump and service bay")
    b.cyl("WATER_PUMP", (17.9, 7.0, 5.7), (17.9, 9.8, 5.7),
          1.25, "blue")
    b.hose_path("SINK_HOSE", [(17.9, 9.8, 5.7), (20.3, 9.8, 5.7),
                              (20.3, 14.2, 5.7), (19.0, 14.2, 12.6)],
                0.18, "blue", "visible hose route")
    b.box("LOWER_SERVICE_DOOR", 14.9, 1.2, 2.0, 6.3, 0.25, 7.1,
          "charcoal", "lower service door")
    b.handle("SERVICE_DOOR_HANDLE", 16.1, 1.15, 5.7, 3.8, 0.45)


def build_fresh_water(b):
    add_common(b)
    b.box("WATER_TANK", 3.0, 4.0, 2.0, 14.0, 12.4, 12.3,
          "blue", "seven-gallon water tank")
    for z in (4.4, 7.6, 10.8):
        b.box("TANK_MOLDED_RIB", 3.18, 3.84, z, 13.64, 0.18, 0.30,
              "blue_dark", "molded tank ribs" if z == 4.4 else None)
    b.box("TANK_SHOULDER", 4.0, 3.8, 14.3, 12.0, 12.8, 1.5, "blue")
    b.cyl("FILL_NECK", (7.0, 9.8, 15.8), (7.0, 9.8, 16.6),
          1.1, "black", "fill cap")
    b.cyl("FILL_CAP", (7.0, 9.8, 16.6), (7.0, 9.8, 16.95), 1.35, "black")
    b.front_knob("SPIGOT", 9.0, 3.72, 4.2, 0.48, "white", "spigot")
    b.cyl("SPIGOT_NOZZLE", (9.0, 3.35, 4.2), (9.0, 2.3, 4.2), 0.18, "aluminum")
    for x in (5.0, 14.5):
        b.box("TANK_RESTRAINT_STRAP", x, 3.55, 2.6, 0.85, 0.24, 13.2,
              "orange", "two restraint straps" if x == 5.0 else None)
        b.box("TANK_STRAP_BUCKLE", x - 0.15, 3.20, 7.6, 1.15, 0.42, 1.35,
              "black")
    b.box("PUMP_SERVICE_BAY", 17.6, 5.0, 2.0, 4.2, 10.8, 7.5,
          "charcoal", "pump service bay")
    b.cyl("SERVICE_PUMP", (19.7, 5.0, 5.8), (19.7, 8.0, 5.8),
          1.1, "aluminum_dark")
    b.hose_path("DELIVERY_HOSE", [(19.7, 8.0, 5.8), (21.0, 8.0, 5.8),
                                  (21.0, 13.0, 5.8), (18.4, 13.0, 9.0)],
                0.17, "blue", "delivery hose")
    # Exposed service face and hose loop remain visible in the customer view.
    b.box("VENTED_ACCESS_PANEL", 18.0, 4.72, 6.7, 3.4, 0.22, 2.25,
          "aluminum_dark", "vented access panel")
    b.vent_rows("SERVICE_PANEL", 18.25, 4.60, 7.05, 5, 2.9, False,
                "service ventilation slots")
    b.cyl("EXTERNAL_PUMP_FACE", (19.7, 4.70, 4.9), (19.7, 3.65, 4.9),
          0.88, "aluminum", "visible pump face")
    b.hose_path("EXTERNAL_DELIVERY_HOSE",
                [(19.7, 3.55, 4.9), (21.0, 3.55, 4.9),
                 (21.0, 3.55, 9.6), (18.2, 3.55, 9.6)],
                0.20, "blue", "visible external delivery hose")
    b.cyl("HOSE_OUTLET", (18.2, 3.55, 9.6), (17.55, 3.55, 9.6),
          0.34, "blue")


def build_recovery(b):
    add_common(b)
    b.drawer("SEALED_TOOL_DRAWER", 2.2, 2.0, 2.0, 19.6, 15.0, 5.2,
             "sealed tool drawer")
    b.box("UPPER_ADJUSTABLE_SHELF", 2.2, 4.1, 8.0, 19.6, 12.5, 0.35,
          "aluminum_dark", "upper adjustable shelf")
    b.box("MOLLE_PANEL", 3.0, 17.0, 8.6, 18.0, 0.18, 7.8,
          "charcoal", "MOLLE organization panel")
    for row in range(4):
        for col in range(9):
            b.box("MOLLE_SLOT", 3.65 + col * 1.85, 16.77,
                  9.25 + row * 1.65, 0.95, 0.12, 0.32, "aluminum_dark")
    # Rope coil shown as three concentric side-by-side loops made of segments.
    center = (8.0, 10.6, 12.2)
    for ring in (1.45, 1.85, 2.25):
        pts = []
        for i in range(17):
            a = 2 * math.pi * i / 16
            pts.append((center[0] + ring * math.cos(a), center[1],
                        center[2] + ring * math.sin(a)))
        b.hose_path("RECOVERY_ROPE", pts, 0.19, "rope",
                    "coiled recovery rope" if ring == 1.45 else None)
    # D-shackle silhouettes and tool bars.
    for x in (14.0, 17.3):
        b.cyl("SHACKLE_PIN", (x - 0.75, 9.9, 10.2), (x + 0.75, 9.9, 10.2),
              0.22, "red", "shackles and tool silhouettes" if x == 14.0 else None)
        b.cyl("SHACKLE_SIDE", (x - 0.75, 9.9, 10.2), (x - 0.75, 9.9, 12.6), 0.22, "red")
        b.cyl("SHACKLE_SIDE", (x + 0.75, 9.9, 10.2), (x + 0.75, 9.9, 12.6), 0.22, "red")
        b.cyl("SHACKLE_TOP", (x - 0.75, 9.9, 12.6), (x + 0.75, 9.9, 12.6), 0.22, "red")
    b.cyl("PRY_BAR", (20.0, 9.7, 9.2), (20.0, 9.7, 15.8), 0.18, "orange")


def build_power(b):
    add_common(b)
    b.box("POWER_STATION_ENCLOSURE", 3.1, 4.2, 6.0, 17.8, 11.8, 9.3,
          "charcoal", "power-station enclosure")
    b.box("POWER_FRONT_BEZEL", 4.0, 3.85, 7.0, 16.0, 0.30, 7.3,
          "aluminum_dark")
    b.box("POWER_DISPLAY", 6.0, 3.45, 11.0, 6.0, 0.42, 2.4,
          "screen", "front display")
    b.box("DISPLAY_INSET", 6.55, 3.30, 11.45, 4.9, 0.17, 1.50, "black")
    for i, color in enumerate(("green", "blue", "white")):
        b.box("DISPLAY_BAR", 7.0, 3.16, 11.75 + i * 0.38,
              3.8 - i * 0.55, 0.10, 0.16, color)
    # AC, DC and USB cues, all proud of the front panel.
    for x in (14.0, 16.6):
        b.front_knob("AC_OUTLET", x, 3.78, 11.9, 0.72,
                     "black", "AC outlets" if x == 14.0 else None)
        b.box("AC_SLOT", x - 0.28, 3.37, 11.85, 0.12, 0.08, 0.40, "white")
        b.box("AC_SLOT", x + 0.16, 3.37, 11.85, 0.12, 0.08, 0.40, "white")
    for x in (14.0, 16.0, 18.0):
        b.front_knob("DC_PORT", x, 3.78, 9.35, 0.42,
                     "black", "round DC ports" if x == 14.0 else None)
    for x in (7.0, 8.6, 10.2):
        b.box("USB_PORT", x, 3.35, 8.6, 1.05, 0.20, 0.42,
              "blue_dark", "USB ports" if x == 7.0 else None)
    b.vent_rows("POWER_VENT", 4.5, 15.95, 7.0, 12, 5.0, False,
                "ventilation slots")
    b.drawer("CABLE_DRAWER", 3.0, 2.1, 2.0, 18.0, 13.5, 3.0, "cable drawer")
    b.cyl("PROTECTED_PASS_THROUGH", (20.1, 11.0, 5.0), (21.85, 11.0, 5.0),
          0.55, "black", "protected cable pass-through")


def build_hot_water(b):
    add_common(b)
    b.box("HEATER_BODY", 3.2, 7.2, 6.2, 11.5, 9.0, 9.5,
          "charcoal", "heater enclosure")
    b.box("HEATER_FACE", 4.0, 6.85, 7.0, 9.9, 0.32, 7.9,
          "aluminum_dark")
    b.box("HEATER_DISPLAY", 6.0, 6.45, 11.5, 5.7, 0.43, 1.7,
          "screen", "heater display")
    for x in (6.8, 10.8):
        b.front_knob("HEATER_KNOB", x, 6.72, 9.2, 0.55,
                     "black", "heater control knobs" if x == 6.8 else None)
    b.vent_rows("HEATER_VENT", 5.2, 6.78, 7.6, 7, 7.2, False,
                "heater vents")
    # A clear vertical hose coil on the open right side.
    cx, cy, cz = 18.0, 11.0, 11.0
    points = []
    turns = 3.25
    for i in range(53):
        a = 2 * math.pi * turns * i / 52
        points.append((cx + 2.1 * math.cos(a), cy,
                       cz + 2.1 * math.sin(a) + 0.075 * i))
    b.hose_path("SHOWER_HOSE", points, 0.14, "blue", "coiled shower hose")
    b.cyl("SHOWER_HEAD_HANDLE", (20.2, 3.0, 10.4), (20.2, 3.0, 14.6),
          0.28, "aluminum", "shower head")
    b.cyl("SHOWER_HEAD", (20.2, 3.0, 14.6), (20.2, 3.0, 15.45),
          0.70, "aluminum")
    for x, color in ((16.8, "red"), (19.2, "blue")):
        b.cyl("QUICK_CONNECT", (x, 3.20, 7.2), (x, 2.45, 7.2),
              0.38, color, "hot/cold quick connectors" if x == 16.8 else None)
    b.box("WET_STORAGE_TRAY", 3.0, 1.8, 2.0, 18.0, 14.3, 2.8,
          "blue_dark", "wet-storage tray")
    b.box("WET_TRAY_LIP", 3.0, 1.35, 2.0, 18.0, 0.45, 2.8, "black")


def build_office(b):
    add_common(b)
    b.box("RUGGED_CASE", 3.0, 1.80, 2.0, 10.0, 6.0, 5.3,
          "charcoal", "rugged camera case")
    b.box("CASE_LID", 2.8, 1.60, 7.3, 10.4, 6.4, 1.0,
          "black", "ribbed case lid")
    for x in (3.7, 5.4, 7.1, 8.8, 10.5, 12.2):
        b.box("CASE_LID_RIB", x, 1.38, 2.55, 0.38, 0.24, 4.20,
              "aluminum_dark")
    for x in (5.0, 10.6):
        b.box("CASE_LATCH", x, 1.18, 4.7, 1.25, 0.42, 1.55,
              "black", "case latches" if x == 5.0 else None)
    b.box("DEPLOYED_WORKTOP", 2.0, 0.8, 9.0, 20.0, 12.5, 0.42,
          "aluminum_dark", "deployable worktop")
    b.slide_pair("WORKTOP", 2.0, 5.0, 8.6, 20.0, 11.5)
    # Laptop base, hinge, open screen and keyboard/button cues.
    b.box("LAPTOP_BASE", 6.3, 2.1, 9.45, 12.0, 7.0, 0.35,
          "aluminum", "open laptop")
    b.cyl("LAPTOP_HINGE", (6.6, 8.9, 9.8), (18.0, 8.9, 9.8), 0.16, "black")
    b.box("LAPTOP_SCREEN_LID", 6.3, 8.82, 9.8, 12.0, 0.35, 6.5,
          "charcoal")
    b.box("LAPTOP_SCREEN", 7.0, 8.57, 10.45, 10.6, 0.22, 5.2,
          "screen")
    for row in range(4):
        for col in range(10):
            b.box("KEY", 7.2 + col * 0.95, 3.1 + row * 0.75, 9.82,
                  0.70, 0.48, 0.08, "black")
    b.box("TRACKPAD", 10.0, 6.35, 9.82, 4.5, 1.75, 0.08, "charcoal")
    b.drawer("ACCESSORY_DRAWER", 15.1, 1.80, 2.1, 6.2, 5.6, 3.8,
             "small accessory drawer")
    b.cyl("CABLE_PASS_THROUGH", (20.8, 1.55, 7.0), (20.8, 0.72, 7.0),
          0.48, "blue", "cable pass-through")


def build_furniture(b):
    add_common(b)
    # Two folded chair/table silhouettes, with feet and hinge lines.
    for idx, x in enumerate((4.0, 9.8), 1):
        b.box("FOLDED_FURNITURE_%d" % idx, x, 5.0, 2.0, 4.2, 10.8, 13.8,
              "tan", "folded chair and table forms" if idx == 1 else None)
        b.box("FURNITURE_EDGE", x + 0.35, 4.75, 2.45, 0.35, 0.25, 12.9, "black")
        b.box("FURNITURE_EDGE", x + 3.5, 4.75, 2.45, 0.35, 0.25, 12.9, "black")
        b.cyl("FURNITURE_HINGE", (x + 0.6, 4.65, 9.0),
              (x + 3.6, 4.65, 9.0), 0.20, "black")
    # Rolled soft goods as horizontal cylinders with contrasting end caps.
    for idx, (z, color) in enumerate(((4.0, "orange"), (8.0, "blue"),
                                      (12.0, "tan")), 1):
        b.cyl("ROLLED_SOFT_GOOD_%d" % idx, (15.0, 7.0, z), (20.8, 7.0, z),
              1.65, color, "rolled fabric cylinders" if idx == 1 else None)
        b.cyl("ROLL_END_CAP", (20.8, 7.0, z), (21.1, 7.0, z), 1.68, "black")
    for x in (7.0, 17.8):
        b.box("COMPRESSION_STRAP", x, 4.45, 2.2, 0.72, 0.25, 13.6,
              "orange", "two compression straps" if x == 7.0 else None)
        b.box("STRAP_BUCKLE", x - 0.15, 4.05, 8.0, 1.02, 0.45, 1.20,
              "aluminum_dark")
    # Front cargo-net pattern: two diagonal families form repeated diamonds.
    left = [(14.2, 3.65, z) for z in (2.7, 6.2, 9.7, 13.2)]
    right = [(21.5, 3.65, z) for z in (2.7, 6.2, 9.7, 13.2)]
    for i in range(3):
        b.cyl("CARGO_NET_UP", left[i], right[i + 1], 0.10, "black",
              "front cargo-net diamond pattern" if i == 0 else None)
        b.cyl("CARGO_NET_DOWN", right[i], left[i + 1], 0.10, "black")
    b.cyl("CARGO_NET_TOP", left[-1], right[-1], 0.10, "black")
    b.cyl("CARGO_NET_BOTTOM", left[0], right[0], 0.10, "black")
    for a in left + right:
        b.front_knob("NET_ANCHOR", a[0], a[1], a[2], 0.18, "black")


BUILDERS = {
    "build_cook_station": build_cook_station,
    "build_dry_pantry": build_dry_pantry,
    "build_fridge": build_fridge,
    "build_sink": build_sink,
    "build_fresh_water": build_fresh_water,
    "build_recovery": build_recovery,
    "build_power": build_power,
    "build_hot_water": build_hot_water,
    "build_office": build_office,
    "build_furniture": build_furniture,
}


def export_design(app, design, builder, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    base = os.path.join(output_dir, builder.module_id)
    export_mgr = design.exportManager
    status = {}

    jobs = [
        ("f3d", base + ".f3d",
         lambda p: export_mgr.createFusionArchiveExportOptions(p, builder.root)),
        ("step", base + ".step",
         lambda p: export_mgr.createSTEPExportOptions(p, builder.root)),
        ("stl", base + ".stl",
         lambda p: export_mgr.createSTLExportOptions(builder.root, p)),
        ("obj", base + ".obj",
         lambda p: export_mgr.createOBJExportOptions(builder.root, p)),
    ]
    for kind, filename, factory in jobs:
        if os.path.exists(filename):
            os.remove(filename)
        options = factory(filename)
        if kind in ("stl", "obj"):
            options.filename = filename
            options.isOneFilePerBody = False
            try:
                options.sendToPrintUtility = False
            except Exception:
                pass
        ok = bool(export_mgr.execute(options))
        status[kind] = {
            "path": filename,
            "api_ok": ok,
            "exists": os.path.exists(filename),
            "bytes": os.path.getsize(filename) if os.path.exists(filename) else 0,
        }
        if not ok or not status[kind]["exists"]:
            raise RuntimeError("%s export failed for %s" % (kind, builder.module_id))

    vp = app.activeViewport
    screenshots = {}
    # Explicit cameras avoid relying on the user's configurable ViewCube front.
    # The product opening is Y=0; both views therefore look from negative Y.
    views = (
        ("iso", (W * 1.75, -D * 1.75, H * 1.65)),
        ("front", (W / 2.0, -D * 3.5, H / 2.0)),
    )
    for label, eye in views:
        camera = vp.camera
        camera.eye = adsk.core.Point3D.create(eye[0] * IN, eye[1] * IN, eye[2] * IN)
        camera.target = adsk.core.Point3D.create(W * IN / 2.0, D * IN / 2.0,
                                                H * IN / 2.0)
        camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
        camera.isSmoothTransition = False
        camera.isFitView = True
        vp.camera = camera
        adsk.doEvents()
        vp.refresh()
        vp.fit()
        adsk.doEvents()
        filename = base + "-%s.png" % label
        if os.path.exists(filename):
            os.remove(filename)
        try:
            image_options = adsk.core.SaveImageFileOptions.create(filename)
            image_options.width = 1600
            image_options.height = 1200
            image_options.isAntiAliased = True
            image_options.isBackgroundTransparent = True
            ok = bool(vp.saveAsImageFileWithOptions(image_options))
        except Exception:
            ok = bool(vp.saveAsImageFile(filename, 1600, 1200))
        screenshots[label] = {
            "path": filename,
            "api_ok": ok,
            "exists": os.path.exists(filename),
            "bytes": os.path.getsize(filename) if os.path.exists(filename) else 0,
        }
        if not ok or not screenshots[label]["exists"]:
            raise RuntimeError("%s screenshot failed for %s" % (label, builder.module_id))
    return status, screenshots


def build_one(app, module_id, title, builder_name):
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design:
        raise RuntimeError("Fusion did not create a Design document")
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    builder = ModuleBuilder(app, design, module_id, title)
    BUILDERS[builder_name](builder)
    adsk.doEvents()
    out_dir = os.path.join(OUT_ROOT, module_id)
    exports, screenshots = export_design(app, design, builder, out_dir)
    report = builder.report(exports, screenshots)
    report_path = os.path.join(out_dir, module_id + "-build.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    print("BUILT %s components=%d bbox=%s" % (
        module_id, report["component_count"], report["measured_bbox"]))
    doc.close(False)
    return report


def run(_context: str):
    app = adsk.core.Application.get()
    os.makedirs(OUT_ROOT, exist_ok=True)
    family = []
    try:
        for module_id, title, builder_name in MODULES:
            family.append(build_one(app, module_id, title, builder_name))
        family_report = {
            "schema_version": 1,
            "result": "success",
            "module_count": len(family),
            "modules": family,
        }
        family_path = os.path.join(OUT_ROOT, "family-build-report.json")
        with open(family_path, "w", encoding="utf-8") as f:
            json.dump(family_report, f, indent=2)
            f.write("\n")
        print("FAMILY_BUILD_COMPLETE modules=%d report=%s" %
              (len(family), family_path))
    except Exception:
        print("FAMILY_BUILD_FAILED")
        print(traceback.format_exc())
        raise
