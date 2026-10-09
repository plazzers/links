"""Validate interior + cover PDFs against KDP rules (see KDP/RULES.md)."""
import os
import subprocess
import tempfile
import pdfplumber
from PIL import Image
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from .core import gutter_min, KDP_OUTSIDE_MIN, MIN_FONT_PT, BLEED, SPINE_CLEARANCE, SPINE_TEXT_MIN_PAGES
from .interior import M_INSIDE, M_OUTSIDE, M_TOP, M_BOTTOM
from .cover import cover_geometry, draw_spine

TOL = 0.6  # pt, allows for stroke half-widths


def pdffonts(path):
    out = subprocess.run(["pdffonts", path], capture_output=True, text=True).stdout.splitlines()[2:]
    res = []
    for ln in out:
        parts = ln.split()
        # columns: name type [encoding] emb sub uni object ID
        emb = parts[-5]
        res.append((parts[0], emb))
    return res


def _objects(page):
    H = page.height
    for kind in ("chars", "rects", "lines", "curves"):
        for o in getattr(page, kind):
            yield kind, o["x0"], H - o["bottom"], o["x1"], H - o["top"], o


def validate_interior(path, spec):
    errs, info = [], {}
    W, H = spec.trim[0] * inch, spec.trim[1] * inch
    with pdfplumber.open(path) as pdf:
        n = len(pdf.pages)
        info["pages"] = n
        if n != spec.pages:
            errs.append(f"page count {n} != spec {spec.pages}")
        if n % 2:
            errs.append("odd page count")
        if n < 24:
            errs.append("fewer than 24 pages")
        gmin = gutter_min(n) * inch
        omin = KDP_OUTSIDE_MIN * inch
        min_clear = {"inside": 99, "outside": 99, "top": 99, "bottom": 99}
        min_font = 99
        design_viol = 0
        blank = []
        for i, p in enumerate(pdf.pages):
            pn = i + 1
            txt = "".join(c["text"] for c in p.chars).strip()
            if txt in ("", str(pn)) and not p.rects and not p.lines and not p.curves:
                blank.append(pn)
            if abs(p.width - W) > 0.05 or abs(p.height - H) > 0.05:
                errs.append(f"p{pn}: size {p.width:.2f}x{p.height:.2f} != {W:.2f}x{H:.2f}")
            recto = pn % 2 == 1
            for kind, x0, y0, x1, y1, o in _objects(p):
                if kind == "chars" and not o["text"].strip():
                    continue
                inside = x0 if recto else W - x1
                outside = W - x1 if recto else x0
                c = {"inside": inside, "outside": outside, "top": H - y1, "bottom": y0}
                for k_, v in c.items():
                    min_clear[k_] = min(min_clear[k_], v)
                if (inside < M_INSIDE * inch - TOL or outside < M_OUTSIDE * inch - TOL or
                        H - y1 < M_TOP * inch - TOL or y0 < M_BOTTOM * inch - TOL):
                    design_viol += 1
                    if design_viol <= 3:
                        errs.append(f"p{pn}: {kind} outside design margins ({x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f})")
                if kind == "chars":
                    min_font = min(min_font, o["size"])
        if blank:
            errs.append(f"blank pages: {blank}")
        info["min_clearance_in"] = {k: round(v / inch, 3) for k, v in min_clear.items()}
        info["min_font_pt"] = round(min_font, 2)
        if min_clear["inside"] < gmin - TOL:
            errs.append(f"inside margin {min_clear['inside'] / inch:.3f}in < KDP {gmin / inch}")
        for k in ("outside", "top", "bottom"):
            if min_clear[k] < omin - TOL:
                errs.append(f"{k} margin {min_clear[k] / inch:.3f}in < KDP 0.25")
        if min_font < MIN_FONT_PT - 0.01:
            errs.append(f"font size {min_font} < 7pt")
    fonts = pdffonts(path)
    bad = [f for f, e in fonts if e != "yes"]
    if bad:
        errs.append(f"fonts not embedded: {bad}")
    info["fonts"] = sorted({f.split('+')[-1] for f, _ in fonts})
    return errs, info


def _render(path, dpi):
    d = tempfile.mkdtemp()
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", path, os.path.join(d, "r")], check=True)
    return Image.open(os.path.join(d, "r.png")).convert("RGB")


