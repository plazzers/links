"""Generate the 1200x630 social preview images (og.jpg) and the optimized
host photos for both link pages, plus the og.jpg for each free tool
(walter/house-age/, sal/restaurant-or-home/).

Run from the repo root:  python3 tools/make_og.py
Needs Pillow (pip install pillow). Reads source-assets/*.jpg.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H = 1200, 630
FONTS = Path("/usr/share/fonts/truetype/liberation")
SANS_BOLD = FONTS / "LiberationSans-Bold.ttf"
SANS = FONTS / "LiberationSans-Regular.ttf"
SERIF_BOLD = FONTS / "LiberationSerif-Bold.ttf"
SERIF_ITALIC = FONTS / "LiberationSerif-Italic.ttf"

# Square crop boxes (left, top, right, bottom) on the 800x800 source photos,
# chosen so the face sits in the middle of the round frame.
CROPS = {"walter": (80, 20, 700, 640), "sal": (95, 0, 705, 610)}


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def square_photo(name, size):
    im = Image.open(ROOT / "source-assets" / f"{name}.jpg").convert("RGB")
    return im.crop(CROPS[name]).resize((size, size), Image.LANCZOS)


def save_page_photo(name):
    """Optimized square photo for the page (<= 80 KB) + apple-touch-icon."""
    out = ROOT / name / "assets"
    out.mkdir(parents=True, exist_ok=True)
    im = square_photo(name, 480)
    for q in (82, 76, 70, 64):
        im.save(out / f"{name}.jpg", quality=q, optimize=True, progressive=True)
        if (out / f"{name}.jpg").stat().st_size <= 80_000:
            break
    icon = im.resize((180, 180), Image.LANCZOS).quantize(128, method=Image.MEDIANCUT)
    icon.save(out / "apple-touch-icon.png", optimize=True)


def circle(im, ring, ring_w, halo=None, halo_w=0):
    size = im.size[0]
    pad = ring_w + halo_w
    total = size + 2 * pad
    canvas = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    if halo:
        d.ellipse((0, 0, total - 1, total - 1), fill=hexrgb(halo))
    d.ellipse((halo_w, halo_w, total - halo_w - 1, total - halo_w - 1), fill=hexrgb(ring))
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.LANCZOS)
    canvas.paste(im, (pad, pad), mask)
    return canvas


def shadow(base, layer, xy, blur=24, offset=12, alpha=120, pad=0):
    """pad > 0 gives the blur room so the shadow fades out instead of being
    cut off at the layer's edges."""
    a = layer.split()[-1].point(lambda v: alpha if v else 0)
    sh = Image.new("RGBA", (layer.width + 2 * pad, layer.height + 2 * pad), (0, 0, 0, 0))
    sa = Image.new("L", sh.size, 0)
    sa.paste(a, (pad, pad))
    sh.putalpha(sa)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(sh, (xy[0] - pad, xy[1] + offset - pad))
    base.alpha_composite(layer, xy)


def text_layer(text, font, fill, squeeze=1.0, tracking=0):
    """Render text to its own RGBA layer. squeeze < 1 condenses it horizontally
    (stand-in for a condensed display face); tracking adds letter spacing."""
    asc, desc = font.getmetrics()
    widths = [font.getlength(c) for c in text]
    w = int(sum(widths) + tracking * (len(text) - 1)) + 4
    layer = Image.new("RGBA", (w, asc + desc), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x = 0
    for c, cw in zip(text, widths):
        d.text((x, 0), c, font=font, fill=fill)
        x += cw + tracking
    if squeeze != 1.0:
        layer = layer.resize((max(1, int(layer.width * squeeze)), layer.height), Image.LANCZOS)
    return layer


def fit(text, path, start, max_w, fill, squeeze=1.0, tracking_em=0.0):
    size = start
    while True:
        font = ImageFont.truetype(str(path), size)
        layer = text_layer(text, font, fill, squeeze, int(size * tracking_em))
        if layer.width <= max_w or size <= 20:
            return layer
        size -= 2


def pill(text, font, bg, fg, pad_x=26, pad_y=16):
    tl = text_layer(text, font, fg)
    asc, desc = font.getmetrics()
    w, h = tl.width + 2 * pad_x, asc + 2 * pad_y
    p = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=hexrgb(bg))
    p.alpha_composite(tl, (pad_x, pad_y - 2))
    return p


