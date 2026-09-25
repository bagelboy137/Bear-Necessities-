#!/usr/bin/env python3
"""Which Bear Necessities modules actually fit in a given vehicle, and how.

Deterministic packing. No model involved - this is arithmetic, and the arithmetic
is unforgiving:

    one module          24 W x 20 D x 18 H inches
    two side by side    48 inches wide
    two stacked         36 inches tall

Most SUV cargo bays are narrower than 48 inches between the wheel wells and
shorter than 36 inches to the ceiling, so the honest answer for most vehicles is
2-4 modules chosen per trip, not a full stack of ten. This tool says which.

    python3 config_solver.py --vehicle 4runner-5th --set M01,M03,M05 --explain
    python3 config_solver.py --vehicle 4runner-5th --best 4
    python3 config_solver.py --validate-all
    python3 config_solver.py --demo

Coordinates are inches, origin at the tailgate edge of the cargo floor on the
driver side: +x toward the passenger side, +y forward into the vehicle, +z up.
So y=0 is the tailgate and a front-opening module wants clear space toward y=0.
"""

import argparse
import itertools
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEPLOYMENT = HERE / "module-deployment.json"
VEHICLES = HERE / "VEHICLE-ENVELOPES.json"
CONFIGS = HERE / "named-configurations.json"

# ponytail: brute-force placement on a 2-inch lattice, <= 6 modules. Exhaustive
# and obviously correct at this scale. Swap for a real bin-packer only if the
# module count or the lattice resolution grows.
LATTICE_IN = 2.0


def load(path):
    if not path.is_file():
        raise SystemExit("missing data file: %s" % path)
    return json.loads(path.read_text())


class Vehicle:
    def __init__(self, data):
        self.id = data["id"]
        self.name = data["name"]
        self.width = float(data["cargo_width_in"])
        self.depth = float(data["cargo_depth_in"])
        self.height = float(data["cargo_height_in"])
        self.well_width = float(data.get("width_between_wells_in", self.width))
        self.well_height = float(data.get("wheel_well_height_in", 0.0))
        self.tailgate_width = float(data.get("tailgate_opening_width_in", self.width))
        self.tailgate_height = float(data.get("tailgate_opening_height_in", self.height))
        self.payload_lb = data.get("payload_lb")
        self.status = data.get("status", "UNVERIFIED")
        self.source = data.get("source")

    def usable_width_at(self, z0, z1):
        """Wheel wells pinch the bay below their height; above them it opens up."""
        return self.well_width if z0 < self.well_height else self.width


class Placement:
    __slots__ = ("module", "x", "y", "z", "w", "d", "h", "rotated")

    def __init__(self, module, x, y, z, rotated):
        self.module = module
        self.x, self.y, self.z = x, y, z
        self.rotated = rotated
        # Yaw 90 degrees swaps the footprint; height never changes.
        self.w, self.d = (20.0, 24.0) if rotated else (24.0, 20.0)
        self.h = 18.0

    @property
    def box(self):
        return (self.x, self.y, self.z,
                self.x + self.w, self.y + self.d, self.z + self.h)

    def overlaps(self, other):
        ax0, ay0, az0, ax1, ay1, az1 = self.box
        bx0, by0, bz0, bx1, by1, bz1 = other.box
        return (ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1
                and az0 < bz1 and bz0 < az1)

    def as_dict(self):
        return {"module": self.module["id"], "name": self.module["name"],
                "origin_in": [self.x, self.y, self.z],
                "footprint_in": [self.w, self.d], "rotated": self.rotated}


def fits_envelope(placement, vehicle):
    x0, y0, z0, x1, y1, z1 = placement.box
    if x0 < 0 or y0 < 0 or z0 < 0:
        return "starts outside the bay"
    if z1 > vehicle.height:
        return ("stack height %.0f in exceeds cargo height %.0f in"
                % (z1, vehicle.height))
    if y1 > vehicle.depth:
        return "depth %.0f in exceeds cargo depth %.0f in" % (y1, vehicle.depth)
    usable = vehicle.usable_width_at(z0, z1)
    if x1 > usable:
        return ("width %.0f in exceeds usable width %.0f in%s"
                % (x1, usable,
                   " between the wheel wells" if usable == vehicle.well_width
                   and usable != vehicle.width else ""))
    return None


