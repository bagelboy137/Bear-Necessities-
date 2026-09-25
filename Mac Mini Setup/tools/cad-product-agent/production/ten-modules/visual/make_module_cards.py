#!/usr/bin/env python3
"""Build website-grade module imagery from the native Fusion CAD exports.

Source of truth is fusion-native/exports/<id>/<id>-iso.png - the accurate,
dimensionally honest CAD view. This script does presentation only: it keys the
white studio background to alpha, trims to content, and composes brand cards in
the website palette. It invents no geometry. Anything you see in an output here
exists in the F3D.

Outputs, all under visual/renders/:
  <id>-alpha.png   trimmed transparent cutout (also feeds render_configurations.py)
  <id>-card.png    1600x1200 brand card, module + name + dimensions
  <id>-square.png  1200x1200 square crop for site grids and social

Run:  ../../../../../Fusion\\ CAD\\ Agent/.venv-cq/bin/python3 make_module_cards.py
"""

import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
STUDY = HERE.parent
EXPORTS = STUDY / "fusion-native" / "exports"
OUT = HERE / "renders"

# Website palette (website/app) - keep these in sync with the site, not invented here.
CREAM = (245, 241, 231)
CREAM_EDGE = (232, 224, 207)
FOREST = (31, 58, 41)
INK = (23, 32, 25)
ACCENT = (213, 104, 56)
SAGE = (130, 148, 107)

MODULE_W_IN, MODULE_D_IN, MODULE_H_IN = 24, 20, 18

FONT_DIRS = [
    "/System/Library/Fonts/Supplemental/",
    "/System/Library/Fonts/",
]


def font(size, bold=False):
    names = ["Arial Bold.ttf", "Helvetica.ttc"] if bold else ["Arial.ttf", "Helvetica.ttc"]
    for d in FONT_DIRS:
        for n in names:
            p = pathlib.Path(d) / n
            if p.exists():
                try:
                    return ImageFont.truetype(str(p), size)
                except OSError:
                    continue
    return ImageFont.load_default()


def key_background(src, thresh=28):
    """White studio background -> alpha, by flood fill from the borders.

    Flood fill rather than a global white threshold: the extrusion highlights and
    the stove top are near-white too, and a global threshold punches holes in the
    product. Only background connected to an edge is removed.
    """
    rgb = src.convert("RGB")
    magic = (255, 0, 255)
    w, h = rgb.size
    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1)]
    for seed in seeds:
        if rgb.getpixel(seed) == magic:
            continue
        ImageDraw.floodfill(rgb, seed, magic, thresh=thresh)

    alpha = Image.new("L", (w, h), 255)
    alpha.putdata([0 if px == magic else 255 for px in rgb.getdata()])
    # Soften the 1px stair-stepping the fill leaves on diagonal extrusion edges.
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.6))
    alpha = alpha.point(lambda v: 0 if v < 110 else (255 if v > 165 else v))

    out = src.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(out.getbbox())


def shadow_for(product, blur=26, opacity=64, squash=0.13):
    """Soft elliptical contact shadow. The CAD view has none and the module floats."""
    w, h = product.size
    pad = blur * 3
    canvas = Image.new("L", (w + pad * 2, int(h * squash) + pad * 2), 0)
    ImageDraw.Draw(canvas).ellipse(
        (pad, pad, pad + w, pad + int(h * squash)), fill=opacity
    )
    return canvas.filter(ImageFilter.GaussianBlur(blur))


def backdrop(size):
    """Vertical cream gradient with a soft vignette - the Trail Kitchens studio look."""
    w, h = size
    bg = Image.new("RGB", (w, h), CREAM)
    grad = Image.new("L", (1, h))
    grad.putdata([int(30 * (y / h) ** 1.4) for y in range(h)])
    bg = Image.composite(Image.new("RGB", (w, h), CREAM_EDGE), bg, grad.resize((w, h)))
    return bg


