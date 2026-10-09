"""Interior PDF builder: front matter (from markup) + fill-in pages, mirrored margins."""
import re
import yaml
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer,
                                PageBreak, Table, TableStyle, Flowable, KeepTogether)
from reportlab.lib import colors
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

from .core import register_fonts, INK, MID, LINE, SOFT, TINT, gutter_min
from . import forms as F
from .icons import draw_icon

# design margins (inches) - all above KDP minimums (inside 0.375 for <=150 pp, others 0.25)
M_INSIDE, M_OUTSIDE, M_TOP, M_BOTTOM = 0.5, 0.4, 0.45, 0.45
FOOTER = 16  # pt reserved inside the live area for the page number

GRAY = lambda g: colors.Color(g, g, g)


def margins_for(pages):
    assert M_INSIDE >= gutter_min(pages)
    return M_INSIDE * inch, M_OUTSIDE * inch, M_TOP * inch, M_BOTTOM * inch


# ------------------------------------------------------------------ content parsing
def load_content(path):
    txt = open(path, encoding="utf-8").read()
    m = re.match(r"---listing\n(.*?)\n---\n(.*)", txt, re.S)
    listing = yaml.safe_load(m.group(1))
    return listing, m.group(2)


def _inline(s):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", s)
    return s


COMPACT = [(1.0, 0.0, 1.0), (0.95, 0.0, 0.6), (0.92, -0.4, 0.45), (0.88, -0.8, 0.3)]


def styles(th, level=0):
    w = th.key == "walter"
    lf, ds, sf = COMPACT[level]
    bs = th.body_size + ds
    body = ParagraphStyle("body", fontName=th.body, fontSize=bs,
                          leading=bs * (1.52 if w else 1.3) * lf, textColor=GRAY(INK),
                          spaceAfter=(6 if w else 5) * sf)
    return {
        "body": body,
        "h1": ParagraphStyle("h1", fontName=th.head, fontSize=32 if w else 26, leading=34 if w else 30,
                             textColor=GRAY(INK), spaceAfter=2, keepWithNext=1),
        "h2": ParagraphStyle("h2", fontName="Poppins-Medium" if w else th.head, fontSize=11 if w else 15,
                             leading=15 if w else 18, textColor=GRAY(INK), spaceBefore=9 * sf, spaceAfter=4 * sf,
                             keepWithNext=1),
        "h3": ParagraphStyle("h3", fontName="Poppins-Medium" if w else "Crimson-SemiBold",
                             fontSize=9.2 if w else 12.2, leading=13 if w else 15, textColor=GRAY(0.25),
                             spaceBefore=6, spaceAfter=2, keepWithNext=1),
        "bullet": ParagraphStyle("bullet", parent=body, leftIndent=13, bulletIndent=2, spaceAfter=2.5,
                                 bulletFontName=th.body),
        "check": ParagraphStyle("check", parent=body, spaceAfter=0),
        "tip": ParagraphStyle("tip", parent=body, fontName=th.italic, spaceAfter=0),
        "cell": ParagraphStyle("cell", parent=body, fontSize=th.body_size - (1 if w else 1.4),
                               leading=(th.body_size - 1) * 1.3, spaceAfter=0),
        "cellh": ParagraphStyle("cellh", parent=body, fontName=th.label, fontSize=7.8 if w else 10,
                                leading=10 if w else 12, spaceAfter=0),
    }


class Rule(Flowable):
    def __init__(self, th, width=None):
        super().__init__()
        self.th = th

    def wrap(self, aw, ah):
        self.aw = aw
        return aw, 12

    def draw(self):
        c = self.canv
        if self.th.key == "walter":
            c.setFillGray(INK)
            c.rect(0, 6, 46, 3.2, stroke=0, fill=1)
            F.hline(c, 50, self.aw, 7.6, gray=SOFT, w=0.6)
        else:
            F.hline(c, 0, self.aw, 7, gray=MID, w=0.6)
            F.hline(c, 0, self.aw, 4.5, gray=SOFT, w=0.4)


class CheckItem(Flowable):
    def __init__(self, text, style):
        super().__init__()
        self.p = Paragraph(text, style)
        self.style = style

    def wrap(self, aw, ah):
        w, h = self.p.wrap(aw - 16, ah)
        self.h = h + 3
        return aw, self.h

    def draw(self):
        lead = self.style.leading
        F.checkbox(self.canv, 1, self.h - lead + (lead - 7.5) / 2 - 1, 7.5)
        self.p.drawOn(self.canv, 16, 3)


class H1(Paragraph):
    """Heading level 1 - recorded for the table of contents."""
    pass


class Mark(Flowable):
    """Zero-size marker for a fill-in section start (for the contents page)."""
    def __init__(self, name):
        super().__init__()
        self.name = name

    def wrap(self, aw, ah):
        return 0, 0

    def draw(self):
        pass


