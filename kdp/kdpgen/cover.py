"""Full-wrap paperback cover (back + spine + front) with 0.125" bleed, all vector."""
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

from .core import (register_fonts, BLEED, spine_width, SPINE_TEXT_MIN_PAGES, SPINE_CLEARANCE, COVER_SAFE,
                   BARCODE_W, BARCODE_H, BARCODE_OFFSET, MIN_FONT_PT)
from .icons import draw_icon


def mix(a, b, t):
    return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def cover_geometry(spec):
    tw, th_ = spec.trim[0] * inch, spec.trim[1] * inch
    sw = spine_width(spec.pages, spec.paper)
    W = 2 * BLEED + 2 * tw + sw
    H = 2 * BLEED + th_
    g = dict(W=W, H=H, tw=tw, th=th_, sw=sw,
             back=(BLEED, BLEED, tw, th_),
             spine=(BLEED + tw, BLEED, sw, th_),
             front=(BLEED + tw + sw, BLEED, tw, th_))
    bx = BLEED + tw - BARCODE_OFFSET - BARCODE_W
    g["barcode"] = (bx, BLEED + BARCODE_OFFSET, BARCODE_W, BARCODE_H)
    return g


def cap_height(font, size):
    face = pdfmetrics.getFont(font).face
    ch = getattr(face, "capHeight", 700) or 700
    return ch / 1000 * size


def _fit_lines(lines, font, maxw, maxsize):
    size = maxsize
    for ln in lines:
        while stringWidth(ln, font, size) > maxw and size > 10:
            size -= 0.5
    return size


def _blueprint(c, box, col, step):
    x, y, w, h = box
    c.setStrokeColorRGB(*col)
    c.setLineWidth(0.5)
    i = 0
    xx = x + step / 2
    while xx <= x + w + 0.1:
        c.line(xx, y, xx, y + h)
        xx += step
    yy = y
    while yy <= y + h + 0.1:
        c.line(x, yy, x + w, yy)
        yy += step


def _gingham(c, box, base, stripe, step):
    x, y, w, h = box
    midc = mix(base, stripe, 0.45)
    c.setFillColorRGB(*base)
    c.rect(x, y, w, h, stroke=0, fill=1)
    nx, ny = int(w / step) + 2, int(h / step) + 2
    for i in range(nx):
        for j in range(ny):
            a, b = i % 2, j % 2
            if a and b:
                col = stripe
            elif a or b:
                col = midc
            else:
                continue
            cx, cy = x + i * step, y + j * step
            ww = min(step, x + w - cx)
            hh = min(step, y + h - cy)
            if ww > 0 and hh > 0:
                c.setFillColorRGB(*col)
                c.rect(cx, cy, ww, hh, stroke=0, fill=1)


def _para(c, text, x, ytop, w, font, size, color, leading=None, align=0):
    text = text.replace("&", "&amp;")
    st = ParagraphStyle("p", fontName=font, fontSize=size, leading=leading or size * 1.35,
                        textColor=colors.Color(*color), alignment=align)
    p = Paragraph(text, st)
    pw, ph = p.wrap(w, 2000)
    p.drawOn(c, x, ytop - ph)
    return ph


