"""Drawing primitives for fill-in pages (grayscale, black-ink interiors).

A box is (x, y, w, h) with (x, y) bottom-left, in points.
"""
import math
from reportlab.pdfbase.pdfmetrics import stringWidth
from .core import INK, MID, LINE, SOFT, TINT, MIN_FONT_PT

GAP = 8


# ---------------------------------------------------------------- layout
def vsplit(box, parts, gap=GAP):
    """Split box top->bottom. parts: numbers (pt, fixed) or strings 'Nf' (flex weight)."""
    x, y, w, h = box
    fixed = sum(p for p in parts if not isinstance(p, str))
    flex = sum(float(p[:-1]) for p in parts if isinstance(p, str))
    free = h - fixed - gap * (len(parts) - 1)
    out, top = [], y + h
    for p in parts:
        ph = p if not isinstance(p, str) else free * float(p[:-1]) / flex
        out.append((x, top - ph, w, ph))
        top -= ph + gap
    return out


def hsplit(box, parts, gap=GAP):
    x, y, w, h = box
    fixed = sum(p for p in parts if not isinstance(p, str))
    flex = sum(float(p[:-1]) for p in parts if isinstance(p, str))
    free = w - fixed - gap * (len(parts) - 1)
    out, left = [], x
    for p in parts:
        pw = p if not isinstance(p, str) else free * float(p[:-1]) / flex
        out.append((left, y, pw, h))
        left += pw + gap
    return out


def inset(box, d):
    x, y, w, h = box
    return (x + d, y + d, w - 2 * d, h - 2 * d)


# ---------------------------------------------------------------- text
def fit(text, font, size, maxw, minsize=MIN_FONT_PT):
    while size > minsize and stringWidth(text, font, size) > maxw:
        size -= 0.25
    return max(size, minsize)


def label(c, th, x, y, text, size=7.6, gray=MID, font=None, align="left", maxw=None):
    font = font or th.label
    t = text.upper() if th.label_caps else text
    if not th.label_caps:
        size = size + 1.4  # serif labels need more size to read the same
    if maxw:
        size = fit(t, font, size, maxw)
    c.setFillGray(gray)
    c.setFont(font, size)
    if align == "left":
        c.drawString(x, y, t)
    elif align == "center":
        c.drawCentredString(x, y, t)
    else:
        c.drawRightString(x, y, t)
    return stringWidth(t, font, size)


def label_w(th, text, size=7.6):
    t = text.upper() if th.label_caps else text
    s = size if th.label_caps else size + 1.4
    return stringWidth(t, th.label, s)


def hline(c, x1, x2, y, gray=LINE, w=0.5):
    c.setStrokeGray(gray)
    c.setLineWidth(w)
    c.line(x1, y, x2, y)


def vline(c, x, y1, y2, gray=SOFT, w=0.5):
    c.setStrokeGray(gray)
    c.setLineWidth(w)
    c.line(x, y1, x, y2)


def checkbox(c, x, y, s=7.5, gray=MID):
    c.setStrokeGray(gray)
    c.setLineWidth(0.7)
    c.roundRect(x, y, s, s, 1.2, stroke=1, fill=0)


def circle(c, x, y, r, gray=MID, w=0.6):
    c.setStrokeGray(gray)
    c.setLineWidth(w)
    c.circle(x, y, r, stroke=1, fill=0)


def star(c, cx, cy, r, gray=MID):
    c.setStrokeGray(gray)
    c.setLineWidth(0.6)
    p = c.beginPath()
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        px, py = cx + rr * math.cos(ang), cy + rr * math.sin(ang)
        (p.moveTo if i == 0 else p.lineTo)(px, py)
    p.close()
    c.drawPath(p, stroke=1, fill=0)


def stars(c, x, y, n=5, r=5.2, gap=3.5):
    for i in range(n):
        star(c, x + r + i * (2 * r + gap), y + r * 0.9, r)
    return n * (2 * r + gap)