def check_access(placement, others, vehicle):
    """A module you cannot open is a module you did not pack."""
    problems = []
    clearances = placement.module.get("access_clearance_in", {})
    x0, y0, z0, x1, y1, z1 = placement.box
    for direction in placement.module.get("access", []):
        need = float(clearances.get(direction, 12.0))
        if direction == "top":
            for other in others:
                ox0, oy0, oz0, ox1, oy1, oz1 = other.box
                if (ox0 < x1 and x0 < ox1 and oy0 < y1 and y0 < oy1
                        and oz0 >= z1 - 0.01):
                    problems.append(
                        "%s opens upward but %s is stacked on it"
                        % (placement.module["id"], other.module["id"]))
                    break
            else:
                if vehicle.height - z1 < need:
                    problems.append(
                        "%s opens upward and needs %.0f in headroom, has %.0f in"
                        % (placement.module["id"], need, vehicle.height - z1))
        elif direction == "front":
            # Anything between this module and the tailgate at the same height
            # and width band blocks a drawer or a pull-out tray.
            blocked = None
            for other in others:
                ox0, oy0, oz0, ox1, oy1, oz1 = other.box
                if (ox0 < x1 and x0 < ox1 and oz0 < z1 and z0 < oz1
                        and oy1 <= y0 + 0.01):
                    blocked = other
                    break
            if blocked is not None:
                problems.append(
                    "%s opens toward the tailgate but %s sits in front of it"
                    % (placement.module["id"], blocked.module["id"]))
            elif y0 < need:
                # Reaching in from the tailgate: the drawer travel has to happen
                # somewhere, and outside the vehicle counts.
                pass
    return problems


def solve(vehicle, modules, limit=200):
    """Every non-overlapping, in-envelope, openable arrangement, best first.

    Candidate positions are corner points - the origin plus the trailing edges of
    already-placed modules - rather than a lattice. In axis-aligned packing any
    arrangement can be pushed back against the walls and its neighbours without
    changing which modules fit, so corner points lose nothing and turn a search
    that does not terminate into one that finishes instantly.
    """
    n = len(modules)
    if n == 0:
        return [], ["no modules requested"]
    if n > 6:
        return [], ["refusing to brute-force more than 6 modules (asked for %d)" % n]
    if vehicle.width <= 0 or vehicle.depth <= 0 or vehicle.height <= 0:
        return [], ["%s envelope is unverified; no dimensions to solve against"
                    % vehicle.id]

    solutions, rejected = [], {}
    nodes = [0]

    def note(reason):
        rejected[reason] = rejected.get(reason, 0) + 1

    def corner_values(chosen, axis):
        values = {0.0}
        for placement in chosen:
            if axis == "x":
                values.add(placement.x + placement.w)
                values.add(placement.x)
            elif axis == "y":
                values.add(placement.y + placement.d)
                values.add(placement.y)
            else:
                values.add(placement.z + placement.h)
        return sorted(values)

    def place(index, chosen):
        nodes[0] += 1
        if len(solutions) >= limit or nodes[0] > 200000:
            return
        if index == n:
            problems = []
            for i, placement in enumerate(chosen):
                others = [c for j, c in enumerate(chosen) if j != i]
                problems.extend(check_access(placement, others, vehicle))
            if problems:
                for problem in problems:
                    note(problem)
                return
            solutions.append(list(chosen))
            return
        module = modules[index]
        for rotated in (False, True):
            for z in corner_values(chosen, "z"):
                for y in corner_values(chosen, "y"):
                    for x in corner_values(chosen, "x"):
                        candidate = Placement(module, x, y, z, rotated)
                        reason = fits_envelope(candidate, vehicle)
                        if reason:
                            note(reason)
                            continue
                        if any(candidate.overlaps(other) for other in chosen):
                            continue
                        if z > 0 and not any(
                                abs(other.z + other.h - z) < 0.01
                                and other.x < candidate.x + candidate.w
                                and candidate.x < other.x + other.w
                                and other.y < candidate.y + candidate.d
                                and candidate.y < other.y + other.d
                                for other in chosen):
                            note("a stacked module needs one directly beneath it")
                            continue
                        chosen.append(candidate)
                        place(index + 1, chosen)
                        chosen.pop()

    place(0, [])
    # Prefer arrangements that stay low and shallow: easier to load, lower centre
    # of gravity, more of the tailgate left usable.
    solutions.sort(key=lambda s: (max(p.z + p.h for p in s),
                                  max(p.y + p.d for p in s)))
    return solutions, rejected