def draw_front(c, spec, g):
    th = spec.theme
    fx, fy, fw, fh = g["front"]
    W, H = g["W"], g["H"]
    dark, acc, light = th.dark, th.accent, th.light
    s = COVER_SAFE
    k = fw / (8.5 * inch)          # scale relative to 8.5" width
    k = max(k, 0.72)
    head = th.head
    caps = th.head_caps
    lines = [l.upper() if caps else l for l in spec.cover_title]
    lay = spec.cover_layout
    right_edge = fx + fw + BLEED   # bleed edge

    if lay == "frame":
        bg, fg, sub = light, dark, mix(dark, light, 0.25)
    else:
        bg, fg, sub = dark, light, mix(light, dark, 0.2)

    # --- background details on the front only
    if th.key == "walter":
        if lay == "band":
            band_h = fh * 0.30
            c.setFillColorRGB(*light)
            c.rect(0, 0, W, BLEED + band_h, stroke=0, fill=1)
            c.setFillColorRGB(*acc)
            c.rect(0, BLEED + band_h, W, 10 * k, stroke=0, fill=1)
            spec._reserve = (BLEED + band_h + 10 * k, 0)
            _blueprint(c, (fx, BLEED + band_h + 10 * k, fw + BLEED, H - BLEED - band_h - 10 * k),
                       mix(dark, light, 0.08), 0.25 * inch)
        elif lay == "split":
            _blueprint(c, (fx, 0, fw + BLEED, H), mix(dark, light, 0.07), 0.25 * inch)
            c.setFillColorRGB(*acc)
            c.rect(fx + fw * 0.08, 0, 14 * k, H, stroke=0, fill=1)
        else:  # frame
            c.setStrokeColorRGB(*dark)
            c.setLineWidth(3 * k)
            c.rect(fx + s, fy + s, fw - 2 * s, fh - 2 * s, stroke=1, fill=0)
            c.setFillColorRGB(*dark)
            c.rect(fx + s, fy + fh * 0.62, fw - 2 * s, fh * 0.38 - s, stroke=0, fill=1)
            _blueprint(c, (fx + s, fy + fh * 0.62, fw - 2 * s, fh * 0.38 - s), mix(dark, light, 0.08), 0.25 * inch)
            c.setFillColorRGB(*acc)
            c.rect(fx + s, fy + fh * 0.62 - 8 * k, fw - 2 * s, 8 * k, stroke=0, fill=1)
    else:
        if lay == "band":
            band_h = fh * 0.24
            _gingham(c, (0, 0, W, BLEED + band_h), light, acc, 0.42 * inch * k)
            c.setFillColorRGB(*acc)
            c.rect(0, BLEED + band_h, W, 6 * k, stroke=0, fill=1)
            spec._reserve = (BLEED + band_h + 6 * k, 0)
        elif lay == "split":
            _gingham(c, (fx + fw - fw * 0.16, 0, fw * 0.16 + BLEED, H), light, acc, 0.32 * inch * k)
        else:  # frame
            _gingham(c, (0, H - BLEED - fh * 0.14, W, fh * 0.14 + BLEED), light, acc, 0.36 * inch * k)
            _gingham(c, (0, 0, W, BLEED + fh * 0.07), light, acc, 0.36 * inch * k)
            spec._reserve = (BLEED + fh * 0.07, BLEED + fh * 0.14)
            c.setStrokeColorRGB(*dark)
            c.setLineWidth(1.6 * k)
            c.rect(fx + s, fy + fh * 0.07 + 12 * k, fw - 2 * s, fh * 0.79 - 24 * k, stroke=1, fill=0)

    # --- text block
    tx0, tx1 = fx + s + 14 * k, fx + fw - s - 14 * k
    if lay == "split" and th.key == "walter":
        tx0 = fx + fw * 0.08 + 14 * k + 24 * k
    if lay == "split" and th.key == "sal":
        tx1 = fx + fw - fw * 0.16 - 18 * k
    tw_ = tx1 - tx0
    maxsize = (118 if caps else 82) * k
    size = _fit_lines(lines, head, tw_, maxsize)
    center = lay != "split"
    cx = (tx0 + tx1) / 2

    if th.key == "walter" and lay == "frame":
        ytop = fy + fh * 0.62 - 40 * k
        kick_y = fy + fh - s - 30 * k
        kick_col = acc
    elif th.key == "sal" and lay == "frame":
        ytop = fy + fh * 0.86 - 50 * k
        kick_y = None
        kick_col = acc
    else:
        ytop = fy + fh - s - 70 * k
        kick_y = fy + fh - s - 22 * k
        kick_col = acc

    # lowest y the text block may reach (keeps clear of icon / author)
    if th.key == "walter" and lay == "band":
        floor = BLEED + fh * 0.30 + 5 * k + 62 * k + 22 * k
    elif th.key == "walter" and lay == "frame":
        floor = fy + s + 26 * k + 40 * k
    elif th.key == "walter":
        floor = fy + s + 200 * k
    elif lay == "band":
        floor = fy + fh * 0.24 + 6 * k + 140 * k + 50 * k
    elif lay == "split":
        floor = fy + s + 226 * k
    else:
        floor = fy + fh * 0.07 + 12 * k + 190 * k
    tfont = "Poppins" if th.key == "walter" else "Crimson-Italic"
    tsize = (17 if th.key == "walter" else 22) * k

    def block_h(sz):
        h = 0
        if spec.cover_kicker:
            h += sz * 0.32 * 1.25
        h += len(lines) * sz * ((0.86 + 0.12) if caps else (0.92 + 0.22))
        h += 14 * k + 18 * k
        st = ParagraphStyle("p", fontName=tfont, fontSize=tsize, leading=tsize * 1.3)
        h += Paragraph(spec.cover_tagline.replace("&", "&amp;"), st).wrap(tw_, 2000)[1]
        return h
    while ytop - block_h(size) < floor and size > 20:
        size -= 1
    spec._title_size = size

    # brand kicker
    kfont = "Poppins-Medium"
    ksize = 11 * k
    ktxt = th.brand
    if kick_y is not None:
        c.setFillColorRGB(*(light if (lay == "frame" and th.key == "walter") else kick_col))
        c.setFont(kfont, ksize)
        sp = 2.2 * k
        if center:
            tw0 = stringWidth(ktxt, kfont, ksize) + sp * (len(ktxt) - 1)
            t = c.beginText(cx - tw0 / 2, kick_y)
        else:
            t = c.beginText(tx0, kick_y)
        t.setFont(kfont, ksize)
        t.setCharSpace(sp)
        t.textOut(ktxt)
        t.setCharSpace(0)
        c.drawText(t)

    # small kicker line (e.g. "THE")
    y = ytop
    if spec.cover_kicker:
        kk = spec.cover_kicker.upper() if caps else spec.cover_kicker
        ks = size * 0.32
        c.setFillColorRGB(*(acc if lay != "frame" else acc))
        c.setFont(head if caps else "DMSerif-Italic", ks)
        (c.drawCentredString(cx, y - ks, kk) if center else c.drawString(tx0, y - ks, kk))
        y -= ks * 1.25

    c.setFillColorRGB(*fg)
    for ln in lines:
        y -= size * (0.86 if caps else 0.92)
        c.setFont(head, size)
        (c.drawCentredString(cx, y, ln) if center else c.drawString(tx0, y, ln))
        y -= size * (0.12 if caps else 0.22)

    # accent rule
    y -= 14 * k
    c.setFillColorRGB(*acc)
    rw = 110 * k
    c.rect((cx - rw / 2) if center else tx0, y, rw, 5 * k, stroke=0, fill=1)
    y -= 18 * k

    # tagline
    al = 1 if center else 0
    ph = _para(c, spec.cover_tagline, tx0, y, tw_, tfont, tsize, sub, leading=tsize * 1.3, align=al)
    y -= ph

    # icon + author area
    if th.key == "walter" and lay == "band":
        band_top = fy + fh * 0.30 - BLEED * 0 + 0
        ic_r = 62 * k
        icy = BLEED + fh * 0.30 + 5 * k
        c.setFillColorRGB(*acc)
        c.circle(cx, icy, ic_r, stroke=0, fill=1)
        c.setStrokeColorRGB(*light); c.setLineWidth(3 * k)
        c.circle(cx, icy, ic_r - 6 * k, stroke=1, fill=0)
        draw_icon(c, spec.icon, cx, icy, ic_r * 1.1, light, lw=4.2 * k, accent=dark)
        auth_col, auth_y = dark, fy + s + 18 * k
    elif th.key == "walter" and lay == "frame":
        icy = fy + fh * 0.62 + (fh * 0.38 - s) * 0.52
        draw_icon(c, spec.icon, cx, icy, 120 * k, light, lw=4.5 * k, accent=acc)
        auth_col, auth_y = dark, fy + s + 26 * k
    elif th.key == "walter":  # split
        icx, icy = tx1 - 70 * k, fy + s + 120 * k
        c.setFillColorRGB(*acc)
        c.circle(icx, icy, 70 * k, stroke=0, fill=1)
        draw_icon(c, spec.icon, icx, icy, 80 * k, light, lw=4.2 * k, accent=dark)
        auth_col, auth_y = light, fy + s + 20 * k
    elif lay == "band":  # sal band
        icy = fy + fh * 0.24 + 6 * k + 70 * k
        c.setFillColorRGB(*light)
        c.circle(cx, icy, 66 * k, stroke=0, fill=1)
        c.setStrokeColorRGB(*acc); c.setLineWidth(3 * k)
        c.circle(cx, icy, 59 * k, stroke=1, fill=0)
        draw_icon(c, spec.icon, cx, icy, 78 * k, dark, lw=4 * k, accent=acc)
        auth_col, auth_y = None, None
    elif lay == "split":
        icx, icy = tx0 + 70 * k, fy + s + 150 * k
        c.setFillColorRGB(*light)
        c.circle(icx, icy, 66 * k, stroke=0, fill=1)
        draw_icon(c, spec.icon, icx, icy, 80 * k, dark, lw=4 * k, accent=acc)
        auth_col, auth_y = light, fy + s + 22 * k
    else:  # sal frame: icon centered in the space between tagline and author
        icy = max(fy + fh * 0.07 + 12 * k + 120 * k, (y + fy + fh * 0.07 + 12 * k + 40 * k) / 2)
        c.setFillColorRGB(*acc)
        c.circle(cx, icy, 64 * k, stroke=0, fill=1)
        draw_icon(c, spec.icon, cx, icy, 78 * k, light, lw=4 * k, accent=dark)
        auth_col, auth_y = dark, fy + fh * 0.07 + 12 * k + 22 * k

    # author
    if th.key == "walter":
        af, asz = "Poppins-Medium", 15 * k
        atxt = th.author.upper()
    else:
        af, asz = "Crimson-SemiBold", 21 * k
        atxt = th.author
    if auth_col is None:  # sal band: author above gingham, in light
        auth_col, auth_y = light, y - 34 * k
    c.setFillColorRGB(*auth_col)
    c.setFont(af, asz)
    if center or (th.key == "sal" and lay == "split"):
        if th.key == "sal" and lay == "split":
            c.drawString(tx0, auth_y, atxt)
        else:
            c.drawCentredString(cx, auth_y, atxt)
    else:
        c.drawString(tx0, auth_y, atxt)


