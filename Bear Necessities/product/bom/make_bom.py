#!/usr/bin/env python3
"""
make_bom.py — generate the Bill of Materials for the Modular Overland Camp System.

DESIGN DECISION: part numbers come from catalog.json (hand-verified), NOT from
the language model. The model builds geometry; this computes quantities. A
hallucinated part number is the one error that costs real money on a drop-ship
order, so the model is never allowed near that field.

    python3 make_bom.py                 # human-readable
    python3 make_bom.py --csv bom.csv   # for a supplier quote
"""
import argparse, csv, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
CATALOG = json.loads((HERE / "catalog.json").read_text())

# --- Frame geometry -----------------------------------------------------------
W, D, H = 24.0, 20.0, 18.0     # OUTSIDE dimensions, inches
P = 1.0                        # 10 Series profile, 1" square

# Post-and-rail: 4 posts run the full height; rails fit BETWEEN them.
POST_LEN = H                   # 18"
WIDTH_RAIL = W - 2 * P         # 22"
DEPTH_RAIL = D - 2 * P         # 18"

CORNERS = 8
BRACKETS_PER_CORNER = 3        # one per plane-pair; 2 is possible, see note
BOLTS_PER_BRACKET = 2          # 4132 has 2 thru holes

MODULES = ["Cook", "Storage", "Fridge", "Sink", "Water", "Gear/Utility"]


def cut_list():
    """Distinct cut lengths. Fewer distinct lengths = simpler, cheaper order."""
    lengths = {}
    for name, qty, length in (
        ("Vertical corner post", 4, POST_LEN),
        ("Depth rail", 4, DEPTH_RAIL),
        ("Width rail", 4, WIDTH_RAIL),
    ):
        lengths.setdefault(length, {"qty": 0, "roles": []})
        lengths[length]["qty"] += qty
        lengths[length]["roles"].append(f"{qty}x {name}")
    return dict(sorted(lengths.items()))


def build_rows(n_modules=1):
    prof = CATALOG["profile"]
    rows = []
    for length, info in cut_list().items():
        rows.append({
            "part_number": prof["part"],
            "alt_part_number": prof["alt_part"],
            "description": f'{prof["desc"]} - CUT TO {length:g}"',
            "vendor": prof["vendor"],
            "qty": info["qty"] * n_modules,
            "unit": "pc",
            "notes": "; ".join(info["roles"]),
            "unit_price_usd": "",
        })

    brackets = CORNERS * BRACKETS_PER_CORNER * n_modules
    b = next(f for f in CATALOG["fasteners"] if f["part"] == "4132")
    rows.append({
        "part_number": b["part"], "alt_part_number": "",
        "description": b["desc"], "vendor": b["vendor"],
        "qty": brackets, "unit": "pc",
        "notes": f"{BRACKETS_PER_CORNER} per corner x {CORNERS} corners. {b['note']}",
        "unit_price_usd": "",
    })

    f3395 = next(f for f in CATALOG["fasteners"] if f["part"] == "3395")
    rows.append({
        "part_number": f3395["part"], "alt_part_number": "",
        "description": f3395["desc"], "vendor": f3395["vendor"],
        "qty": brackets * BOLTS_PER_BRACKET, "unit": "pc",
        "notes": f"{BOLTS_PER_BRACKET} per bracket",
        "unit_price_usd": "",
    })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modules", type=int, default=1)
    ap.add_argument("--csv")
    a = ap.parse_args()

    rows = build_rows(a.modules)
    total_in = sum(
        r["qty"] * float(r["description"].rsplit("CUT TO ", 1)[1].rstrip('"'))
        for r in rows if "CUT TO" in r["description"])

    print(f"BILL OF MATERIALS - Modular Overland Camp System base frame")
    print(f"Module size: {W:g}\" W x {D:g}\" D x {H:g}\" H outside | {CATALOG['series'].split(' - ')[0]}")
    print(f"Quantity: {a.modules} module frame(s)\n")

    w = (10, 10, 44, 11, 5)
    hdr = ("PART", "CUT", "DESCRIPTION", "VENDOR", "QTY")
    print(f"{hdr[0]:<{w[0]}} {hdr[1]:<{w[1]}} {hdr[2]:<{w[2]}} {hdr[3]:<{w[3]}} {hdr[4]:>{w[4]}}")
    print("-" * (sum(w) + 4))
    for r in rows:
        if "CUT TO " in r["description"]:
            base, cut = r["description"].rsplit(" - CUT TO ", 1)
        else:
            base, cut = r["description"], "-"
        print(f"{r['part_number']:<{w[0]}} {cut:<{w[1]}} {base[:w[2]]:<{w[2]}} "
              f"{r['vendor']:<{w[3]}} {r['qty']:>{w[4]}}")

    print(f"\nTotal extrusion: {total_in:g} in = {total_in/12:.2f} ft "
          f"({total_in/12/a.modules:.2f} ft per module)")
    summary = ", ".join('{:g}" x{}'.format(l, i["qty"] * a.modules)
                        for l, i in cut_list().items())
    print(f"Distinct cut lengths: {len(cut_list())} -> {summary}")
    print("\nWHY THIS MATTERS FOR DROP-SHIP:")
    print("  Only TWO distinct cut lengths per module. Posts and depth rails are")
    print("  both 18\", so one saw setup covers 8 of the 12 pieces. That is the")
    print("  cheapest possible order to place with a cut-to-length supplier.")
    print("\nPRICING: intentionally blank - get a live quote. Do not estimate from memory.")

    if a.csv:
        out = pathlib.Path(a.csv)
        with out.open("w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            wr.writeheader(); wr.writerows(rows)
        print(f"\nCSV written: {out}")


if __name__ == "__main__":
    main()
