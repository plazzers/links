"""Simple original line-art icons drawn with vector paths (no external art).

Each icon is drawn inside a unit square (0..1) scaled to `size`.
"""
import math


def _setup(c, cx, cy, size, stroke, lw):
    c.saveState()
    c.translate(cx - size / 2, cy - size / 2)
    c.scale(size, size)
    c.setLineWidth(lw / size)
    c.setLineJoin(1)
    c.setLineCap(1)
    c.setStrokeColorRGB(*stroke)


def _poly(c, pts, close=True, fill=False):
    p = c.beginPath()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    if close:
        p.close()
    c.drawPath(p, stroke=1, fill=1 if fill else 0)


def _line(c, *pts):
    _poly(c, pts, close=False)


def _house(c, x0=0.14, x1=0.86, base=0.12, wall=0.52, peak=0.86, door=True, chimney=True):
    if chimney:
        _poly(c, [(x1 - 0.2, wall + 0.17), (x1 - 0.2, peak - 0.06), (x1 - 0.1, peak - 0.06), (x1 - 0.1, wall + 0.09)], close=False)
    _poly(c, [(x0 - 0.06, wall), ((x0 + x1) / 2, peak), (x1 + 0.06, wall)], close=False)
    _poly(c, [(x0, wall - 0.02), (x0, base), (x1, base), (x1, wall - 0.02)], close=False)
    if door:
        mx = (x0 + x1) / 2
        _poly(c, [(mx - 0.07, base), (mx - 0.07, base + 0.22), (mx + 0.07, base + 0.22), (mx + 0.07, base)], close=False)


def draw_icon(c, name, cx, cy, size, stroke, lw=3.0, accent=None):
    accent = accent or stroke
    _setup(c, cx, cy, size, stroke, lw)
    fn = ICONS[name]
    fn(c, accent)
    c.restoreState()


def i_house_check(c, a):
    _house(c, door=False)
    c.setStrokeColorRGB(*a)
    _line(c, (0.36, 0.33), (0.47, 0.22), (0.66, 0.43))


def i_key_house(c, a):
    _house(c, x0=0.08, x1=0.62, wall=0.48, peak=0.80, door=True, chimney=False)
    c.setStrokeColorRGB(*a)
    c.circle(0.78, 0.62, 0.11, stroke=1, fill=0)
    _line(c, (0.78, 0.51), (0.78, 0.14))
    _line(c, (0.78, 0.22), (0.86, 0.22))
    _line(c, (0.78, 0.31), (0.84, 0.31))


def i_magnifier_house(c, a):
    _house(c, x0=0.10, x1=0.60, base=0.30, wall=0.62, peak=0.88, chimney=False)
    c.setStrokeColorRGB(*a)
    c.circle(0.62, 0.38, 0.17, stroke=1, fill=0)
    _line(c, (0.74, 0.26), (0.92, 0.08))


def i_victorian(c, a):
    # tall narrow house with steep gable, turret and round window
    _poly(c, [(0.30, 0.10), (0.30, 0.58), (0.86, 0.58), (0.86, 0.10)], close=False)
    _poly(c, [(0.24, 0.56), (0.58, 0.92), (0.92, 0.56)], close=False)
    _poly(c, [(0.08, 0.10), (0.08, 0.50), (0.30, 0.50)], close=False)
    _poly(c, [(0.04, 0.48), (0.16, 0.76), (0.28, 0.58)], close=False)
    c.circle(0.58, 0.68, 0.06, stroke=1, fill=0)
    c.setStrokeColorRGB(*a)
    _poly(c, [(0.50, 0.10), (0.50, 0.34), (0.66, 0.34), (0.66, 0.10)], close=False)
    _poly(c, [(0.13, 0.24), (0.13, 0.38), (0.24, 0.38), (0.24, 0.24)])


def i_duplex(c, a):
    _poly(c, [(0.08, 0.10), (0.08, 0.58), (0.92, 0.58), (0.92, 0.10)], close=False)
    _poly(c, [(0.02, 0.56), (0.28, 0.84), (0.50, 0.62), (0.72, 0.84), (0.98, 0.56)], close=False)
    _line(c, (0.50, 0.62), (0.50, 0.10))
    _line(c, (0.04, 0.10), (0.96, 0.10))
    c.setStrokeColorRGB(*a)
    for x in (0.22, 0.64):
        _poly(c, [(x, 0.10), (x, 0.32), (x + 0.12, 0.32), (x + 0.12, 0.10)], close=False)
    for x in (0.13, 0.75):
        _poly(c, [(x, 0.40), (x, 0.50), (x + 0.12, 0.50), (x + 0.12, 0.40)])


