"""Pinterest pin factory for Walter's Home Check and Chef Sal Romano.

Reads the pin content from tools/pins_walter.yaml and tools/pins_sal.yaml and
writes, for each channel:

  pins/<channel>/NNN-slug.jpg        1000x1500 pins (sRGB JPEG, < 350 KB)
  pins/pinterest-bulk-<channel>.csv  Pinterest bulk-create CSV
  pins/contact-<channel>.jpg         contact sheet of every pin
plus pins/index.html, a noindex gallery for reviewing everything.

Weekly batches: pins with  week: YYYY-MM-DD  in the YAML are kept out of the
big bulk CSV and go to pins/weekly/<week>-<channel>.csv (+ a contact sheet
pins/weekly/<week>-<channel>.jpg). Each weekly batch is scheduled 3 a day
from the day after the last publish date of the batches before it, so old
schedules never move.

Run from the repo root:   python3 tools/make_pins.py
Only one channel:         python3 tools/make_pins.py walter
Then check the output:    python3 tools/check_pins.py

Needs Python 3 with Pillow and PyYAML (pip install pillow pyyaml). Fonts are
vendored in tools/fonts/ (all SIL Open Font License, see the OFL-*.txt files).
The cut-out host photos (source-assets/*-cutout.png) were made once from
source-assets/<name>.jpg with a background-removal model; the script only
reads them.
"""
import csv
import html
import io
import re
import sys
from datetime import datetime, timedelta
from functools import lru_cache
from itertools import combinations
from pathlib import Path
from urllib.parse import quote

import yaml
from PIL import Image, ImageChops, ImageCms, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "pins"
SITE = "https://plazzers.github.io/links/"
W, H = 1000, 1500
X0, X1 = 70, 930            # left / right text margin
MAX_BYTES = 350_000
START = datetime(2026, 10, 10)
SLOTS = (13, 17, 21)         # UTC publish hours, 3 pins a day per channel
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

LINKS = {
    "walter": SITE + "walter/",
    "house-age": SITE + "walter/house-age/",
    "sal": SITE + "sal/",
    "restaurant-or-home": SITE + "sal/restaurant-or-home/",
}


# ---------------------------------------------------------------- basics

def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgba(h, a=255):
    return rgb(h) + (a,)


@lru_cache(None)
def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def cap_height(f):
    b = f.getbbox("H")
    return b[3] - b[1]


def tracked(draw, xy, text, f, fill, track=0.0, anchor="ls"):
    """Draw text with letter spacing (track in em). anchor: ls (left) or rs
    (right-aligned at x). Returns the drawn width."""
    sp = f.size * track
    w = tracked_width(text, f, track)
    x, y = xy
    if anchor == "rs":
        x -= w
    for c in text:
        draw.text((x, y), c, font=f, fill=fill, anchor="ls")
        x += f.getlength(c) + sp
    return w


def tracked_width(text, f, track):
    return sum(f.getlength(c) for c in text) + f.size * track * (len(text) - 1)


def caps(text):
    """Uppercase, but keep decades readable: 1970s, not 1970S."""
    return re.sub(r"(\d)S\b", r"\1s", text.upper())


def parse_rich(text):
    """'FIND YOUR *WATER SHUTOFF*' -> [(word, emphasized), ...]; a '|' forces
    a line break."""
    words, hot = [], False
    for part in re.split(r"(\*|\|)", text):
        if part == "|":
            words.append(("|", False))
            continue
        if part == "*":
            hot = not hot
            continue
        toks = part.split()
        # punctuation right after an emphasized run sticks to the last word
        if toks and part[0] != " " and all(not ch.isalnum() for ch in toks[0]) \
                and words and words[-1][0] != "|":
            words[-1] = (words[-1][0] + toks.pop(0), words[-1][1])
        for w in toks:
            words.append((w, hot))
    return words


def line_width(words, f):
    return f.getlength(" ".join(w for w, _ in words))


HARD = 10 ** 12  # penalty that marks a split as ugly


def best_breaks(words, f, max_w, max_lines, strict=False):
    """Split words into the fewest lines that fit max_w, then pick the
    nicest split of that count: even line lengths, no lone short word on a
    line (widow), emphasized phrases kept together. With strict=True, ugly
    splits are rejected (returns None) so the caller can try a smaller size.
    Returns a list of lines or None."""
    n = len(words)
    for k in range(1, min(max_lines, n) + 1):
        best, best_score = None, None
        for cuts in combinations(range(1, n), k - 1):
            bounds = (0,) + cuts + (n,)
            lines = [words[bounds[i]:bounds[i + 1]] for i in range(k)]
            widths = [line_width(l, f) for l in lines]
            if max(widths) > max_w:
                continue
            score = sum((max_w - w) ** 2 for w in widths[:-1]) + 0.25 * (max_w - widths[-1]) ** 2
            if k > 1:
                for l, w in zip(lines, widths):
                    if len(l) == 1 and w < 0.42 * max_w:
                        score += HARD
            # keep an emphasized phrase on one line when possible
            score += sum(2 * max_w ** 2 for c in cuts if words[c - 1][1] and words[c][1])
            if best_score is None or score < best_score:
                best, best_score = lines, score
        if best:
            if strict and best_score >= HARD:
                return None
            return best
    return None