def validate_cover(path, spec):
    errs, info = [], {}
    g = cover_geometry(spec)
    with pdfplumber.open(path) as pdf:
        if len(pdf.pages) != 1:
            errs.append("cover must be one page")
        p = pdf.pages[0]
        info["size_in"] = (round(p.width / inch, 4), round(p.height / inch, 4))
        info["expected_in"] = (round(g["W"] / inch, 4), round(g["H"] / inch, 4))
        info["spine_in"] = round(g["sw"] / inch, 4)
        if abs(p.width - g["W"]) > 0.05 or abs(p.height - g["H"]) > 0.05:
            errs.append(f"cover size {info['size_in']} != formula {info['expected_in']}")
        sx0, sx1 = g["spine"][0], g["spine"][0] + g["sw"]
        min_safe = 99
        H = p.height
        for ch in p.chars:
            if not ch["text"].strip():
                continue
            x0, x1, y0, y1 = ch["x0"], ch["x1"], H - ch["bottom"], H - ch["top"]
            cx = (x0 + x1) / 2
            if sx0 <= cx <= sx1:
                continue  # spine text: size and clearance checked below
            if ch["size"] < MIN_FONT_PT - 0.01:
                errs.append(f"cover text below 7pt: {ch['text']} {ch['size']:.2f}")
            panel = g["back"] if cx < sx0 else g["front"]
            px, py, pw, ph = panel
            d = min(x0 - px, px + pw - x1, y0 - py, py + ph - y1)
            min_safe = min(min_safe, d)
            if d < 0.25 * inch:
                errs.append(f"cover text '{ch['text']}' only {d / inch:.3f}in from trim/spine")
            bx, by, bw, bh = g["barcode"]
            if x1 > bx and x0 < bx + bw and y1 > by and y0 < by + bh:
                errs.append(f"text in barcode area: {ch['text']}")
        info["min_text_to_trim_in"] = round(min_safe / inch, 3)
    # barcode zone must be solid white
    dpi = 100
    img = _render(path, dpi)
    s = dpi / 72
    bx, by, bw, bh = g["barcode"]
    Hpx = img.height
    box = (int(bx * s) + 1, int(Hpx - (by + bh) * s) + 1, int((bx + bw) * s) - 1, int(Hpx - by * s) - 1)
    crop = img.crop(box)
    if min(min(px) for px in crop.getdata()) < 250:
        errs.append("barcode area is not clear white")
    # spine text clearance: render the spine text alone and look for ink in the clearance strips
    if spec.pages >= SPINE_TEXT_MIN_PAGES:
        tmp = tempfile.mktemp(suffix=".pdf")
        c = canvas.Canvas(tmp, pagesize=(g["W"], g["H"]), initialFontName="Poppins")
        st = draw_spine(c, spec, g, mono=True)
        c.showPage(); c.save()
        info["spine_text"] = st and {k: round(v, 2) for k, v in st.items()}
        if st and min(st["size"], st["asz"]) < MIN_FONT_PT:
            errs.append("spine text below 7pt")
        if st:
            import numpy as np
            dpi2 = 600
            s2 = dpi2 / 72
            gx0, gx1 = g["spine"][0], g["spine"][0] + g["sw"]
            cx0 = int((gx0 - 0.2 * inch) * s2)
            cw = int((g["sw"] + 0.4 * inch) * s2)
            d = tempfile.mkdtemp()
            subprocess.run(["pdftoppm", "-r", str(dpi2), "-gray", "-x", str(cx0), "-y", "0", "-W", str(cw), "-H",
                            str(int(g["H"] * s2)), "-png", "-singlefile", tmp, os.path.join(d, "s")], check=True)
            a = np.asarray(Image.open(os.path.join(d, "s.png")).convert("L"))
            cols = np.where((a < 200).any(axis=0))[0]
            if len(cols):
                lo, hi = (cx0 + cols.min()) / s2, (cx0 + cols.max() + 1) / s2
                info["spine_ink_clearance_in"] = (round((lo - gx0) / inch, 4), round((gx1 - hi) / inch, 4))
                if lo < gx0 + SPINE_CLEARANCE - 0.5 or hi > gx1 - SPINE_CLEARANCE + 0.5:
                    errs.append(f"spine text closer than 0.0625in to spine edge: {info['spine_ink_clearance_in']}")
        os.remove(tmp)
    fonts = pdffonts(path)
    bad = [f for f, e in fonts if e != "yes"]
    if bad:
        errs.append(f"cover fonts not embedded: {bad}")
    return errs, info