def describe(solution):
    return " | ".join(
        "%s @ (%.0f,%.0f,%.0f)%s" % (p.module["id"], p.x, p.y, p.z,
                                     " rot" if p.rotated else "")
        for p in solution)


def payload_note(vehicle, modules):
    unknown = [m["id"] for m in modules if m.get("mass_status") != "VERIFIED"]
    if unknown:
        return ("payload NOT checked: mass unverified for %s. Populate mass_lb in "
                "module-deployment.json before quoting a load." % ", ".join(unknown))
    total = sum(float(m["mass_lb"]) for m in modules)
    if vehicle.payload_lb and total > float(vehicle.payload_lb):
        return "OVER PAYLOAD: %.0f lb of modules against %.0f lb rated" % (
            total, float(vehicle.payload_lb))
    return "modules total %.0f lb" % total


def demo():
    """Self-check: the arithmetic that drives every real answer must hold."""
    modules = {m["id"]: m for m in load(DEPLOYMENT)["modules"]}

    narrow = Vehicle({"id": "t", "name": "test bay", "cargo_width_in": 45.0,
                      "cargo_depth_in": 40.0, "cargo_height_in": 34.0,
                      "width_between_wells_in": 41.0, "wheel_well_height_in": 12.0})

    # Two modules side by side is 48 in. A 45 in bay cannot take them side by
    # side, but 24+20 rotated is 44 in and must still be found.
    solutions, rejected = solve(narrow, [modules["BN-M02"], modules["BN-M06"]])
    assert solutions, "two front-access modules should fit a 45 in bay somehow"
    for solution in solutions:
        widths = {(round(p.x, 1), round(p.y, 1)) for p in solution}
        assert len(widths) == 2
    assert any("usable width" in reason for reason in rejected), \
        "the solver must reject over-wide placements out loud"

    # Nothing may ever be stacked on the top-opening fridge.
    fridge, pantry = modules["BN-M03"], modules["BN-M02"]
    stacked = [Placement(fridge, 0, 0, 0, False), Placement(pantry, 0, 0, 18, False)]
    problems = check_access(stacked[0], [stacked[1]], narrow)
    assert any("stacked on it" in p for p in problems), problems

    # A front-opening module blocked by another between it and the tailgate.
    behind = Placement(modules["BN-M06"], 0, 20, 0, False)
    infront = Placement(modules["BN-M02"], 0, 0, 0, False)
    problems = check_access(behind, [infront], narrow)
    assert any("sits in front of it" in p for p in problems), problems

    # Two-high is 36 in and must be rejected by a 34 in ceiling.
    tall = Placement(modules["BN-M02"], 0, 0, 18, False)
    assert "exceeds cargo height" in (fits_envelope(tall, narrow) or ""), \
        "36 in of stack must not fit a 34 in bay"

    # Payload must refuse to answer while masses are unverified.
    note = payload_note(narrow, [modules["BN-M01"]])
    assert "NOT checked" in note, note

    print("demo ok: over-wide rejected, fridge un-stackable, front access "
          "blocked, 36 in stack rejected by a 34 in ceiling, payload withheld")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vehicle")
    parser.add_argument("--set", dest="module_set",
                        help="comma-separated, e.g. M01,M03,M05")
    parser.add_argument("--best", type=int, metavar="N",
                        help="largest set of N modules that fits")
    parser.add_argument("--explain", action="store_true")
    parser.add_argument("--validate-all", action="store_true")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()

    if args.demo:
        demo()
        return 0

    deployment = load(DEPLOYMENT)
    modules = {m["id"]: m for m in deployment["modules"]}
    vehicles = {v["id"]: Vehicle(v) for v in load(VEHICLES)["vehicles"]}

    if args.validate_all:
        return validate_all(modules, vehicles, args.output)

    if not args.vehicle or args.vehicle not in vehicles:
        raise SystemExit("--vehicle must be one of: %s" % ", ".join(sorted(vehicles)))
    vehicle = vehicles[args.vehicle]
    if vehicle.status != "VERIFIED":
        print("WARNING: %s envelope is %s - %s\n"
              % (vehicle.id, vehicle.status, vehicle.source or "no source"))

    if args.best:
        best = None
        for combo in itertools.combinations(sorted(modules), args.best):
            chosen = [modules[m] for m in combo]
            solutions, _ = solve(vehicle, chosen, limit=1)
            if solutions:
                best = (combo, solutions[0])
                break
        if not best:
            print("no %d-module set fits %s" % (args.best, vehicle.name))
            return 1
        print("%s: %s" % (vehicle.name, describe(best[1])))
        return 0

    ids = ["BN-" + part.strip().upper().removeprefix("BN-")
           for part in (args.module_set or "").split(",") if part.strip()]
    missing = [i for i in ids if i not in modules]
    if missing:
        raise SystemExit("unknown module(s): %s" % ", ".join(missing))
    chosen = [modules[i] for i in ids]

    solutions, rejected = solve(vehicle, chosen)
    print("%s (%s)  bay %.0f W x %.0f D x %.0f H, %.0f W between wells"
          % (vehicle.name, vehicle.status, vehicle.width, vehicle.depth,
             vehicle.height, vehicle.well_width))
    print("modules: %s" % ", ".join(ids))
    print(payload_note(vehicle, chosen))
    if solutions:
        print("\n%d valid arrangement(s). Best:" % len(solutions))
        print("  " + describe(solutions[0]))
    else:
        print("\nNO valid arrangement.")
    if args.explain or not solutions:
        print("\nwhy placements were rejected (count, reason):")
        for reason, count in sorted(rejected.items(), key=lambda kv: -kv[1])[:12]:
            print("  %6d  %s" % (count, reason))
    if args.output:
        args.output.write_text(json.dumps({
            "vehicle": vehicle.id, "modules": ids,
            "solutions": [[p.as_dict() for p in s] for s in solutions[:20]],
            "rejected": rejected,
        }, indent=2) + "\n")
    return 0 if solutions else 1


def validate_all(modules, vehicles, output):
    named = load(CONFIGS)["configurations"] if CONFIGS.is_file() else []
    if not named:
        print("no named-configurations.json yet - nothing to validate")
        return 0
    rows, failures = [], 0
    for config in named:
        chosen = [modules[m] for m in config["modules"]]
        fits = []
        for vehicle in vehicles.values():
            solutions, _ = solve(vehicle, chosen, limit=1)
            if solutions:
                fits.append(vehicle.id)
        row = {"configuration": config["name"], "modules": config["modules"],
               "fits_vehicles": fits}
        if not fits:
            failures += 1
            row["result"] = "FAIL - fits no known vehicle"
        else:
            row["result"] = "PASS"
        rows.append(row)
        print("%-18s %-28s %s" % (config["name"], ",".join(config["modules"]),
                                  row["result"] + (" (" + ", ".join(fits) + ")"
                                                   if fits else "")))
    document = {"configurations": rows, "failures": failures,
                "result": "PASS" if not failures else "FAIL"}
    if output:
        output.write_text(json.dumps(document, indent=2) + "\n")
    print("\n%s: %d configuration(s), %d with no fitting vehicle"
          % (document["result"], len(rows), failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