# ---------------------------------------------------------------- header
def header(c, th, box, title, right=None, sub=None):
    """Draw page title at top of box, return remaining box."""
    x, y, w, h = box
    if th.key == "walter":
        bh = 30
        top = y + h
        c.setFillGray(TINT)
        c.rect(x, top - bh, w, bh, stroke=0, fill=1)
        c.setFillGray(INK)
        c.rect(x, top - bh, 5, bh, stroke=0, fill=1)
        size = fit(title.upper(), th.head, 21, w - 30 - (label_w(th, right, 7.6) + 20 if right else 0))
        c.setFont(th.head, size)
        c.drawString(x + 14, top - bh + 9, title.upper())
        if right:
            label(c, th, x + w - 10, top - bh + 11.5, right, gray=MID, align="right")
        used = bh
        if sub:
            c.setFont(th.italic, 7.8)
            c.setFillGray(MID)
            c.drawString(x, top - bh - 12, sub)
            used += 14
        return (x, y, w, h - used - 10)
    else:
        top = y + h
        size = fit(title, th.head, 22, w - 20)
        c.setFillGray(INK)
        c.setFont(th.head, size)
        c.drawCentredString(x + w / 2, top - 20, title)
        ry = top - 30
        hline(c, x, x + w / 2 - 8, ry, gray=MID, w=0.6)
        hline(c, x + w / 2 + 8, x + w, ry, gray=MID, w=0.6)
        c.setFillGray(MID)
        cx = x + w / 2
        p = c.beginPath()
        p.moveTo(cx, ry + 3.5); p.lineTo(cx + 3.5, ry); p.lineTo(cx, ry - 3.5); p.lineTo(cx - 3.5, ry); p.close()
        c.drawPath(p, stroke=0, fill=1)
        used = 34
        if right:
            label(c, th, x + w, ry - 12, right, align="right")
            used += 12
        if sub:
            c.setFont(th.italic, 9.5)
            c.setFillGray(MID)
            c.drawCentredString(x + w / 2, ry - 13, sub)
            used = max(used, 47)
        return (x, y, w, h - used - 8)


# ---------------------------------------------------------------- fields
def field(c, th, x, y, w, text, gray=LINE):
    lw = label(c, th, x, y + 2.5, text) if text else 0
    hline(c, x + lw + (5 if text else 0), x + w, y, gray=gray)


def fields(c, th, box, rows, row_h=24, colgap=14):
    """rows: list of rows, each a list of labels (or (label, weight))."""
    x, y, w, h = box
    top = y + h
    n = 0
    for row in rows:
        if top - row_h < y - 0.1:
            break
        items = [r if isinstance(r, tuple) else (r, 1) for r in row]
        tot = sum(wt for _, wt in items)
        free = w - colgap * (len(items) - 1)
        cx = x
        for lab, wt in items:
            cw = free * wt / tot
            field(c, th, cx, top - row_h + 6, cw, lab)
            cx += cw + colgap
        top -= row_h
        n += 1
    return (x, y, w, top - y)


def lines(c, th, box, spacing=22, first=None, gray=LINE, numbered=False):
    x, y, w, h = box
    yy = y + h - (first or spacing)
    i = 1
    while yy >= y - 0.1:
        if numbered:
            c.setFont(th.label, 7.5 if th.label_caps else 8.5)
            c.setFillGray(SOFT)
            c.drawRightString(x + 10, yy + 3, str(i))
            hline(c, x + 14, x + w, yy, gray=gray)
        else:
            hline(c, x, x + w, yy, gray=gray)
        yy -= spacing
        i += 1


def panel(c, th, box, title=None, spacing=None, radius=5, numbered=False, tint=False):
    x, y, w, h = box
    c.setStrokeGray(SOFT)
    c.setLineWidth(0.8)
    if tint:
        c.setFillGray(0.96)
        c.roundRect(x, y, w, h, radius, stroke=1, fill=1)
    else:
        c.roundRect(x, y, w, h, radius, stroke=1, fill=0)
    inner_top = y + h - 8
    if title:
        label(c, th, x + 9, y + h - 15, title, gray=INK, maxw=w - 18)
        inner_top = y + h - 22
    if spacing:
        lines(c, th, (x + 9, y + 6, w - 18, inner_top - y - 6), spacing=spacing, numbered=numbered)
    return (x + 9, y + 6, w - 18, inner_top - y - 6)