def i_house_clipboard(c, a):
    _poly(c, [(0.18, 0.06), (0.18, 0.86), (0.82, 0.86), (0.82, 0.06)])
    _poly(c, [(0.36, 0.82), (0.36, 0.94), (0.64, 0.94), (0.64, 0.82)])
    c.setStrokeColorRGB(*a)
    _house(c, x0=0.36, x1=0.64, base=0.52, wall=0.64, peak=0.76, door=False, chimney=False)
    for y in (0.40, 0.28, 0.16):
        _line(c, (0.28, y), (0.72, y))


def i_recipe_card(c, a):
    _poly(c, [(0.08, 0.16), (0.08, 0.84), (0.92, 0.84), (0.92, 0.16)])
    c.setStrokeColorRGB(*a)
    # heart
    p = c.beginPath()
    p.moveTo(0.50, 0.44)
    p.curveTo(0.30, 0.56, 0.30, 0.74, 0.42, 0.74)
    p.curveTo(0.47, 0.74, 0.50, 0.70, 0.50, 0.66)
    p.curveTo(0.50, 0.70, 0.53, 0.74, 0.58, 0.74)
    p.curveTo(0.70, 0.74, 0.70, 0.56, 0.50, 0.44)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeColorRGB(*a)
    for y in (0.34, 0.25):
        _line(c, (0.20, y), (0.80, y))


def i_cloche(c, a):
    p = c.beginPath()
    p.moveTo(0.10, 0.34)
    p.curveTo(0.12, 0.74, 0.88, 0.74, 0.90, 0.34)
    c.drawPath(p, stroke=1, fill=0)
    _line(c, (0.04, 0.30), (0.96, 0.30))
    c.circle(0.50, 0.68, 0.04, stroke=1, fill=0)
    c.setStrokeColorRGB(*a)
    c.circle(0.70, 0.44, 0.13, stroke=1, fill=0)
    _line(c, (0.79, 0.35), (0.94, 0.18))
    for x in (0.30, 0.42):
        p = c.beginPath()
        p.moveTo(x, 0.80); p.curveTo(x - 0.05, 0.86, x + 0.05, 0.90, x, 0.96)
        c.drawPath(p, stroke=1, fill=0)


def i_calendar_fork(c, a):
    _poly(c, [(0.08, 0.08), (0.08, 0.80), (0.92, 0.80), (0.92, 0.08)])
    _line(c, (0.08, 0.64), (0.92, 0.64))
    _line(c, (0.28, 0.88), (0.28, 0.72))
    _line(c, (0.72, 0.88), (0.72, 0.72))
    c.setStrokeColorRGB(*a)
    # fork
    _line(c, (0.38, 0.54), (0.38, 0.40))
    _line(c, (0.44, 0.54), (0.44, 0.40))
    _line(c, (0.50, 0.54), (0.50, 0.40))
    p = c.beginPath(); p.moveTo(0.38, 0.40); p.curveTo(0.38, 0.32, 0.50, 0.32, 0.50, 0.40)
    c.drawPath(p, stroke=1, fill=0)
    _line(c, (0.44, 0.34), (0.44, 0.16))
    # knife
    p = c.beginPath(); p.moveTo(0.62, 0.16); p.lineTo(0.62, 0.54)
    p.curveTo(0.70, 0.50, 0.70, 0.38, 0.62, 0.34)
    c.drawPath(p, stroke=1, fill=0)