def draw_back(c, spec, g):
    th = spec.theme
    bx, by, bw, bh = g["back"]
    s = COVER_SAFE
    k = max(bw / (8.5 * inch), 0.72)
    lay = spec.cover_layout
    if lay == "frame":
        fg, sub, acc = th.dark, mix(th.dark, th.light, 0.2), th.accent
    else:
        fg, sub, acc = th.light, mix(th.light, th.dark, 0.15), th.accent
    x0, x1 = bx + s + 10 * k, bx + bw - s - 10 * k
    w = x1 - x0
    rb, rt = getattr(spec, "_reserve", (0, 0))
    y = min(by + bh - s - 20 * k, g["H"] - rt - 28 * k)
    # kicker
    c.setFillColorRGB(*acc)
    c.setFont("Poppins-Medium", 10 * k)
    t = c.beginText(x0, y)
    t.setFont("Poppins-Medium", 10 * k); t.setCharSpace(2 * k); t.textOut(th.brand); t.setCharSpace(0); c.drawText(t)
    y -= 26 * k
    hf = th.head
    hs = (46 if th.head_caps else 34) * k
    head = spec.back_headline.upper() if th.head_caps else spec.back_headline
    ph = _para(c, head, x0, y, w, hf, hs, fg, leading=hs * 1.05)
    y -= ph + 14 * k
    bf = "Poppins-Light" if th.key == "walter" else "Crimson"
    bs = (14.5 if th.key == "walter" else 17.5) * k
    ph = _para(c, spec.back_blurb, x0, y, w, bf, bs, sub, leading=bs * 1.45)
    y -= ph + 16 * k
    c.setFillColorRGB(*acc)
    c.setFont("Poppins-Medium", 10 * k)
    t = c.beginText(x0, y - 10 * k)
    t.setFont("Poppins-Medium", 10 * k); t.setCharSpace(2 * k); t.textOut("INSIDE"); t.setCharSpace(0); c.drawText(t)
    y -= 22 * k
    for b in spec.back_bullets:
        c.setFillColorRGB(*acc)
        c.rect(x0, y - bs * 0.72, 6 * k, 6 * k, stroke=0, fill=1)
        ph = _para(c, b, x0 + 16 * k, y, w - 16 * k, bf, bs, fg, leading=bs * 1.35)
        y -= ph + 5 * k
    rb, rt = getattr(spec, "_reserve", (0, 0))
    af = "Poppins-Medium" if th.key == "walter" else "Crimson-SemiBold"
    asz = (11 if th.key == "walter" else 14) * k
    atxt = th.author.upper() if th.key == "walter" else th.author
    c.setFillColorRGB(*fg)
    c.setFont(af, asz)
    if lay == "band":
        y -= 14 * k
        c.drawString(x0, y - asz, atxt)
        y -= asz + 4
        floor = rb + 12 * k
    else:
        c.drawString(x0, max(by + s + 4, rb + 14 * k), atxt)
        floor = max(rb, g["barcode"][1] + g["barcode"][3]) + 14 * k
    spec._back_text_bottom = y
    if y < floor:
        raise ValueError(f"back cover text overflows ({y:.0f} < {floor:.0f})")
    # barcode area: solid white, nothing else inside
    gx, gy, gw, gh = g["barcode"]
    c.setFillColorRGB(1, 1, 1)
    c.rect(gx, gy, gw, gh, stroke=0, fill=1)