def wrap_plain(text, f, max_w, max_lines=99):
    lines = best_breaks([(w, False) for w in text.split()], f, max_w, max_lines)
    return None if lines is None else [" ".join(w for w, _ in l) for l in lines]


def draw_rich_lines(draw, x, y, lines, f, color, hot, line_h):
    """Lines of (word, emphasized) pairs; baseline of first line at y."""
    space = f.getlength(" ")
    for line in lines:
        cx = x
        for w, is_hot in line:
            draw.text((cx, y), w, font=f, fill=hot if is_hot else color, anchor="ls")
            cx += f.getlength(w) + space
        y += line_h
    return y


def fit_headline(text, fname, sizes, max_w, max_lines, max_h, lead):
    """Largest size whose wrapped headline fits max_w x max_h."""
    words = parse_rich(text)
    if any(w == "|" for w, _ in words):  # manual line breaks
        forced, cur = [], []
        for w in words:
            if w[0] == "|":
                forced.append(cur)
                cur = []
            else:
                cur.append(w)
        forced.append(cur)
        for size in sizes:
            f = font(fname, size)
            if max(line_width(l, f) for l in forced) <= max_w and \
                    cap_height(f) + (len(forced) - 1) * size * lead <= max_h:
                return f, forced
        raise ValueError(f"headline does not fit: {text!r}")
    for strict in (True, False):
        for size in sizes:
            f = font(fname, size)
            lines = best_breaks(words, f, max_w, max_lines, strict)
            if lines and cap_height(f) + (len(lines) - 1) * size * lead <= max_h:
                return f, lines
    raise ValueError(f"headline does not fit: {text!r}")


# ---------------------------------------------------------------- photos

@lru_cache(None)
def cutout(name):
    im = Image.open(ROOT / "source-assets" / f"{name}-cutout.png").convert("RGBA")
    a = im.split()[-1].filter(ImageFilter.GaussianBlur(1.2))  # soften the cut edge
    im.putalpha(a)
    return im


def place_host(base, name, size, xy, ring, ring_box, ring_w, fade_left, fade_bottom=0):
    """Cut-out host photo standing in front of a thin ring, like the style
    reference: head breaks out of the circle, shirt fades out to the left."""
    d = ImageDraw.Draw(base)
    # ring (supersampled for a smooth edge)
    l, t, r, b = ring_box
    ss = 4
    ringl = Image.new("L", ((r - l) * ss, (b - t) * ss), 0)
    ImageDraw.Draw(ringl).ellipse((0, 0, (r - l) * ss - 1, (b - t) * ss - 1), outline=255, width=ring_w * ss)
    ringl = ringl.resize((r - l, b - t), Image.LANCZOS)
    layer = Image.new("RGBA", ringl.size, ring)
    layer.putalpha(ringl)
    base.alpha_composite(layer, (l, t))

    im = cutout(name).resize((size, size), Image.LANCZOS)
    a = im.split()[-1]
    grad = Image.new("L", im.size, 255)
    gd = ImageDraw.Draw(grad)
    # fade the left side (the source is cut off there), strongest at the bottom
    for x in range(fade_left):
        v = int(255 * (x / fade_left) ** 1.4)
        gd.line((x, int(size * 0.45), x, size), fill=v)
    if fade_bottom:
        for i in range(fade_bottom):
            y = size - fade_bottom + i
            v = int(255 * (1 - i / fade_bottom) ** 1.2)
            row = grad.crop((0, y, size, y + 1)).point(lambda p, v=v: min(p, v))
            grad.paste(row, (0, y))
    a = ImageChops.multiply(a, grad)
    im.putalpha(a)
    # soft shadow so the cut-out sits on the background
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(a.point(lambda v: v * 0.45).filter(ImageFilter.GaussianBlur(18)))
    base.alpha_composite(sh, (xy[0] - 10, xy[1] + 8))
    base.alpha_composite(im, xy)


# ---------------------------------------------------------------- shared parts

def save_jpeg(im, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    for q in (88, 84, 80, 76, 72):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True, progressive=True,
                subsampling="4:2:0", icc_profile=SRGB)
        if buf.tell() < MAX_BYTES:
            break
    path.write_bytes(buf.getvalue())
    return buf.tell()


def pill_button(draw, x, y, text, f, bg, fg, pad_x, pad_y, radius, track=0.0):
    w = tracked_width(text, f, track)
    ch = cap_height(f)
    h = ch + 2 * pad_y
    draw.rounded_rectangle((x, y, x + w + 2 * pad_x, y + h), radius=radius, fill=bg)
    tracked(draw, (x + pad_x, y + pad_y + ch), text, f, fg, track)
    return w + 2 * pad_x, h


# ================================================================ WALTER

