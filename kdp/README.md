# kdpgen — KDP low-content paperback generator

Builds KDP-ready paperbacks (black & white, no bleed) with ReportLab:

- `kdpgen/interior.py` — interior PDF: markup guide pages + fill-in form pages, mirrored margins (gutter on the binding side), page numbers, contents page, automatic tightening of guide sections that would leave a near-empty page, padding to an even page count.
- `kdpgen/forms.py`, `kdpgen/pages.py` — drawing primitives and page factories (log tables, record cards, checklists, check grids, calendars, dot/grid paper...). Interiors are greyscale only.
- `kdpgen/cover.py` — full-wrap cover PDF: bleed 0.125", spine = pages × 0.002252" (white paper), spine text only above 79 pages with 0.0625" clearance, clear white 2" × 1.2" barcode box bottom-right of the back, text ≥ 0.375" inside the trim. All vector.
- `kdpgen/validate.py` — checks page size, page count parity, margins (every glyph/line inside the design margins and KDP minimums), 7 pt minimum font size, blank pages, embedded fonts (`pdffonts`), cover size vs. formula, text safe zone, barcode area pixels, spine text clearance (rendered at 600 dpi).
- `kdpgen/core.py` — KDP constants, printing-cost and royalty math, brand themes.
- `build.py` — builds every book in `books/` into `../<slug>/` with previews, listing.md and INDEX.md.
- `fonts/` — Bebas Neue, Poppins, DM Serif Display, Crimson Text (SIL Open Font License, licenses included).

Book specs (`books/`) and guide text (`content/`) are separate from the engine.

Requirements: Python 3, reportlab, pdfplumber, Pillow, numpy, pyyaml, poppler-utils (`pdftoppm`, `pdffonts`).

```
python3 build.py            # all books
python3 build.py italian    # one book (filter by spec name or slug)
```

Note: this folder holds only the engine. The book specs (`books/`) and guide texts (`content/`) are kept privately and are not in this repository, so `build.py` needs a `books/` package next to it to run.