def walter():
    navy, denim, paper, orange, wood = "#1C2B3A", "#3E5F8A", "#F2EDE4", "#E07A1F", "#6B4A2F"
    base = Image.new("RGBA", (W, H), hexrgb(navy))
    d = ImageDraw.Draw(base)
    # subtle blueprint grid
    for x in range(0, W, 40):
        d.line((x, 0, x, H), fill=(36, 54, 73, 255))
    for y in range(0, H, 40):
        d.line((0, y, W, y), fill=(36, 54, 73, 255))
    d.rectangle((0, H - 18, W, H), fill=hexrgb(wood))
    d.rectangle((0, H - 24, W, H - 18), fill=hexrgb(orange))

    photo = circle(square_photo("walter", 400), orange, 10, "#243649", 12)
    shadow(base, photo, (60, 85))

    x0, max_w = 540, 600
    l1 = fit("WALTER'S", SANS_BOLD, 132, max_w, hexrgb(paper), squeeze=0.78, tracking_em=0.04)
    l2 = fit("HOME CHECK", SANS_BOLD, 132, max_w, hexrgb(paper), squeeze=0.78, tracking_em=0.04)
    y = 118
    base.alpha_composite(l1, (x0, y)); y += l1.height - 6
    base.alpha_composite(l2, (x0, y)); y += l2.height + 14
    d.rectangle((x0 + 2, y, x0 + 92, y + 8), fill=hexrgb(orange)); y += 30
    tag = fit("WHAT HOMEOWNERS MISS", SANS_BOLD, 50, max_w, hexrgb(orange), squeeze=0.82, tracking_em=0.12)
    base.alpha_composite(tag, (x0, y)); y += tag.height + 30
    p = pill("FREE: The Weekend Home Check", ImageFont.truetype(str(SANS_BOLD), 30), denim, paper)
    base.alpha_composite(p, (x0, y))
    return base.convert("RGB")


def sal():
    esp, cream, muted, red, olive = "#2A1E18", "#FAF4E8", "#D9CBB5", "#BE3A24", "#586E34"
    base = Image.new("RGBA", (W, H), hexrgb(esp))
    # warm radial glow behind the photo
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((-40, 20, 620, 680), fill=(70, 48, 36, 255))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(base)
    third = W // 3
    d.rectangle((0, 0, third, 14), fill=hexrgb(olive))
    d.rectangle((third, 0, 2 * third, 14), fill=hexrgb(cream))
    d.rectangle((2 * third, 0, W, 14), fill=hexrgb(red))

    photo = circle(square_photo("sal", 400), cream, 8, red, 12)
    shadow(base, photo, (60, 100))

    x0, max_w = 540, 610
    small = fit("CHEF", SERIF_BOLD, 44, max_w, hexrgb(muted), tracking_em=0.35)
    y = 126
    base.alpha_composite(small, (x0 + 4, y)); y += small.height + 2
    l1 = fit("SAL ROMANO", SERIF_BOLD, 112, max_w, hexrgb(cream), tracking_em=0.04)
    base.alpha_composite(l1, (x0, y)); y += l1.height + 16
    d.rectangle((x0 + 4, y, x0 + 34, y + 5), fill=hexrgb(olive))
    d.rectangle((x0 + 34, y, x0 + 64, y + 5), fill=hexrgb(cream))
    d.rectangle((x0 + 64, y, x0 + 94, y + 5), fill=hexrgb(red)); y += 30
    t1 = fit("What the restaurants", SERIF_ITALIC, 54, max_w, hexrgb(cream))
    t2 = fit("won't tell you.", SERIF_ITALIC, 54, max_w, hexrgb(cream))
    base.alpha_composite(t1, (x0, y)); y += t1.height
    base.alpha_composite(t2, (x0, y)); y += t2.height + 28
    p = pill("FREE: Sal's 25 Rules for Eating Out", ImageFont.truetype(str(SANS_BOLD), 28), red, cream)
    base.alpha_composite(p, (x0, y))
    return base.convert("RGB")


