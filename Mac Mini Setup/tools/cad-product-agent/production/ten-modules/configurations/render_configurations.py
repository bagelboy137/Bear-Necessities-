#!/usr/bin/env python3
"""Render exact solver placements as customer-readable vehicle layout boards.

The board is intentionally a diagram, not a fake vehicle photograph: plan and
side elevations stay dimensionally tied to config_solver.py, while the canonical
alpha product renders show which physical modules occupy each labelled box.
"""

import hashlib
import json
import pathlib
import re
import sys

from PIL import Image, ImageDraw, ImageFont

import config_solver as solver

HERE = pathlib.Path(__file__).resolve().parent
VISUAL = HERE.parent / "visual"
OUT = HERE / "renders"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size, bold=False):
    names = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def module_color(module_id):
    index = int(module_id[-2:]) - 1
    palette = [(207, 91, 50), (82, 116, 90), (184, 148, 66), (73, 111, 128),
               (132, 92, 112), (104, 110, 70), (168, 103, 45), (69, 120, 113),
               (121, 91, 63), (92, 104, 122)]
    return palette[index]


def draw_box(draw, box, fill, label, scale, origin, axes=(0, 1)):
    x0 = origin[0] + box[axes[0]] * scale
    y0 = origin[1] + box[axes[1]] * scale
    x1 = origin[0] + box[axes[0] + 3] * scale
    y1 = origin[1] + box[axes[1] + 3] * scale
    draw.rounded_rectangle((x0, y0, x1, y1), radius=14, fill=fill,
                           outline=(246, 241, 228), width=4)
    draw.text((x0 + 12, y0 + 10), label, font=font(25 if len(label) < 11 else 18, True),
              fill=(250, 247, 239))


def group_labels(items):
    """Give hidden boxes their names back.

    Two modules that stack, or that sit side by side across the vehicle, project
    to the same rectangle in one of the two views - only the last one drawn stays
    visible. The placement is still honest, but a reader sees one box and counts
    one module. So the visible box carries every name sharing its rectangle.

    items: list of (rect_key, label). Returns one label per index, "" to skip.
    """
    groups = {}
    for index, (key, label) in enumerate(items):
        groups.setdefault(key, []).append((index, label))
    out = [""] * len(items)
    for group in groups.values():
        out[group[-1][0]] = " + ".join(label for _, label in group)
    return out


