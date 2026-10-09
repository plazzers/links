"""Core KDP constants, fonts, themes and cost math.

All KDP numbers here come from KDP help pages (see KDP/RULES.md).
"""
import os
from dataclasses import dataclass, field
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import inch

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(os.path.dirname(HERE), "fonts")

# ---- KDP rules -----------------------------------------------------------
BLEED = 0.125 * inch
SPINE_PER_PAGE = {"white": 0.002252, "cream": 0.0025}   # inches per page
SPINE_TEXT_MIN_PAGES = 80          # KDP: spine text only for books with MORE than 79 pages
SPINE_CLEARANCE = 0.0625 * inch    # min distance text <-> spine edge
COVER_SAFE = 0.375 * inch          # our safe zone (KDP minimum 0.25")
BARCODE_W, BARCODE_H = 2.0 * inch, 1.2 * inch
BARCODE_OFFSET = 0.25 * inch       # from spine and bottom trim
MIN_FONT_PT = 7.0


def gutter_min(pages):
    """KDP minimum inside margin (inches) for a page count."""
    for limit, m in ((150, .375), (300, .5), (500, .625), (700, .75), (828, .875)):
        if pages <= limit:
            return m
    raise ValueError("too many pages")


KDP_OUTSIDE_MIN = 0.25  # inches, no bleed (top/bottom/outside)


def is_large_trim(w_in, h_in):
    # KDP: large trim = wider than 6.12" or taller than 9"
    return w_in > 6.12 or h_in > 9.0


def print_cost(pages, w_in, h_in):
    """Amazon.com black-ink paperback printing cost (USD) and the formula text."""
    large = is_large_trim(w_in, h_in)
    if pages == 110:
        raise ValueError("110 pages sits on KDP's ambiguous boundary - avoid")
    if pages < 110:
        cost = 2.84 if large else 2.30
        txt = f"{pages} pages is in the 24-110 page band: flat ${cost:.2f} ({'large' if large else 'regular'} trim)"
    else:
        per = 0.017 if large else 0.012
        cost = 1.00 + pages * per
        txt = f"$1.00 + {pages} x ${per:.3f} = ${cost:.2f} ({'large' if large else 'regular'} trim, 110-828 pages)"
    return round(cost, 2), txt


def royalty(price, cost):
    rate = 0.60 if price >= 9.99 else 0.50
    return round(rate * price - cost, 2), rate


def spine_width(pages, paper="white"):
    return pages * SPINE_PER_PAGE[paper] * inch


# ---- fonts -----------------------------------------------------------------
_FONTS = {
    "Bebas": "BebasNeue-Regular.ttf",
    "Poppins": "Poppins-Regular.ttf",
    "Poppins-Light": "Poppins-Light.ttf",
    "Poppins-Medium": "Poppins-Medium.ttf",
    "Poppins-Bold": "Poppins-Bold.ttf",
    "Poppins-Italic": "Poppins-Italic.ttf",
    "DMSerif": "DMSerifDisplay-Regular.ttf",
    "DMSerif-Italic": "DMSerifDisplay-Italic.ttf",
    "Crimson": "CrimsonText-Regular.ttf",
    "Crimson-Italic": "CrimsonText-Italic.ttf",
    "Crimson-Bold": "CrimsonText-Bold.ttf",
    "Crimson-SemiBold": "CrimsonText-SemiBold.ttf",
}
_registered = False


def register_fonts():
    global _registered
    if _registered:
        return
    for name, fn in _FONTS.items():
        pdfmetrics.registerFont(TTFont(name, os.path.join(FONT_DIR, fn)))
    pdfmetrics.registerFontFamily("Poppins", normal="Poppins", bold="Poppins-Bold",
                                  italic="Poppins-Italic", boldItalic="Poppins-Bold")
    pdfmetrics.registerFontFamily("Poppins-Light", normal="Poppins-Light", bold="Poppins-Medium",
                                  italic="Poppins-Italic", boldItalic="Poppins-Bold")
    pdfmetrics.registerFontFamily("Crimson", normal="Crimson", bold="Crimson-Bold",
                                  italic="Crimson-Italic", boldItalic="Crimson-Bold")
    _registered = True


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


@dataclass
class Theme:
    key: str               # 'walter' | 'sal'
    brand: str             # brand line
    author: str            # pen name
    head: str              # heading font
    head_caps: bool
    body: str
    body_size: float
    label: str             # small label font
    label_caps: bool
    italic: str
    dark: tuple
    accent: tuple
    light: tuple
    publisher_line: str = ""


WALTER = Theme("walter", "WALTER'S HOME CHECK", "Walter Briggs", "Bebas", True,
               "Poppins-Light", 9.2, "Poppins-Medium", True, "Poppins-Italic",
               hexrgb("#1C2B3A"), hexrgb("#E07A1F"), hexrgb("#F2EDE4"))
SAL = Theme("sal", "CHEF SAL ROMANO", "Sal Romano", "DMSerif", False,
            "Crimson", 11.6, "Crimson-SemiBold", False, "Crimson-Italic",
            hexrgb("#2A1E18"), hexrgb("#BE3A24"), hexrgb("#FAF4E8"))

# interior is printed in black ink - use greys only
INK = 0.12
MID = 0.42
LINE = 0.62
SOFT = 0.80
TINT = 0.91


@dataclass
class BookSpec:
    slug: str
    theme: Theme
    title: str
    subtitle: str
    trim: tuple            # inches (w, h)
    pages: int             # final page count (even)
    price: float
    cover_title: list      # list of lines for the front cover title
    cover_kicker: str      # small line above title
    cover_tagline: str     # line under title
    cover_layout: str      # 'band' | 'frame' | 'split'
    icon: str
    back_headline: str
    back_blurb: str
    back_bullets: list
    spine_title: str
    sections: list = field(default_factory=list)   # [(name, [pagefn,...])]
    content_file: str = ""
    paper: str = "white"