WN = dict(navy="#1C2B3A", grid="#25374A", grid2="#2A3E52", paper="#F2EDE4",
          orange="#E07A1F", tape="#E9B12A", tape_dark="#8A6512", muted="#B8C1CC",
          denim="#3E5F8A")
OSWALD, SS3, INTER_B = "Oswald-Bold.ttf", "SourceSans3-SemiBold.ttf", "Inter-Bold.otf"


def walter_background():
    base = Image.new("RGBA", (W, H), rgba(WN["navy"]))
    d = ImageDraw.Draw(base)
    for i, x in enumerate(range(0, W + 1, 36)):
        d.line((x, 0, x, H), fill=rgba(WN["grid2"] if i % 5 == 0 else WN["grid"]), width=1)
    for i, y in enumerate(range(0, H + 1, 36)):
        d.line((0, y, W, y), fill=rgba(WN["grid2"] if i % 5 == 0 else WN["grid"]), width=1)
    # gentle vignette so the grid fades toward the edges
    v = Image.new("L", (W, H), 0)
    ImageDraw.Draw(v).ellipse((-300, -200, W + 300, H + 300), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(160))
    dark = Image.new("RGBA", (W, H), rgba("#16222E"))
    dark.putalpha(v.point(lambda p: int((255 - p) * 0.55)))
    base.alpha_composite(dark)
    return base


def tape(draw, x, y, w, h=18):
    draw.rounded_rectangle((x, y, x + w, y + h), radius=3, fill=rgb(WN["tape"]))
    for i, tx in enumerate(range(x + 8, x + w - 4, 9)):
        th = h * 0.55 if i % 5 == 0 else h * 0.32
        draw.line((tx, y + 2, tx, y + 2 + th), fill=rgb(WN["tape_dark"]), width=2)


def walter_pin(p):
    base = walter_background()
    d = ImageDraw.Draw(base)
    is_list = bool(p.get("items"))

    # host photo first, text on top
    if is_list:
        place_host(base, "walter", 520, (540, 1010), rgba(WN["orange"]),
                   (590, 1060, 1010, 1480), 4, fade_left=200)
    else:
        place_host(base, "walter", 700, (400, 805), rgba(WN["orange"]),
                   (470, 860, 1100, 1490), 4, fade_left=260)

    small = font(INTER_B, 24)
    tracked(d, (X0, 86), "WALTER'S HOME CHECK", small, rgb(WN["paper"]), 0.14)
    tracked(d, (X1, 86), "WHAT HOMEOWNERS MISS", small, rgb(WN["orange"]), 0.14, anchor="rs")

    kick = font(INTER_B, 29)
    tracked(d, (X0, 200), caps(p["kicker"]), kick, rgb(WN["orange"]), 0.16)

    top = 238
    f = font(SS3, 40)
    if is_list:
        rest = 58 + 18 + 34 + 8 + len(p["items"]) * 74 - 22
        limit = 1150
    else:
        body = wrap_plain(p["body"], f, X1 - X0 - 10, 3)
        if body is None:
            raise ValueError(f"body too long: {p['slug']}")
        rest = 58 + 18 + 34 + 30 + (len(body) - 1) * 54 + 10
        limit = 815  # Walter's head starts below this
    hf, lines = fit_headline(caps(p["headline"]), OSWALD, range(150 if not is_list else 120, 86, -2),
                             X1 - X0, 4 if not is_list else 3, limit - top - rest, 0.98)
    lead = int(hf.size * 0.98)
    y = top + cap_height(hf)
    y = draw_rich_lines(d, X0, y, lines, hf, rgb(WN["paper"]), rgb(WN["orange"]), lead) - lead
    y += 58
    tape(d, X0, y, 420)
    y += 18 + 34

    if is_list:
        nf = font(OSWALD, 38)
        row = 74
        y += 8
        for i, item in enumerate(p["items"], 1):
            d.rounded_rectangle((X0, y, X0 + 52, y + 52), radius=6, fill=rgb(WN["orange"]))
            d.text((X0 + 26, y + 27), str(i), font=nf, fill=rgb(WN["navy"]), anchor="mm")
            maxw = (X1 - X0 - 76) if y + 52 < 1030 else 530
            if f.getlength(item) > maxw:
                raise ValueError(f"list item too long: {item!r}")
            d.text((X0 + 76, y + 40), item, font=f, fill=rgb(WN["paper"]), anchor="ls")
            y += row
        content_bottom = y - row + 52
    else:
        y += 30
        for line in body:
            d.text((X0, y), line, font=f, fill=rgb(WN["paper"]), anchor="ls")
            y += 54
        content_bottom = y - 54 + 10
    p["_bottom"] = content_bottom

    tagf = font(OSWALD, 50)
    pill_button(d, X0, 1262, caps(p["tag"]), tagf, rgb(WN["orange"]), rgb(WN["navy"]), 28, 20, 8, 0.01)
    tracked(d, (X0, 1424), "YOUTUBE · WALTER'S HOME CHECK", font(INTER_B, 24), rgb(WN["muted"]), 0.14)
    return base.convert("RGB")


