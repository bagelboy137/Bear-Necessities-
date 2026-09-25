#!/usr/bin/env python3
"""Build the one-pass marketing review sheet from canonical hero/front renders."""

import argparse
import hashlib
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
RENDERS = HERE / "renders"
MODULE_IDS = ["BN-M%02d" % index for index in range(1, 11)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit(image, size):
    copy = image.convert("RGB")
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, (235, 232, 225))
    x = (size[0] - copy.width) // 2
    y = (size[1] - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path,
                        default=HERE / "marketing-contact-sheet.png")
    args = parser.parse_args()

    paths = [(module_id, view,
              RENDERS / ("%s-%s.png" % (module_id, view)))
             for view in ("hero", "front") for module_id in MODULE_IDS]
    missing = [str(path) for _, _, path in paths if not path.is_file()]
    if missing:
        print("CONTACT_SHEET_FAIL missing %d image(s):\n%s" %
              (len(missing), "\n".join(missing)), file=sys.stderr)
        return 1

    cell_w, cell_h, label_h = 500, 360, 38
    cols, rows = 5, 4
    sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)),
                      (28, 31, 28))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=18)
    manifest = []
    for index, (module_id, view, path) in enumerate(paths):
        row, col = divmod(index, cols)
        x, y = col * cell_w, row * (cell_h + label_h)
        tile = fit(Image.open(path), (cell_w, cell_h))
        sheet.paste(tile, (x, y))
        draw.text((x + 14, y + cell_h + 8), "%s · %s" %
                  (module_id, view.upper()), fill=(239, 235, 224), font=font)
        manifest.append({"module_id": module_id, "view": view,
                         "path": str(path), "sha256": digest(path)})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, optimize=True)
    manifest_path = args.output.with_suffix(".json")
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "contact_sheet": str(args.output),
        "contact_sheet_sha256": digest(args.output),
        "images": manifest,
    }, indent=2) + "\n")
    print("CONTACT_SHEET_PASS images=20 output=%s" % args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