def compose(product, size, module_id, name, footer=True):
    w, h = size
    card = backdrop(size).convert("RGBA")
    draw = ImageDraw.Draw(card)

    # Reserve space for the caption block so the product never collides with type.
    top_pad = int(h * 0.10)
    bot_pad = int(h * 0.26) if footer else int(h * 0.10)
    box_w, box_h = int(w * 0.80), h - top_pad - bot_pad
    scale = min(box_w / product.width, box_h / product.height)
    pw, ph = int(product.width * scale), int(product.height * scale)
    prod = product.resize((pw, ph), Image.LANCZOS)

    cx = (w - pw) // 2
    cy = top_pad + (box_h - ph) // 2

    sh = shadow_for(prod)
    sh_x = cx + (pw - sh.width) // 2
    sh_y = cy + ph - int(sh.height * 0.55)
    card.paste(Image.new("RGB", sh.size, (60, 70, 58)), (sh_x, sh_y), sh)
    card.alpha_composite(prod, (cx, cy))

    if footer:
        left = int(w * 0.10)
        base = h - bot_pad + int(h * 0.055)
        draw.line((left, base - int(h * 0.035), left + 54, base - int(h * 0.035)),
                  fill=ACCENT, width=4)

        # The wordmark sits on the same baseline, so the title gets whatever width
        # is left after it. Long names ("Camp Furniture/Soft Goods") shrink to fit
        # rather than running under the wordmark.
        mark_font = font(int(h * 0.030), True)
        mark = "BEAR NECESSITIES"
        mark_w = draw.textlength(mark, font=mark_font)
        avail = w - left * 2 - mark_w - int(w * 0.04)

        size = int(h * 0.058)
        title_font = font(size, True)
        while size > 12 and draw.textlength(name, font=title_font) > avail:
            size -= 2
            title_font = font(size, True)

        draw.text((left, base), name, font=title_font, fill=INK)
        sub = "%s   ·   %d\" W × %d\" D × %d\" H" % (
            module_id, MODULE_W_IN, MODULE_D_IN, MODULE_H_IN)
        draw.text((left, base + int(h * 0.075)), sub,
                  font=font(int(h * 0.036)), fill=FOREST)
        draw.text((w - left, base), mark, font=mark_font, fill=SAGE, anchor="ra")
    return card.convert("RGB")


def main():
    names = {}
    fam = json.loads((STUDY / "module-family.json").read_text())
    mods = fam.get("modules", fam)
    for m in (mods if isinstance(mods, list) else mods.values()):
        names[m["id"]] = m.get("name", m["id"])

    OUT.mkdir(parents=True, exist_ok=True)
    made, missing = [], []
    for i in range(1, 11):
        mid = "BN-M%02d" % i
        src = EXPORTS / mid / (mid + "-iso.png")
        if not src.exists():
            missing.append(mid)
            continue
        product = key_background(Image.open(src))
        product.save(OUT / (mid + "-alpha.png"))
        compose(product, (1600, 1200), mid, names.get(mid, mid)).save(
            OUT / (mid + "-card.png"), optimize=True)
        compose(product, (1200, 1200), mid, names.get(mid, mid)).save(
            OUT / (mid + "-square.png"), optimize=True)
        made.append(mid)
        print("  ok  %s  %s  (cutout %dx%d)" % (mid, names.get(mid, ""),
                                                product.width, product.height))

    print("\n%d/10 modules rendered -> %s" % (len(made), OUT))
    if missing:
        print("MISSING native iso export: %s" % ", ".join(missing), file=sys.stderr)
        return 1
    return 0


def _selfcheck():
    """Keying must remove the border but keep light interior pixels."""
    img = Image.new("RGB", (60, 60), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle((15, 15, 45, 45), fill=(40, 40, 40))     # body
    d.rectangle((25, 25, 35, 35), fill=(252, 252, 252))  # near-white highlight inside
    out = key_background(img)
    assert out.size == (31, 31), "cutout should trim to the body, got %r" % (out.size,)
    # centre highlight survives; it is enclosed by the body, not connected to the edge
    assert out.getpixel((15, 15))[3] == 255, "interior highlight was punched out"
    print("selfcheck ok")


if __name__ == "__main__":
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        sys.exit(main())