# ================================================================ SAL

SN = dict(esp="#2A1E18", esp2="#36281F", esp3="#433228", cream="#FAF4E8", muted="#D9CBB5",
          dim="#A8957F", red="#BE3A24", red_text="#E2583D", olive="#586E34", olive_text="#9DB46B")
PF_B, PF_I, INTER_M, INTER_SB = "PlayfairDisplay-Bold.ttf", "PlayfairDisplay-MediumItalic.ttf", "Inter-Medium.otf", "Inter-SemiBold.otf"


def sal_background():
    base = Image.new("RGBA", (W, H), rgba(SN["esp"]))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((300, 850, 1300, 1700), fill=(78, 54, 40, 255))
    ImageDraw.Draw(glow).ellipse((-300, -200, 700, 600), fill=(56, 40, 31, 255))
    base.alpha_composite(glow.filter(ImageFilter.GaussianBlur(140)))
    d = ImageDraw.Draw(base)
    third = W // 3
    d.rectangle((0, 0, third, 12), fill=rgb(SN["olive"]))
    d.rectangle((third, 0, 2 * third, 12), fill=rgb(SN["cream"]))
    d.rectangle((2 * third, 0, W, 12), fill=rgb(SN["red"]))
    return base


# --- simple line icons (drawn at 4x and scaled down for smooth strokes)