def i_pasta_fork(c, a):
    # fork, tines up, twirled spaghetti nest
    _line(c, (0.50, 0.04), (0.50, 0.46))
    for x in (0.40, 0.47, 0.53, 0.60):
        _line(c, (x, 0.70), (x, 0.92))
    p = c.beginPath(); p.moveTo(0.40, 0.70); p.curveTo(0.40, 0.58, 0.60, 0.58, 0.60, 0.70)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeColorRGB(*a)
    for i, (ry, rx) in enumerate(((0.07, 0.24), (0.07, 0.22), (0.07, 0.20))):
        y = 0.62 - i * 0.07
        c.ellipse(0.50 - rx, y - ry, 0.50 + rx, y + ry, stroke=1, fill=0)
    p = c.beginPath(); p.moveTo(0.30, 0.50); p.curveTo(0.22, 0.36, 0.26, 0.24, 0.18, 0.14)
    c.drawPath(p, stroke=1, fill=0)
    p = c.beginPath(); p.moveTo(0.70, 0.50); p.curveTo(0.78, 0.38, 0.74, 0.26, 0.82, 0.16)
    c.drawPath(p, stroke=1, fill=0)


def i_basket(c, a):
    _poly(c, [(0.06, 0.52), (0.94, 0.52)], close=False)
    _poly(c, [(0.12, 0.52), (0.22, 0.10), (0.78, 0.10), (0.88, 0.52)], close=False)
    p = c.beginPath(); p.moveTo(0.26, 0.52); p.curveTo(0.26, 0.90, 0.74, 0.90, 0.74, 0.52)
    c.drawPath(p, stroke=1, fill=0)
    for x in (0.38, 0.50, 0.62):
        _line(c, (x, 0.44), (x, 0.18))
    c.setStrokeColorRGB(*a)
    c.circle(0.80, 0.24, 0.15, stroke=1, fill=0)
    c.circle(0.80, 0.24, 0.09, stroke=1, fill=0)


def i_chef_hat(c, a):
    p = c.beginPath()
    p.moveTo(0.28, 0.40)
    p.curveTo(0.06, 0.44, 0.10, 0.80, 0.32, 0.72)
    p.curveTo(0.34, 0.96, 0.66, 0.96, 0.68, 0.72)
    p.curveTo(0.90, 0.80, 0.94, 0.44, 0.72, 0.40)
    c.drawPath(p, stroke=1, fill=0)
    _poly(c, [(0.28, 0.40), (0.28, 0.22), (0.72, 0.22), (0.72, 0.40)], close=False)
    c.setStrokeColorRGB(*a)
    _line(c, (0.28, 0.30), (0.72, 0.30))
    # little whisk
    c.ellipse(0.80, 0.10, 0.94, 0.40, stroke=1, fill=0)
    _line(c, (0.87, 0.10), (0.87, 0.40))
    _line(c, (0.87, 0.10), (0.87, 0.02))


def i_tomato(c, a):
    p = c.beginPath()
    p.moveTo(0.50, 0.70)
    p.curveTo(0.20, 0.74, 0.06, 0.56, 0.10, 0.38)
    p.curveTo(0.14, 0.14, 0.36, 0.06, 0.50, 0.08)
    p.curveTo(0.64, 0.06, 0.86, 0.14, 0.90, 0.38)
    p.curveTo(0.94, 0.56, 0.80, 0.74, 0.50, 0.70)
    c.drawPath(p, stroke=1, fill=0)
    c.setStrokeColorRGB(*a)
    # leaves
    for (x, y) in ((0.30, 0.68), (0.40, 0.60), (0.60, 0.60), (0.70, 0.68)):
        _line(c, (0.50, 0.70), (x, y))
    _line(c, (0.50, 0.70), (0.52, 0.90))
    p = c.beginPath(); p.moveTo(0.52, 0.90); p.curveTo(0.58, 0.94, 0.64, 0.92, 0.66, 0.88)
    c.drawPath(p, stroke=1, fill=0)
    # highlight
    p = c.beginPath(); p.moveTo(0.22, 0.42); p.curveTo(0.22, 0.30, 0.28, 0.24, 0.34, 0.20)
    c.drawPath(p, stroke=1, fill=0)


ICONS = {
    "tomato": i_tomato,
    "house_check": i_house_check, "key_house": i_key_house, "magnifier_house": i_magnifier_house,
    "victorian": i_victorian, "duplex": i_duplex, "house_clipboard": i_house_clipboard,
    "recipe_card": i_recipe_card, "cloche": i_cloche, "calendar_fork": i_calendar_fork,
    "pasta_fork": i_pasta_fork, "basket": i_basket, "chef_hat": i_chef_hat,
}