def render_board(config, vehicle, solution, pitch, output):
    width, height = 2400, 1600
    image = Image.new("RGB", (width, height), (29, 33, 29))
    draw = ImageDraw.Draw(image)
    paper, muted, orange = (238, 233, 220), (166, 171, 159), (211, 91, 49)

    draw.text((110, 80), config, font=font(72, True), fill=paper)
    draw.text((112, 170), pitch, font=font(30), fill=muted)
    draw.text((112, 222), "SOLVER-VALIDATED · %s" % vehicle.name.upper(),
              font=font(22, True), fill=orange)

    # Plan view: x across vehicle, y forward from tailgate.
    plan_origin = (110, 360)
    plan_w, plan_h = 1030, 780
    scale = min(plan_w / vehicle.width, plan_h / vehicle.depth)
    bay = (plan_origin[0], plan_origin[1],
           plan_origin[0] + vehicle.width * scale,
           plan_origin[1] + vehicle.depth * scale)
    draw.rounded_rectangle(bay, radius=28, fill=(49, 57, 49),
                           outline=(136, 151, 128), width=6)
    draw.text((plan_origin[0], plan_origin[1] - 48), "PLAN · TAILGATE AT BOTTOM",
              font=font(24, True), fill=paper)
    plan_labels = group_labels([
        ((p.box[0], p.box[1], p.box[3], p.box[4]),
         p.module["id"] + (" ↻" if p.rotated else ""))
        for p in solution])
    for placement, label in zip(solution, plan_labels):
        draw_box(draw, placement.box, module_color(placement.module["id"]),
                 label, scale, plan_origin, (0, 1))

    # Side elevation: y into vehicle, z up.
    side_origin = (1280, 360)
    side_w, side_h = 1000, 540
    side_scale = min(side_w / vehicle.depth, side_h / vehicle.height)
    side_bay = (side_origin[0], side_origin[1],
                side_origin[0] + vehicle.depth * side_scale,
                side_origin[1] + vehicle.height * side_scale)
    draw.rounded_rectangle(side_bay, radius=28, fill=(49, 57, 49),
                           outline=(136, 151, 128), width=6)
    draw.text((side_origin[0], side_origin[1] - 48), "SIDE · HEADROOM / STACKING",
              font=font(24, True), fill=paper)
    side_labels = group_labels([
        ((p.y, p.z, p.d, p.h), p.module["id"]) for p in solution])
    for placement, label in zip(solution, side_labels):
        # Side elevation y/z: invert z so floor is at the bottom of the bay.
        y0 = side_origin[0] + placement.y * side_scale
        y1 = side_origin[0] + (placement.y + placement.d) * side_scale
        z1 = side_origin[1] + vehicle.height * side_scale - placement.z * side_scale
        z0 = z1 - placement.h * side_scale
        draw.rounded_rectangle((y0, z0, y1, z1), radius=12,
                               fill=module_color(placement.module["id"]),
                               outline=paper, width=4)
        draw.text((y0 + 10, z0 + 8), label,
                  font=font(21 if len(label) < 11 else 16, True),
                  fill=(250, 247, 239))

    # Product strip uses the final transparent renders, not anonymous boxes.
    card_y, card_h = 1010, 470
    card_gap = 20
    card_w = min(390, (2180 - card_gap * (len(solution) - 1)) // len(solution))
    x = 110
    for placement in solution:
        module_id = placement.module["id"]
        path = VISUAL / "renders" / (module_id + "-alpha.png")
        card = Image.new("RGBA", (card_w, card_h), (238, 233, 220, 255))
        product = Image.open(path).convert("RGBA")
        product.thumbnail((card_w - 24, card_h - 96), Image.Resampling.LANCZOS)
        card.alpha_composite(product, ((card_w - product.width) // 2, 8))
        card_draw = ImageDraw.Draw(card)
        card_draw.text((18, card_h - 74), module_id, font=font(27, True),
                       fill=(211, 91, 49))
        card_draw.text((18, card_h - 42), placement.module["name"],
                       font=font(22), fill=(29, 33, 29))
        image.paste(card.convert("RGB"), (x, card_y))
        x += card_w + card_gap

    draw.text((1280, 930), "%g × %g × %g IN BAY" %
              (vehicle.width, vehicle.depth, vehicle.height),
              font=font(25, True), fill=paper)
    draw.text((1280, 966), "Module origins measured from tailgate / driver side",
              font=font(21), fill=muted)
    image.save(output, optimize=True)


def main():
    deployment = solver.load(solver.DEPLOYMENT)
    modules = {item["id"]: item for item in deployment["modules"]}
    vehicles = {item["id"]: solver.Vehicle(item)
                for item in solver.load(solver.VEHICLES)["vehicles"]}
    configs = solver.load(solver.CONFIGS)["configurations"]
    validation = {item["configuration"]: item
                  for item in solver.load(HERE / "configuration-validation.json")
                  ["configurations"]}

    sources = [VISUAL / "renders" / (module_id + "-alpha.png")
               for module_id in modules]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        print("CONFIG_RENDER_FAIL missing %d alpha render(s)" % len(missing),
              file=sys.stderr)
        return 1

    OUT.mkdir(exist_ok=True)
    records = []
    for config in configs:
        fit_ids = validation[config["name"]]["fits_vehicles"]
        if not fit_ids:
            print("CONFIG_RENDER_FAIL %s has no fitting vehicle" % config["name"],
                  file=sys.stderr)
            return 1
        vehicle = vehicles[fit_ids[0]]
        chosen = [modules[module_id] for module_id in config["modules"]]
        solutions, rejected = solver.solve(vehicle, chosen, limit=1)
        if not solutions:
            print("CONFIG_RENDER_FAIL %s no longer solves" % config["name"],
                  file=sys.stderr)
            return 1
        output = OUT / (slug(config["name"]) + ".png")
        render_board(config["name"], vehicle, solutions[0], config["pitch"], output)
        records.append({"configuration": config["name"], "vehicle": vehicle.id,
                        "modules": config["modules"],
                        "placements": [p.as_dict() for p in solutions[0]],
                        "image": str(output), "sha256": digest(output)})
        print("  rendered %s" % output.name)
    report = {"result": "PASS", "renders": records}
    (OUT / "configuration-render-report.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print("CONFIG_RENDER_PASS configurations=%d" % len(records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