def icon(kind, size=46, color=SN["muted"]):
    s = 4
    S = size * s
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = rgba(color)
    lw = int(3.2 * s)
    if kind == "clock":
        d.ellipse((lw, lw, S - lw, S - lw), outline=c, width=lw)
        m = S // 2
        d.line((m, m, m, int(S * 0.24)), fill=c, width=lw)
        d.line((m, m, int(S * 0.70), int(S * 0.60)), fill=c, width=lw)
        d.ellipse((m - lw, m - lw, m + lw, m + lw), fill=c)
    elif kind == "list":
        d.rounded_rectangle((int(S * .14), lw, int(S * .86), S - lw), radius=int(S * .1), outline=c, width=lw)
        d.rounded_rectangle((int(S * .36), 0, int(S * .64), int(S * .16)), radius=int(S * .05), fill=c)
        for k, yy in enumerate((0.38, 0.56, 0.74)):
            y = int(S * yy)
            d.ellipse((int(S * .28) - lw, y - lw, int(S * .28) + lw, y + lw), fill=c)
            d.line((int(S * .40), y, int(S * .72), y), fill=c, width=lw)
    elif kind == "coin":
        d.ellipse((lw, lw, S - lw, S - lw), outline=c, width=lw)
        f = font("Inter-Bold.otf", int(S * 0.56))
        d.text((S // 2, S // 2 + s), "$", font=f, fill=c, anchor="mm")
    return im.resize((size, size), Image.LANCZOS)


def quote_box(base, x, y, w, text, label="SAL SAYS", max_lines=4):
    """'Sal says' box: italic serif quote in a rounded panel with a red label."""
    d = ImageDraw.Draw(base)
    for size in (42, 40, 38, 36, 34):
        qf = font(PF_I, size)
        lines = wrap_plain(text, qf, w - 80, max_lines)
        if lines:
            break
    else:
        raise ValueError(f"quote too long: {text!r}")
    lh = int(qf.size * 1.32)
    h = 52 + cap_height(qf) + (len(lines) - 1) * lh + 40
    panel = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle((0, 0, w - 1, h - 1), radius=22, fill=rgba(SN["esp2"], 235),
                                            outline=rgba(SN["esp3"]), width=2)
    base.alpha_composite(panel, (x, y))
    d.rectangle((x, y + 22, x + 6, y + h - 22), fill=rgb(SN["red"]))
    lf = font(INTER_B, 20)
    tw = tracked_width(label, lf, 0.18)
    d.rounded_rectangle((x + 34, y - 17, x + 34 + tw + 32, y + 19), radius=18, fill=rgb(SN["red"]))
    tracked(d, (x + 50, y + 9), label, lf, rgb(SN["cream"]), 0.18)
    ty = y + 52 + cap_height(qf)
    for line in lines:
        d.text((x + 40, ty), line, font=qf, fill=rgb(SN["cream"]), anchor="ls")
        ty += lh
    return h


def stats_row(base, y, stats):
    """Row of 3 stats with icons: [(icon, value, label), ...]."""
    d = ImageDraw.Draw(base)
    d.line((X0, y, X1, y), fill=rgb(SN["esp3"]), width=2)
    h = 116
    d.line((X0, y + h, X1, y + h), fill=rgb(SN["esp3"]), width=2)
    colw = (X1 - X0) / 3
    vf, lf = font(INTER_B, 38), font(INTER_SB, 19)
    for i, (ic, val, lab) in enumerate(stats):
        cx = int(X0 + i * colw)
        if i:
            d.line((cx, y + 22, cx, y + h - 22), fill=rgb(SN["esp3"]), width=2)
        px = cx + (18 if i else 0)
        base.alpha_composite(icon(ic), (px, y + 34))
        tx = px + 62
        avail = int(colw) - (tx - cx) - 8
        vsize = 38
        while font(INTER_B, vsize).getlength(val) > avail:
            vsize -= 2
        d.text((tx, y + 56), val, font=font(INTER_B, vsize), fill=rgb(SN["cream"]), anchor="ls")
        lsize = 19
        while tracked_width(lab.upper(), font(INTER_SB, lsize), 0.1) > avail and lsize > 15:
            lsize -= 1
        tracked(d, (tx, y + 88), lab.upper(), font(INTER_SB, lsize), rgb(SN["dim"]), 0.1)
    return h


def money_card(base, y, m):
    """Restaurant vs home comparison card (numbers come from the calculator)."""
    w, h = X1 - X0, 360
    x = X0
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle((0, 0, w - 1, h - 1), radius=26, fill=rgba(SN["cream"]))
    lab, big = font(INTER_B, 26), font(PF_B, 80)
    tracked(cd, (40, 76), m["out_label"].upper(), lab, rgb("#7A6655"), 0.1)
    cd.text((w - 40, 84), m["out"], font=big, fill=rgb(SN["esp"]), anchor="rs")
    cd.line((40, 120, w - 40, 120), fill=rgb(SN["muted"]), width=2)
    tracked(cd, (40, 188), "MADE AT HOME", lab, rgb("#7A6655"), 0.1)
    cd.text((w - 40, 196), m["home"], font=big, fill=rgb(SN["olive"]), anchor="rs")
    cd.rounded_rectangle((22, 230, w - 22, h - 22), radius=18, fill=rgb(SN["red"]))
    kf = font(PF_B, 64)
    cd.text((w // 2, 290), f"You keep {m['keep']}", font=kf, fill=rgb(SN["cream"]), anchor="mm")
    sh = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((40, 40, w + 40, h + 40), radius=26, fill=(0, 0, 0, 120))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (x - 40, y - 30))
    base.alpha_composite(card, (x, y))
    d = ImageDraw.Draw(base)
    d.text((x + 4, y + h + 40), m["note"], font=font(INTER_M, 22), fill=rgb(SN["dim"]), anchor="ls")
    return h + 40


def savings_list(base, y, rows):
    d = ImageDraw.Draw(base)
    f, vf = font(INTER_SB, 40), font(INTER_B, 40)
    row = 84
    for i, (name, val) in enumerate(rows, 1):
        d.ellipse((X0, y, X0 + 54, y + 54), fill=rgb(SN["red"]))
        d.text((X0 + 27, y + 28), str(i), font=font(PF_B, 34), fill=rgb(SN["cream"]), anchor="mm")
        d.text((X0 + 76, y + 41), name, font=f, fill=rgb(SN["cream"]), anchor="ls")
        d.text((X1, y + 41), val, font=vf, fill=rgb(SN["olive_text"]), anchor="rs")
        if i < len(rows):
            d.line((X0 + 72, y + row - 12, X1, y + row - 12), fill=rgb(SN["esp3"]), width=2)
        y += row
    return row * len(rows) - 12


SAL_BOTTOM = 985  # Sal's head starts below this


def sal_pin(p):
    """Render a Sal pin; if the content would run into the photo, try again
    with a smaller headline."""
    for top_size in (124, 116, 108, 100):
        im = _sal_pin(p, top_size)
        if p["_bottom"] <= SAL_BOTTOM:
            return im
    raise ValueError(f"content runs into the photo: {p['slug']} ({p['_bottom']})")


def _sal_pin(p, top_size):
    base = sal_background()
    d = ImageDraw.Draw(base)
    kind = p["type"]
    place_host(base, "sal", 560, (500, 1000), rgba(SN["red"]),
               (560, 1040, 1010, 1490), 5, fade_left=220)

    small = font(INTER_B, 24)
    tracked(d, (X0, 84), "CHEF SAL ROMANO", small, rgb(SN["cream"]), 0.14)
    tracked(d, (X1, 84), "WHAT RESTAURANTS WON'T TELL YOU", font(INTER_B, 19), rgb(SN["red_text"]), 0.1, anchor="rs")

    kick = font(INTER_B, 28)
    tracked(d, (X0, 190), p["kicker"].upper(), kick, rgb(SN["red_text"]), 0.16)

    max_h = 300 if kind == "money" else 330
    hf, lines = fit_headline(p["headline"], PF_B, range(top_size, 97, -2), X1 - X0, 3, max_h, 1.06)
    lead = int(hf.size * 1.06)
    y = 226 + cap_height(hf)
    y = draw_rich_lines(d, X0, y, lines, hf, rgb(SN["cream"]), rgb(SN["red_text"]), lead) - lead

    if kind == "recipe":
        y += 30
        sub = font(PF_I, 36)
        sl = wrap_plain(p["sub"], sub, X1 - X0, 2)
        if sl is None:
            raise ValueError(f"sub too long: {p['slug']}")
        y += cap_height(sub) + 6
        for line in sl:
            d.text((X0, y), line, font=sub, fill=rgb(SN["muted"]), anchor="ls")
            y += 48
        y += 4
        stats_row(base, y, [("clock", p["time"], p.get("time_label", "Total time")),
                            ("list", str(p["ingredients"]), "Ingredients"),
                            ("coin", p["cost"], p["cost_label"])])
        y += 116 + 52
        y += quote_box(base, X0, y, X1 - X0, p["quote"], max_lines=3)
    elif kind == "trick":
        y += 62
        bf = font(INTER_M, 40)
        bl = wrap_plain(p["body"], bf, X1 - X0, 4)
        if bl is None:
            raise ValueError(f"body too long: {p['slug']}")
        y += cap_height(bf)
        for line in bl:
            d.text((X0, y), line, font=bf, fill=rgb(SN["muted"]), anchor="ls")
            y += 56
        y += 44
        y += quote_box(base, X0, y, X1 - X0, p["quote"], max_lines=3)
    else:  # money
        y += 56
        if p.get("rows"):
            y += savings_list(base, y, p["rows"])
        else:
            y += money_card(base, y, p["_money"])
    p["_bottom"] = y

    tagf = font(INTER_B, 30)
    pill_button(d, X0, 1270, p["tag"].upper(), tagf, rgb(SN["red"]), rgb(SN["cream"]), 30, 22, 30, 0.12)
    tracked(d, (X0, 1424), "YOUTUBE · CHEF SAL ROMANO", font(INTER_B, 24), rgb(SN["muted"]), 0.14)
    return base.convert("RGB")


# ---------------------------------------------------------------- Sal money math

def calculator_dishes():
    """The dish list of the Restaurant or Home? calculator, so pin numbers
    always match what the calculator shows."""
    src = (ROOT / "sal" / "restaurant-or-home" / "index.html").read_text(encoding="utf-8")
    block = src[src.index("var DISHES = ["):src.index("];", src.index("var DISHES = ["))]
    out = {}
    for m in re.finditer(r"\[(\d+),\s*(['\"])(.*?)\2,\s*([\d.]+),\s*([\d.]+)", block):
        out[int(m.group(1))] = (m.group(3).replace("\\'", "'"), float(m.group(4)), float(m.group(5)))
    return out


def money_numbers(spec, dishes):
    """Same math as the calculator: food + drinks + tip vs home food + drinks."""
    p, t, dr = spec["p"], spec.get("t", 18), spec.get("dr", 3)
    out_plate = sum(dishes[i][1] for i in spec["d"])
    home_plate = sum(dishes[i][2] for i in spec["d"])
    food, drinks = out_plate * p, dr * p
    out = food + drinks + (food + drinks) * t / 100
    home = home_plate * p + (0.5 * p if dr > 0 else 0)
    o, h = round(out), round(home)
    return o, h


def short_dish(name):
    """'Pan-Seared Steak with Garlic Butter' -> 'Pan-Seared Steak'"""
    return name.split(" with ")[0]


def approx(n):
    return f"~${n:,}"


# ---------------------------------------------------------------- schedule, CSV, gallery

def spread_pick(group, last_topic):
    """From one group, take a pin of the topic with the most pins left (but
    not the topic just used), so topics stay spread out to the end."""
    left = {}
    for p in group:
        left[p.get("topic")] = left.get(p.get("topic"), 0) + 1
    for topic in sorted(left, key=lambda t: -left[t]):
        if topic != last_topic:
            return next(p for p in group if p.get("topic") == topic)
    return None


def schedule(pins, start=START):
    """Order the pins so similar topics aren't back to back: always take the
    next pin from the group with the most pins left, skipping the group (and
    topic) just used when possible. Then 3 slots a day."""
    groups = {}
    for p in pins:
        groups.setdefault(p["type"], []).append(p)
    order, last_type, last_topic = [], None, None
    while any(groups.values()):
        cands = sorted((g for g in groups if groups[g]), key=lambda g: -len(groups[g]))
        pick = None
        for g in cands:
            if g == last_type:
                continue
            pick = spread_pick(groups[g], last_topic)
            if pick:
                break
        if pick is None:  # only the last group is left: at least vary the topic
            g = cands[0]
            pick = spread_pick(groups[g], last_topic) or groups[g][0]
        groups[pick["type"]].remove(pick)
        order.append(pick)
        last_type, last_topic = pick["type"], pick.get("topic")
    for i, p in enumerate(order):
        p["publish"] = (start + timedelta(days=i // 3, hours=SLOTS[i % 3])).strftime("%Y-%m-%dT%H:%M:%S")
    return order


def link_for(p):
    # link: walter | house-age | sal | restaurant-or-home, or a site path such
    # as walter/guides/<slug> (a guide article)
    base = LINKS.get(p["link"]) or SITE + p["link"].strip("/") + "/"
    return base + f"?utm_source=pinterest&utm_medium=pin&utm_campaign={p['slug']}"


def write_csv(channel, pins, path=None):
    path = path or OUT / f"pinterest-bulk-{channel}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"])
        for p in sorted(pins, key=lambda p: p["publish"]):
            w.writerow([p["title"], SITE + f"pins/{channel}/{p['file']}", p["board"], "",
                        " ".join(p["description"].split()), link_for(p), p["publish"], ", ".join(p["keywords"])])
    return path


def contact_sheet(channel, pins, cols=10, tw=200, path=None, label=None):
    th = tw * 3 // 2
    pad, lab = 12, 26
    rows = -(-len(pins) // cols)
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + pad + lab) + pad + 50), (238, 236, 232))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 34), label or f"{channel.upper()} — {len(pins)} pins (in file order)", font=font(INTER_B, 26), fill=(30, 30, 30), anchor="ls")
    for i, p in enumerate(sorted(pins, key=lambda p: p["file"])):
        im = Image.open(OUT / channel / p["file"]).resize((tw, th), Image.LANCZOS)
        x = pad + (i % cols) * (tw + pad)
        y = 50 + pad + (i // cols) * (th + pad + lab)
        sheet.paste(im, (x, y))
        label, lf = p["file"], font(INTER_M, 13)
        while lf.getlength(label) > tw:
            label = label[:-2] + "…"
        d.text((x, y + th + 18), label, font=lf, fill=(60, 60, 60), anchor="ls")
    path = path or OUT / f"contact-{channel}.jpg"
    sheet.save(path, quality=85, optimize=True)
    return path


def gallery(all_pins):
    esc = html.escape
    cards = {}
    for channel, pins in all_pins.items():
        out = []
        for p in sorted(pins, key=lambda p: p["publish"]):
            link = link_for(p)
            out.append(f"""<article class="pin">
  <a href="{channel}/{esc(p['file'])}"><img src="{channel}/{esc(p['file'])}" width="1000" height="1500" loading="lazy" alt="{esc(p['title'])}"></a>
  <h3>{esc(p['title'])}</h3>
  <p class="meta"><span class="board">{esc(p['board'])}</span> · <time>{p['publish'].replace('T', ' ')[:16]} UTC</time></p>
  <p class="link"><a href="{esc(link)}">{esc(link.replace(SITE, '/links/'))}</a></p>
  <details><summary>Description</summary><p>{esc(' '.join(p['description'].split()))}</p><p class="kw">{esc(', '.join(p['keywords']))}</p></details>
</article>""")
        cards[channel] = "\n".join(out)
    weekly = " · ".join(f'<a href="weekly/{f.name}">{f.stem}</a>'
                        for f in sorted((OUT / "weekly").glob("*.csv"))) if (OUT / "weekly").is_dir() else ""
    weekly = f"<br>Weekly CSVs: {weekly}" if weekly else ""
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Pin gallery — Walter &amp; Sal</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ margin: 0; font: 15px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; background: #f3f1ed; color: #222; }}
  header {{ padding: 20px 16px 8px; max-width: 1400px; margin: 0 auto; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  h2 {{ font-size: 18px; margin: 28px 0 12px; }}
  nav a {{ margin-right: 14px; }}
  main {{ max-width: 1400px; margin: 0 auto; padding: 0 16px 40px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; }}
  .pin {{ background: #fff; border-radius: 12px; padding: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.08); min-width: 0; }}
  .pin img {{ width: 100%; height: auto; border-radius: 8px; display: block; }}
  .pin h3 {{ font-size: 14px; margin: 10px 0 4px; }}
  .meta, .link {{ font-size: 12.5px; margin: 2px 0; color: #555; overflow-wrap: anywhere; }}
  .board {{ font-weight: 600; color: #333; }}
  details {{ font-size: 12.5px; margin-top: 6px; }}
  .kw {{ color: #777; }}
</style>
</head>
<body>
<header>
  <h1>Pin gallery</h1>
  <p>Review page, not linked from the site. {sum(len(v) for v in all_pins.values())} pins in publish order. CSVs:
  <a href="pinterest-bulk-walter.csv">Walter</a> · <a href="pinterest-bulk-sal.csv">Sal</a> ·
  contact sheets: <a href="contact-walter.jpg">Walter</a> · <a href="contact-sal.jpg">Sal</a>{weekly}</p>
  <nav><a href="#walter">Walter's Home Check</a><a href="#sal">Chef Sal Romano</a></nav>
</header>
<main>
<h2 id="walter">Walter's Home Check ({len(all_pins.get('walter', []))})</h2>
<div class="grid">
{cards.get('walter', '')}
</div>
<h2 id="sal">Chef Sal Romano ({len(all_pins.get('sal', []))})</h2>
<div class="grid">
{cards.get('sal', '')}
</div>
</main>
</body>
</html>
"""
    (OUT / "index.html").write_text(page, encoding="utf-8")


# ---------------------------------------------------------------- main

BOARDS = {
    "walter": {"quick": "Home Maintenance Checklists", "buyer": "Buying a House: Red Flags",
               "older": "Older Homes", "seasonal": "Winter Home Prep", "list": "Home Maintenance Checklists"},
    "sal": {"recipe": "Copycat Restaurant Recipes", "trick": "Restaurant Secrets", "money": "Budget Family Dinners"},
}
DEFAULT_LINK = {"walter": {"older": "house-age"}, "sal": {"money": "restaurant-or-home"}}


def load(channel):
    data = yaml.safe_load((ROOT / "tools" / f"pins_{channel}.yaml").read_text(encoding="utf-8"))
    pins = data["pins"]
    dishes = calculator_dishes() if channel == "sal" else None
    for n, p in enumerate(pins, 1):
        p.setdefault("board", BOARDS[channel][p["type"]])
        p.setdefault("link", DEFAULT_LINK[channel].get(p["type"], channel))
        p["file"] = f"{n:03d}-{p['slug']}.jpg"
        if channel == "sal" and p["type"] == "money" and p.get("calc"):
            o, h = money_numbers(p["calc"], dishes)
            c = p["calc"]
            p["_money"] = {
                "out_label": p.get("out_label", f"At a restaurant, {c['p']} people"),
                "out": approx(o), "home": approx(h), "keep": approx(o - h),
                "note": p.get("note", "Estimates from the Restaurant or Home? calculator"
                          + (f" · tip {c.get('t', 18)}%" if c.get("t", 18) else " · no tip")
                          + (f" · drinks ${c.get('dr', 3)} each" if c.get("dr", 3) else "")),
            }
            p["description"] = p["description"].format(out=approx(o), home=approx(h), keep=approx(o - h),
                                                       year=approx((o - h) * 52))
            p["headline"] = p["headline"].format(out=approx(o), home=approx(h), keep=approx(o - h),
                                                 year=approx((o - h) * 52))
        if channel == "sal" and p.get("rows") == "top_savings":
            best = sorted(dishes.values(), key=lambda d: d[1] - d[2], reverse=True)[:5]
            p["rows"] = [(short_dish(n), f"~${o - h:.0f} a plate") for n, o, h in best]
        elif channel == "sal" and p.get("rows") == "breakdown":
            c = p["calc"]
            t, dr = c.get("t", 18), c.get("dr", 3)
            food = sum(dishes[i][1] for i in c["d"]) * c["p"]
            drinks = dr * c["p"]
            tip = (food + drinks) * t / 100
            o, h = money_numbers(c, dishes)
            p["rows"] = [(f"The food, {c['p']} plates", approx(round(food))),
                         (f"Drinks, {c['p']} people", approx(round(drinks))),
                         (f"The {t}% tip", approx(round(tip))),
                         ("Total at the restaurant", approx(o)),
                         ("Same dinner at home", approx(h))]
        if channel == "sal" and p["type"] == "recipe" and "dish" in p:
            name, out_price, home = dishes[p["dish"]]
            p.setdefault("cost", f"${home:.2f}".replace(".00", ""))
    return pins


def week_of(p):
    w = p.get("week")
    return str(w) if w else None


def schedule_all(channel, pins):
    """Schedule the original batch from START, then each weekly batch from the
    day after the previous batch's last publish date. Returns {week: pins}."""
    base = [p for p in pins if not week_of(p)]
    schedule(base)
    last = max(p["publish"] for p in base)
    weeks = {}
    for p in pins:
        if week_of(p):
            weeks.setdefault(week_of(p), []).append(p)
    for wk in sorted(weeks):
        start = datetime.strptime(last[:10], "%Y-%m-%d") + timedelta(days=1)
        schedule(weeks[wk], start)
        last = max(p["publish"] for p in weeks[wk])
    return base, weeks


def build(channel):
    pins = load(channel)
    folder = OUT / channel
    folder.mkdir(parents=True, exist_ok=True)
    keep = {p["file"] for p in pins}
    for old in folder.glob("*.jpg"):
        if old.name not in keep:
            old.unlink()
    make = walter_pin if channel == "walter" else sal_pin
    for p in pins:
        size = save_jpeg(make(p), folder / p["file"])
        p["_size"] = size
    base, weeks = schedule_all(channel, pins)
    write_csv(channel, base)
    contact_sheet(channel, base)
    for wk, wp in weeks.items():
        write_csv(channel, wp, OUT / "weekly" / f"{wk}-{channel}.csv")
        contact_sheet(channel, wp, cols=7, path=OUT / "weekly" / f"{wk}-{channel}.jpg",
                      label=f"{channel.upper()} — week {wk} — {len(wp)} pins")
        print(f"{channel}: week {wk}: {len(wp)} pins, {wp and min(p['publish'] for p in wp)} .. {max(p['publish'] for p in wp)}")
    print(f"{channel}: {len(pins)} pins, largest {max(p['_size'] for p in pins) // 1024} KB")
    return pins


if __name__ == "__main__":
    which = sys.argv[1:] or ["walter", "sal"]
    built = {}
    for ch in ("walter", "sal"):
        if ch in which:
            built[ch] = build(ch)
        else:
            built[ch] = load(ch)
            schedule_all(ch, built[ch])
    gallery(built)
    print("pins/index.html written")