def walter_tool():
    """Share picture for walter/house-age/."""
    navy, navy2, denim, paper, orange, wood = "#1C2B3A", "#243649", "#3E5F8A", "#F2EDE4", "#E07A1F", "#6B4A2F"
    base = Image.new("RGBA", (W, H), hexrgb(navy))
    d = ImageDraw.Draw(base)
    for x in range(0, W, 40):
        d.line((x, 0, x, H), fill=(36, 54, 73, 255))
    for y in range(0, H, 40):
        d.line((0, y, W, y), fill=(36, 54, 73, 255))
    d.rectangle((0, H - 18, W, H), fill=hexrgb(wood))
    d.rectangle((0, H - 24, W, H - 18), fill=hexrgb(orange))

    x0, max_w = 70, 870
    p = pill("FREE TOOL", ImageFont.truetype(str(SANS_BOLD), 30), orange, navy, pad_x=20, pad_y=12)
    base.alpha_composite(p, (x0, 62))
    brand = fit("WALTER'S HOME CHECK", SANS_BOLD, 26, 400, hexrgb("#B9C3CF"), tracking_em=0.18)
    base.alpha_composite(brand, (x0 + p.width + 22, 62 + (p.height - brand.height) // 2 + 2))
    photo = circle(square_photo("walter", 150), orange, 6, navy2, 6)
    shadow(base, photo, (W - 70 - photo.width, 140), blur=12, offset=6, pad=30)
    y = 140
    for line in ("WHAT TO CHECK IN A", "HOUSE BUILT IN..."):
        l = fit(line, SANS_BOLD, 118, max_w, hexrgb(paper), squeeze=0.78, tracking_em=0.03)
        base.alpha_composite(l, (x0, y)); y += l.height - 4
    y += 22
    font = ImageFont.truetype(str(SANS_BOLD), 34)
    x = x0
    for i, label in enumerate(("1950s", "1960s", "1970s", "1980s", "1990s", "2000s")):
        c = pill(label, font, orange if label == "1970s" else denim, navy if label == "1970s" else paper, pad_x=20, pad_y=14)
        base.alpha_composite(c, (x, y)); x += c.width + 14
    y += 96
    tag = fit("PICK THE YEAR. GET YOUR CHECKLIST.", SANS_BOLD, 40, max_w, hexrgb(orange), squeeze=0.85, tracking_em=0.1)
    base.alpha_composite(tag, (x0, y))
    return base.convert("RGB")


def sal_tool():
    """Share picture for sal/restaurant-or-home/."""
    esp, esp2, cream, muted, red, olive = "#2A1E18", "#36281F", "#FAF4E8", "#D9CBB5", "#BE3A24", "#586E34"
    base = Image.new("RGBA", (W, H), hexrgb(esp))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((560, -80, 1300, 700), fill=(70, 48, 36, 255))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(base)
    third = W // 3
    d.rectangle((0, 0, third, 14), fill=hexrgb(olive))
    d.rectangle((third, 0, 2 * third, 14), fill=hexrgb(cream))
    d.rectangle((2 * third, 0, W, 14), fill=hexrgb(red))

    x0 = 70
    p = pill("FREE CALCULATOR", ImageFont.truetype(str(SANS_BOLD), 28), cream, red, pad_x=20, pad_y=12)
    base.alpha_composite(p, (x0, 66))
    t1 = fit("Restaurant", SERIF_BOLD, 120, 640, hexrgb(cream))
    t2 = fit("or Home?", SERIF_BOLD, 120, 640, hexrgb(cream))
    y = 140
    base.alpha_composite(t1, (x0, y)); y += t1.height - 6
    base.alpha_composite(t2, (x0, y)); y += t2.height + 18
    d.rectangle((x0 + 4, y, x0 + 34, y + 5), fill=hexrgb(olive))
    d.rectangle((x0 + 34, y, x0 + 64, y + 5), fill=hexrgb(cream))
    d.rectangle((x0 + 64, y, x0 + 94, y + 5), fill=hexrgb(red)); y += 28
    sub = fit("See what you keep by cooking it yourself.", SERIF_ITALIC, 40, 640, hexrgb(muted))
    base.alpha_composite(sub, (x0, y))

    # receipt-style comparison card
    cx, cy, cw, ch = 760, 110, 370, 400
    card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=24, fill=hexrgb(cream))
    lab = ImageFont.truetype(str(SANS_BOLD), 24)
    big = ImageFont.truetype(str(SERIF_BOLD), 76)
    cd.text((32, 30), "DINNER FOR 4, OUT", font=lab, fill=hexrgb("#7a6655"))
    cd.text((32, 62), "~$96", font=big, fill=hexrgb(esp))
    cd.line((32, 168, cw - 32, 168), fill=hexrgb(muted), width=3)
    cd.text((32, 186), "AT HOME", font=lab, fill=hexrgb("#7a6655"))
    cd.text((32, 218), "~$14", font=big, fill=hexrgb(olive))
    cd.rounded_rectangle((24, 318, cw - 24, ch - 24), radius=16, fill=hexrgb(red))
    keep = ImageFont.truetype(str(SERIF_BOLD), 40)
    kt = "You keep ~$82"
    cd.text(((cw - cd.textlength(kt, font=keep)) / 2, 328), kt, font=keep, fill=hexrgb(cream))
    shadow(base, card, (cx, cy), blur=20, offset=10, alpha=140, pad=60)
    photo = circle(square_photo("sal", 110), cream, 5, red, 6)
    shadow(base, photo, (cx + cw - 80, cy - 50), blur=10, offset=6, pad=30)
    small = fit("CHEF SAL ROMANO", SERIF_BOLD, 26, 400, hexrgb(muted), tracking_em=0.2)
    base.alpha_composite(small, (x0, H - 76))
    return base.convert("RGB")


def wrap_fit(text, path, start, max_w, max_lines, fill, squeeze=1.0, min_size=40, max_h=10_000, gap=0):
    """Word-wrap text into at most max_lines lines, shrinking the font until it fits."""
    size = start
    while True:
        font = ImageFont.truetype(str(path), size)
        lines, cur = [], ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if font.getlength(trial) * squeeze <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
        widest = max(font.getlength(l) * squeeze for l in lines)
        asc, desc = font.getmetrics()
        tall = len(lines) * (asc + desc + gap)
        if (len(lines) <= max_lines and widest <= max_w and tall <= max_h) or size <= min_size:
            return [text_layer(l, font, fill, squeeze) for l in lines]
        size -= 4


def guide_og(channel, title, label):
    """Share picture for a guide article or page (1200x630): brand look + title."""
    if channel == "walter":
        navy, navy2, paper, orange, wood, muted = "#1C2B3A", "#243649", "#F2EDE4", "#E07A1F", "#6B4A2F", "#B9C3CF"
        base = Image.new("RGBA", (W, H), hexrgb(navy))
        d = ImageDraw.Draw(base)
        for x in range(0, W, 40):
            d.line((x, 0, x, H), fill=(36, 54, 73, 255))
        for y in range(0, H, 40):
            d.line((0, y, W, y), fill=(36, 54, 73, 255))
        d.rectangle((0, H - 18, W, H), fill=hexrgb(wood))
        d.rectangle((0, H - 24, W, H - 18), fill=hexrgb(orange))
        x0, max_w = 70, 1060
        p = pill(label.upper(), ImageFont.truetype(str(SANS_BOLD), 28), orange, navy, pad_x=20, pad_y=12)
        base.alpha_composite(p, (x0, 64))
        lines = wrap_fit(title.upper(), SANS_BOLD, 108, max_w, 3, hexrgb(paper), squeeze=0.8, min_size=56, max_h=310, gap=-4)
        y = 150
        for l in lines:
            base.alpha_composite(l, (x0, y)); y += l.height - 4
        photo = circle(square_photo("walter", 96), orange, 5, navy2, 5)
        shadow(base, photo, (x0, H - 150), blur=10, offset=5, pad=30)
        brand = fit("WALTER'S HOME CHECK", SANS_BOLD, 34, 600, hexrgb(paper), squeeze=0.85, tracking_em=0.12)
        base.alpha_composite(brand, (x0 + photo.width + 22, H - 136))
        tag = fit("WHAT HOMEOWNERS MISS", SANS_BOLD, 24, 600, hexrgb(muted), tracking_em=0.18)
        base.alpha_composite(tag, (x0 + photo.width + 24, H - 90))
        return base.convert("RGB")
    esp, cream, muted, red, olive = "#2A1E18", "#FAF4E8", "#D9CBB5", "#BE3A24", "#586E34"
    base = Image.new("RGBA", (W, H), hexrgb(esp))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((500, -120, 1400, 640), fill=(70, 48, 36, 255))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(base)
    third = W // 3
    d.rectangle((0, 0, third, 14), fill=hexrgb(olive))
    d.rectangle((third, 0, 2 * third, 14), fill=hexrgb(cream))
    d.rectangle((2 * third, 0, W, 14), fill=hexrgb(red))
    x0, max_w = 70, 1060
    p = pill(label.upper(), ImageFont.truetype(str(SANS_BOLD), 26), red, cream, pad_x=20, pad_y=12)
    base.alpha_composite(p, (x0, 66))
    lines = wrap_fit(title, SERIF_BOLD, 96, max_w, 3, hexrgb(cream), min_size=52, max_h=300)
    y = 150
    for l in lines:
        base.alpha_composite(l, (x0, y)); y += l.height
    y += 10
    d.rectangle((x0 + 4, y, x0 + 34, y + 5), fill=hexrgb(olive))
    d.rectangle((x0 + 34, y, x0 + 64, y + 5), fill=hexrgb(cream))
    d.rectangle((x0 + 64, y, x0 + 94, y + 5), fill=hexrgb(red))
    photo = circle(square_photo("sal", 96), cream, 4, red, 5)
    shadow(base, photo, (x0, H - 150), blur=10, offset=5, pad=30)
    brand = fit("CHEF SAL ROMANO", SERIF_BOLD, 36, 600, hexrgb(cream), tracking_em=0.12)
    base.alpha_composite(brand, (x0 + photo.width + 22, H - 134))
    tag = fit("What the restaurants won't tell you.", SERIF_ITALIC, 28, 600, hexrgb(muted))
    base.alpha_composite(tag, (x0 + photo.width + 24, H - 88))
    return base.convert("RGB")


def avatar_webp(name, out, size=128):
    """Small round-crop-ready author photo for the guide pages."""
    square_photo(name, size).save(out, "WEBP", quality=80, method=6)


if __name__ == "__main__":
    for name, make in (("walter", walter), ("sal", sal)):
        save_page_photo(name)
        out = ROOT / name / "og.jpg"
        make().save(out, quality=86, optimize=True, progressive=True)
        print(out.relative_to(ROOT), out.stat().st_size // 1024, "KB")
    for folder, make in (("walter/house-age", walter_tool), ("sal/restaurant-or-home", sal_tool)):
        out = ROOT / folder / "og.jpg"
        make().save(out, quality=86, optimize=True, progressive=True)
        print(out.relative_to(ROOT), out.stat().st_size // 1024, "KB")