def draw_spine(c, spec, g, mono=False):
    th = spec.theme
    sx, sy, sw, sh = g["spine"]
    if spec.pages < SPINE_TEXT_MIN_PAGES:
        return None
    avail = sw - 2 * SPINE_CLEARANCE
    font = th.head if th.head_caps else "DMSerif"
    title = spec.spine_title.upper()
    author = th.author.upper()
    afont = "Bebas" if th.key == "walter" else "Crimson-SemiBold"
    # size so the glyph height (cap height; author has no descenders in caps) fits the available width
    size = 30
    while size > MIN_FONT_PT and cap_height(font, size) > avail * 0.92:
        size -= 0.25
    if size < MIN_FONT_PT:
        return None
    asz = size
    while asz > MIN_FONT_PT and cap_height(afont, asz) > avail * 0.92:
        asz -= 0.25
    fg = th.dark if spec.cover_layout == "frame" else th.light
    c.saveState()
    cx = sx + sw / 2
    c.translate(cx, sy + sh)
    c.rotate(-90)  # text reads top to bottom
    # baseline offset so caps are centered on spine axis
    off = -cap_height(font, size) / 2
    c.setFillColorRGB(*((0, 0, 0) if mono else fg))
    c.setFont(font, size)
    rb, rt = getattr(spec, "_reserve", (0, 0))
    top_pad = max(0.6 * inch, rt - BLEED + 0.3 * inch)
    bot_pad = max(0.6 * inch, rb - BLEED + 0.3 * inch)
    c.drawString(top_pad, off, title)
    c.setFillColorRGB(*((0, 0, 0) if mono else th.accent))
    c.setFont(afont, asz)
    c.drawRightString(sh - bot_pad, -cap_height(afont, asz) / 2, author)
    if stringWidth(title, font, size) + stringWidth(author, afont, asz) + 0.4 * inch > sh - top_pad - bot_pad:
        raise ValueError("spine text too long")
    c.restoreState()
    return dict(size=size, asz=asz, cap=cap_height(font, size), avail=avail)


def build_cover(spec, out_path):
    register_fonts()
    g = cover_geometry(spec)
    c = canvas.Canvas(out_path, pagesize=(g["W"], g["H"]), initialFontName="Poppins", initialFontSize=10)
    c.setTitle(spec.title + " - cover")
    c.setAuthor(spec.theme.author)
    c.setCreator("kdpgen")
    th = spec.theme
    bg = th.light if spec.cover_layout == "frame" else th.dark
    c.setFillColorRGB(*bg)
    c.rect(0, 0, g["W"], g["H"], stroke=0, fill=1)
    draw_front(c, spec, g)
    draw_back(c, spec, g)
    sp = draw_spine(c, spec, g)
    c.showPage()
    c.save()
    g["spine_text"] = sp
    return g