def parse_markup(body, th, levels=None):
    levels = levels or {}
    sec = -1
    st = styles(th)
    out = []
    lines = body.strip("\n").split("\n")
    i = 0
    para = []

    def flush():
        if para:
            out.append(Paragraph(_inline(" ".join(para)), st["body"]))
            para.clear()

    while i < len(lines):
        ln = lines[i].rstrip()
        if not ln.strip():
            flush(); i += 1; continue
        if ln.strip() == "::page":
            flush()
            if out and not isinstance(out[-1], PageBreak):
                out.append(PageBreak())
            i += 1; continue
        if ln.startswith("# "):
            flush()
            t = ln[2:].strip()
            sec += 1
            st = styles(th, levels.get(sec, 0))
            h = H1(_inline(t.upper() if th.head_caps else t), st["h1"])
            h.toc_title = t
            out += [h, Rule(th), Spacer(1, 4)]
        elif ln.startswith("## "):
            flush(); out.append(Paragraph(_inline(ln[3:]), st["h2"]))
        elif ln.startswith("### "):
            flush(); out.append(Paragraph(_inline(ln[4:]), st["h3"]))
        elif ln.startswith("[ ] "):
            flush(); out.append(CheckItem(_inline(ln[4:]), st["check"]))
        elif ln.startswith("- "):
            flush(); out.append(Paragraph(_inline(ln[2:]), st["bullet"], bulletText="•"))
        elif ln.startswith("> "):
            flush()
            p = Paragraph(_inline(ln[2:]), st["tip"])
            t = Table([[p]], colWidths=["100%"])
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), th.body),
                ("BACKGROUND", (0, 0), (-1, -1), GRAY(0.93)),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, GRAY(MID)),
                ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            out += [Spacer(1, 3), t, Spacer(1, 7)]
        elif ln.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", x) for x in cells):
                    rows.append(cells)
                i += 1
            data = [[Paragraph(_inline(x), st["cellh" if r == 0 else "cell"]) for x in row] for r, row in enumerate(rows)]
            t = Table(data, repeatRows=1, hAlign="LEFT", colWidths=None)
            t._argW = [None] * len(rows[0])
            t.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), th.body),
                ("BACKGROUND", (0, 0), (-1, 0), GRAY(TINT)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, GRAY(MID)),
                ("LINEBELOW", (0, 1), (-1, -1), 0.4, GRAY(SOFT)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            out += [Spacer(1, 3), FullWidthTable(t, len(rows[0])), Spacer(1, 8)]
            continue
        else:
            para.append(ln.strip())
        i += 1
    flush()
    # drop spacers that would otherwise spill onto an otherwise empty page
    clean = []
    for i, f in enumerate(out):
        nxt = out[i + 1] if i + 1 < len(out) else None
        if isinstance(f, Spacer) and (nxt is None or isinstance(nxt, PageBreak)):
            continue
        clean.append(f)
    return clean


class FullWidthTable(Flowable):
    """Wrap a Table so its columns share the frame width evenly."""
    def __init__(self, t, n):
        super().__init__()
        self.t, self.n = t, n

    def wrap(self, aw, ah):
        self.t._argW = [aw / self.n] * self.n
        self.t._colWidths = self.t._argW
        return self.t.wrap(aw, ah)

    def split(self, aw, ah):
        self.t._argW = [aw / self.n] * self.n
        return self.t.split(aw, ah)

    def drawOn(self, canv, x, y, _sW=0):
        self.t.drawOn(canv, x, y, _sW)


class FormPage(Flowable):
    """A full-page fill-in form drawn by a callback fn(c, th, box)."""
    def __init__(self, fn, th):
        super().__init__()
        self.fn, self.th = fn, th

    def wrap(self, aw, ah):
        self.aw, self.ah = aw, ah - 1
        return aw, self.ah

    def draw(self):
        self.fn(self.canv, self.th, (0, 0, self.aw, self.ah))


# ------------------------------------------------------------------ special pages
def title_page(spec):
    th = spec.theme

    def fn(c, th_, box):
        x, y, w, h = box
        cx = x + w / 2
        c.setFillGray(MID)
        F.label(c, th, cx, y + h - 40, th.brand, align="center", size=8)
        draw_icon(c, spec.icon, cx, y + h * 0.70, min(w, h) * 0.22, (0.25, 0.25, 0.25), lw=2.2,
                  accent=(0.45, 0.45, 0.45))
        size = 40 if th.key == "walter" else 32
        lines = spec.cover_title
        maxw = w - 20
        for ln in lines:
            t = ln.upper() if th.head_caps else ln
            size = min(size, F.fit(t, th.head, size, maxw))
        yy = y + h * 0.52
        c.setFillGray(INK)
        for ln in lines:
            t = ln.upper() if th.head_caps else ln
            c.setFont(th.head, size)
            c.drawCentredString(cx, yy, t)
            yy -= size * 1.05
        yy -= 6
        # subtitle wrapped
        sub_style = ParagraphStyle("s", fontName=th.italic, fontSize=10.5 if th.key == "sal" else 9,
                                   leading=14 if th.key == "sal" else 13.5, alignment=TA_CENTER,
                                   textColor=GRAY(MID))
        p = Paragraph(_inline(spec.subtitle), sub_style)
        pw, ph = p.wrap(w * 0.8, 200)
        p.drawOn(c, x + w * 0.1, yy - ph)
        yy -= ph + 26
        c.setFillGray(INK)
        c.setFont(th.label if th.key == "walter" else "Crimson-SemiBold", 11 if th.key == "walter" else 13)
        c.drawCentredString(cx, yy, th.author.upper() if th.key == "walter" else th.author)
        # belongs to
        bx = (x + w * 0.12, y + 30, w * 0.76, 70)
        F.panel(c, th, bx, title="This book belongs to")
        F.hline(c, bx[0] + 12, bx[0] + bx[2] - 12, bx[1] + 22, gray=LINE)
    return fn


def copyright_page(spec, year=2026):
    th = spec.theme
    st = styles(th)
    small = ParagraphStyle("sm", parent=st["body"], fontSize=8.2 if th.key == "walter" else 10,
                           leading=12 if th.key == "walter" else 13, spaceAfter=7, textColor=GRAY(0.25))
    disc = getattr(spec, "disclaimer", "")
    paras = [
        f"<b>{_inline(spec.title)}</b><br/>{_inline(spec.subtitle)}",
        f"Copyright © {year} {th.author}. All rights reserved.",
        "No part of this book may be reproduced, stored or transmitted in any form without written permission "
        "from the publisher, except that the owner of this copy may fill in its pages and photocopy blank "
        "pages for their own personal use.",
        *([disc] if disc else []),
        f"{th.author} is a pen name.",
        "Fonts: Bebas Neue, Poppins, DM Serif Display and Crimson Text, used under the SIL Open Font License.",
    ]

    def fn(c, th_, box):
        x, y, w, h = box
        flows = [Paragraph(p, small) for p in paras]
        tot = 0
        sizes = []
        for f in flows:
            fw, fh = f.wrap(w * 0.86, h)
            sizes.append(fh)
            tot += fh + 7
        yy = y + 10 + tot
        for f, fh in zip(flows, sizes):
            yy -= fh
            f.drawOn(c, x, yy)
            yy -= 7
    return fn


def contents_page(spec, toc):
    th = spec.theme

    def fn(c, th_, box):
        rem = F.header(c, th, box, "Contents")
        x, y, w, h = rem
        yy = y + h - 16
        row = min(22, (h - 10) / max(len(toc), 1))
        font = "Poppins" if th.key == "walter" else "Crimson"
        size = 9.5 if th.key == "walter" else 12
        for kind, name, pg in toc:
            if kind == "fill" and toc and toc[0] != (kind, name, pg):
                pass
            c.setFillGray(INK if kind == "guide" else 0.2)
            f = font if kind == "guide" else ("Poppins-Medium" if th.key == "walter" else "Crimson-SemiBold")
            c.setFont(f, size)
            c.drawString(x + 4, yy, name)
            c.drawRightString(x + w - 4, yy, str(pg))
            tw = stringWidth(name, f, size)
            c.setFillGray(SOFT)
            dx = x + 4 + tw + 6
            while dx < x + w - 4 - stringWidth(str(pg), f, size) - 6:
                c.circle(dx, yy + 2.2, 0.5, stroke=0, fill=1)
                dx += 4
            yy -= row
    return fn


# ------------------------------------------------------------------ doc template
class EmbeddedCanvas(Canvas):
    """Canvas whose initial font is an embedded TTF (avoids an unembedded Helvetica reference)."""
    def __init__(self, *a, **k):
        k["initialFontName"] = "Poppins"
        k["initialFontSize"] = 10
        k["initialLeading"] = 12
        super().__init__(*a, **k)


class BookDoc(BaseDocTemplate):
    def __init__(self, path, spec, pages_hint):
        self.spec = spec
        w, h = spec.trim[0] * inch, spec.trim[1] * inch
        mi, mo, mt, mb = margins_for(pages_hint or 300)
        super().__init__(path, pagesize=(w, h), leftMargin=0, rightMargin=0, topMargin=0, bottomMargin=0,
                         title=spec.title, author=spec.theme.author, subject=spec.subtitle, creator="kdpgen",
                         producer="kdpgen")
        fw, fh = w - mi - mo, h - mt - mb - FOOTER
        odd = Frame(mi, mb + FOOTER, fw, fh, id="odd", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        even = Frame(mo, mb + FOOTER, fw, fh, id="even", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.box = dict(odd=(mi, mb, fw, h - mt - mb), even=(mo, mb, fw, h - mt - mb))
        self.addPageTemplates([
            PageTemplate("odd", [odd], onPage=self._footer),
            PageTemplate("even", [even], onPage=self._footer),
        ])
        self.toc = []
        self.fill = {}

    def handle_pageBegin(self):
        # recto (odd) pages have the gutter on the left, verso (even) on the right
        self.pageTemplate = self.pageTemplates[0 if (self.page + 1) % 2 else 1]
        super().handle_pageBegin()

    def _footer(self, c, doc):
        n = c.getPageNumber()
        if n == 1:
            return
        th = self.spec.theme
        x, y, w, h = self.box["odd" if n % 2 else "even"]
        c.saveState()
        c.setFillGray(MID)
        if th.key == "walter":
            c.setFont("Poppins-Medium", 7.5)
        else:
            c.setFont("Crimson-Italic", 9.5)
        if n % 2:
            c.drawRightString(x + w, y + 4, str(n))
        else:
            c.drawString(x, y + 4, str(n))
        c.restoreState()

    def afterFlowable(self, f):
        fr = getattr(self, "frame", None)
        if fr is not None and not isinstance(f, (PageBreak, Mark)):
            self.fill[self.page] = (fr._y2 - fr._y) / (fr._y2 - fr._y1)
        if isinstance(f, H1):
            self.toc.append(("guide", f.toc_title, self.page))
        elif isinstance(f, Mark):
            self.toc.append(("fill", f.name, self.page))


def build_story(spec, guide_flows, toc, pad):
    th = spec.theme
    story = [FormPage(title_page(spec), th), PageBreak(),
             FormPage(copyright_page(spec), th), PageBreak(),
             FormPage(contents_page(spec, toc), th), PageBreak()]
    story += guide_flows
    sections = list(spec.sections)
    if pad:
        from .pages import notes_page
        if sections and sections[-1][0] == "Notes":
            sections[-1] = ("Notes", sections[-1][1] + [notes_page] * pad)
        else:
            sections.append(("Notes", [notes_page] * pad))
    for name, pages in sections:
        if not pages:
            continue
        if not isinstance(story[-1], PageBreak):
            story.append(PageBreak())
        story.append(Mark(name))
        for i, pf in enumerate(pages):
            story.append(FormPage(pf, th))
            story.append(PageBreak())
    while isinstance(story[-1], PageBreak):
        story.pop()
    return story


def build_interior(spec, out_path):
    register_fonts()
    listing, body = load_content(spec.content_file)

    levels = {}

    def run(toc, pad, path):
        flows = parse_markup(body, spec.theme, levels)
        doc = BookDoc(path, spec, spec.pages)
        doc.build(build_story(spec, flows, toc, pad), canvasmaker=EmbeddedCanvas)
        return doc

    # pass 1: count pages and collect toc
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".pdf")
    # tighten guide sections whose last page would hold only a few lines
    for _ in range(4):
        d0 = run([("guide", "x", 0)], 0, tmp)
        starts = [p for k, n, p in d0.toc if k == "guide"]
        first_fill = min([p for k, n, p in d0.toc if k == "fill"] or [d0.page + 1])
        changed = False
        for i, st_ in enumerate(starts):
            end = (starts[i + 1] if i + 1 < len(starts) else first_fill) - 1
            if end > st_ and d0.fill.get(end, 1) < 0.30 and levels.get(i, 0) < len(COMPACT) - 1:
                levels[i] = levels.get(i, 0) + 1
                changed = True
        if not changed:
            break
    spec._compaction = dict(levels)
    for _ in range(4):
        d1 = run([("guide", "x", 0)], 0, tmp)
        n1 = d1.page
        fixed = False
        for name in getattr(spec, "align_even", []):
            pg = next(p for k, nm, p in d1.toc if nm == name)
            if pg % 2 == 1:
                idx = [s_[0] for s_ in spec.sections].index(name)
                prev = spec.sections[idx - 1]
                spec.sections[idx - 1] = (prev[0], prev[1] + [spec.align_filler])
                fixed = True
        if not fixed:
            break
    if spec.pages is None:
        n = n1 + 2
        n += n % 2
        if n == 110:
            n = 112
        spec.pages = n
    pad = spec.pages - n1
    if pad < 0:
        raise ValueError(f"{spec.slug}: content is {n1} pages, target {spec.pages}")
    d2 = run(d1.toc, pad, tmp)
    d3 = run(d2.toc, pad, out_path)
    os.remove(tmp)
    assert d3.page == spec.pages, (d3.page, spec.pages)
    assert d3.page % 2 == 0
    return listing, d3.toc, n1