def table(c, th, box, cols, row_h=20, header_h=20, numbered=False, rows=None):
    """cols: list of (label, weight). Draws a ruled log table filling the box."""
    x, y, w, h = box
    tot = sum(wt for _, wt in cols)
    if numbered:
        cols = [("#", tot * 0.035)] + list(cols)
        tot = sum(wt for _, wt in cols)
    widths = [w * wt / tot for _, wt in cols]
    top = y + h
    c.setFillGray(TINT)
    c.rect(x, top - header_h, w, header_h, stroke=0, fill=1)
    cx = x
    for (lab, _), cw in zip(cols, widths):
        if lab and lab != "#":
            label(c, th, cx + 4, top - header_h + 7, lab, gray=INK, maxw=cw - 8)
        cx += cw
    nrows = rows or int((h - header_h) // row_h)
    bottom = top - header_h - nrows * row_h
    yy = top - header_h
    for i in range(nrows):
        yy -= row_h
        hline(c, x, x + w, yy, gray=LINE)
        if numbered:
            c.setFont(th.label, 7)
            c.setFillGray(SOFT)
            c.drawCentredString(x + widths[0] / 2, yy + row_h / 2 - 2.5, str(i + 1))
    cx = x
    for cw in widths[:-1]:
        cx += cw
        vline(c, cx, bottom, top - header_h, gray=SOFT)
    hline(c, x, x + w, top - header_h, gray=MID, w=0.8)
    return bottom


def checklist(c, th, box, items, cols=1, row_h=17, size=None, colgap=12, line_after=False):
    x, y, w, h = box
    per = math.ceil(len(items) / cols)
    cw = (w - colgap * (cols - 1)) / cols
    font = th.body if th.key == "sal" else "Poppins"
    size = size or (10 if th.key == "sal" else 8.2)
    for i, it in enumerate(items):
        col, row = divmod(i, per)
        cx = x + col * (cw + colgap)
        cy = y + h - (row + 1) * row_h + 4
        if cy < y - 0.1:
            continue
        checkbox(c, cx, cy, 7.5)
        if it:
            c.setFont(font, fit(it, font, size, cw - 14))
            c.setFillGray(INK)
            c.drawString(cx + 13, cy + 0.8, it)
            if line_after:
                tw = stringWidth(it, font, size)
                if tw + 30 < cw:
                    hline(c, cx + 18 + tw, cx + cw, cy, gray=SOFT)
        else:
            hline(c, cx + 13, cx + cw, cy, gray=LINE)


def checkgrid(c, th, box, items, colheads, row_h=17, item_frac=0.55, header_h=18):
    """Rows of items with a tick box under each column heading."""
    x, y, w, h = box
    iw = w * item_frac
    cw = (w - iw) / len(colheads)
    top = y + h
    c.setFillGray(TINT)
    c.rect(x, top - header_h, w, header_h, stroke=0, fill=1)
    for j, ch in enumerate(colheads):
        label(c, th, x + iw + cw * j + cw / 2, top - header_h + 6.5, ch, gray=INK, align="center", maxw=cw - 4)
    font = th.body if th.key == "sal" else "Poppins"
    size = 10 if th.key == "sal" else 8
    yy = top - header_h
    for it in items:
        if yy - row_h < y - 0.1:
            break
        yy -= row_h
        hline(c, x, x + w, yy, gray=SOFT)
        c.setFillGray(INK)
        if it:
            c.setFont(font, fit(it, font, size, iw - 8))
            c.drawString(x + 4, yy + row_h / 2 - 3, it)
        for j in range(len(colheads)):
            checkbox(c, x + iw + cw * j + cw / 2 - 3.75, yy + row_h / 2 - 3.75)
    return yy


def dotgrid(c, box, step=14, gray=0.55, r=0.55):
    x, y, w, h = box
    nx, ny = int(w // step), int(h // step)
    ox = x + (w - nx * step) / 2
    oy = y + (h - ny * step) / 2
    c.setFillGray(gray)
    for i in range(nx + 1):
        for j in range(ny + 1):
            c.circle(ox + i * step, oy + j * step, r, stroke=0, fill=1)


def gridpaper(c, box, step=14):
    x, y, w, h = box
    nx, ny = int(w // step), int(h // step)
    ox = x + (w - nx * step) / 2
    oy = y + (h - ny * step) / 2
    for i in range(nx + 1):
        vline(c, ox + i * step, oy, oy + ny * step, gray=0.78, w=0.35)
    for j in range(ny + 1):
        hline(c, ox, ox + nx * step, oy + j * step, gray=0.78, w=0.35)


def scale(c, th, x, y, text, n=5, r=5):
    lw = label(c, th, x, y, text)
    cx = x + lw + 8
    for i in range(n):
        circle(c, cx + r + i * (2 * r + 6), y + 2.5, r)
        c.setFont(th.label, 7 if th.label_caps else 7.5)
        c.setFillGray(SOFT)
        c.drawCentredString(cx + r + i * (2 * r + 6), y + 0.3, str(i + 1))
    return cx + n * (2 * r + 6)


def month_grid(c, th, box, start_monday=False, header_h=16):
    x, y, w, h = box
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] if start_monday else \
           ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    cw = w / 7
    top = y + h
    c.setFillGray(TINT)
    c.rect(x, top - header_h, w, header_h, stroke=0, fill=1)
    for i, d in enumerate(days):
        label(c, th, x + cw * i + cw / 2, top - header_h + 5, d, gray=INK, align="center")
    rh = (h - header_h) / 5
    c.setStrokeGray(LINE)
    c.setLineWidth(0.5)
    for r in range(6):
        hline(c, x, x + w, top - header_h - r * rh, gray=LINE)
    for i in range(8):
        vline(c, x + i * cw, y, top - header_h, gray=LINE)
    for r in range(5):
        for i in range(7):
            circle(c, x + i * cw + 9, top - header_h - r * rh - 9, 6, gray=SOFT, w=0.5)
