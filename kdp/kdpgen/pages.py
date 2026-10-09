"""Generic fill-in page factories. Each returns fn(c, th, box)."""
from . import forms as F
from .core import INK, MID, LINE, SOFT, TINT
from .icons import draw_icon


def notes_page(c, th, box):
    rem = F.header(c, th, box, "Notes")
    F.lines(c, th, rem, spacing=22)


def lined(title, spacing=22, right=None, sub=None):
    def fn(c, th, box):
        rem = F.header(c, th, box, title, right=right, sub=sub)
        F.lines(c, th, rem, spacing=spacing)
    return fn


def dots(title, right=None, step=14):
    def fn(c, th, box):
        rem = F.header(c, th, box, title, right=right)
        F.dotgrid(c, rem, step=step)
    return fn


def grid(title, right=None, step=14, sub=None):
    def fn(c, th, box):
        rem = F.header(c, th, box, title, right=right, sub=sub)
        F.gridpaper(c, rem, step=step)
    return fn


def log(title, cols, row_h=22, right=None, sub=None, numbered=False, top_fields=None, rows=None):
    def fn(c, th, box):
        rem = F.header(c, th, box, title, right=right, sub=sub)
        if top_fields:
            rem = F.fields(c, th, rem, top_fields, row_h=22)
            x, y, w, h = rem
            rem = (x, y, w, h - 8)
        F.table(c, th, rem, cols, row_h=row_h, numbered=numbered, rows=rows)
    return fn


def cards(title, field_rows, n, notes_label="Notes", notes_spacing=18, right=None, row_h=23, sub=None):
    """n stacked record panels, each with label/line fields and a notes area."""
    def fn(c, th, box):
        rem = F.header(c, th, box, title, right=right, sub=sub)
        for b in F.vsplit(rem, ["1f"] * n, gap=10):
            inner = F.inset(b, 0)
            F.panel(c, th, inner)
            x, y, w, h = F.inset(inner, 9)
            r = F.fields(c, th, (x, y, w, h), field_rows, row_h=row_h)
            rx, ry, rw, rh = r
            if notes_label is not None and rh > notes_spacing + 8:
                F.label(c, th, rx, ry + rh - 12, notes_label)
                F.lines(c, th, (rx, ry, rw, rh - 12), spacing=notes_spacing, first=notes_spacing - 2)
    return fn


def contacts(title="Contacts", n=5, extra=("Notes",)):
    rows = [[("Name", 3), ("Company", 3)], [("Service / trade", 3), ("Phone", 2)],
            [("Email", 3), ("License / account #", 2)]]
    return cards(title, rows, n, notes_label=extra[0] if extra else None, row_h=22)


def checklist_page(title, items, cols=1, row_h=19, right=None, sub=None):
    def fn(c, th, box):
        rem = F.header(c, th, box, title, right=right, sub=sub)
        F.checklist(c, th, rem, items, cols=cols, row_h=row_h)
    return fn


def checkgrid_page(title, items, colheads, row_h=19, right=None, sub=None, item_frac=0.6):
    def fn(c, th, box):
        rem = F.header(c, th, box, title, right=right, sub=sub)
        F.checkgrid(c, th, rem, items, colheads, row_h=row_h, item_frac=item_frac)
    return fn


def divider(title, sub=None, icon=None):
    def fn(c, th, box):
        x, y, w, h = box
        cx = x + w / 2
        if icon:
            draw_icon(c, icon, cx, y + h * 0.62, min(w, h) * 0.2, (0.3, 0.3, 0.3), lw=2, accent=(0.5, 0.5, 0.5))
        c.setFillGray(INK)
        t = title.upper() if th.head_caps else title
        size = F.fit(t, th.head, 46 if th.head_caps else 38, w - 30)
        c.setFont(th.head, size)
        c.drawCentredString(cx, y + h * 0.45, t)
        F.hline(c, cx - 60, cx + 60, y + h * 0.45 - 16, gray=MID, w=0.8)
        if sub:
            c.setFont(th.italic, 11 if th.key == "sal" else 9)
            c.setFillGray(MID)
            c.drawCentredString(cx, y + h * 0.45 - 36, sub)
    return fn


def two_up(fn_top, fn_bottom, gap=14, title=None):
    """Place two half-page forms on one page (optional page header)."""
    def fn(c, th, box):
        if title:
            box = F.header(c, th, box, title)
        a, b = F.vsplit(box, ["1f", "1f"], gap=gap)
        fn_top(c, th, a)
        fn_bottom(c, th, b)
    return fn
