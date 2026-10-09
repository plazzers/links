"""Build every book: interior, cover, previews, listing, validation, INDEX.

Usage: python3 build.py [slug-filter]
Output goes to ../<slug>/ (i.e. KDP/<slug>/).
"""
import os
import sys
import json
import subprocess
import glob
from PIL import Image, ImageFilter, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kdpgen.interior import build_interior
from kdpgen.cover import build_cover, cover_geometry
from kdpgen.validate import validate_interior, validate_cover
from kdpgen.core import print_cost, royalty, is_large_trim, BLEED
from books import walter, sal
from books.common import disclaimer_for

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # KDP/


def render(pdf, out_prefix, dpi, first=None, last=None):
    cmd = ["pdftoppm", "-r", str(dpi), "-png"]
    if first:
        cmd += ["-f", str(first), "-l", str(last)]
    subprocess.run(cmd + [pdf, out_prefix], check=True)


def previews(spec, d, g):
    pv = os.path.join(d, "previews")
    os.makedirs(pv, exist_ok=True)
    for f in glob.glob(os.path.join(pv, "*.png")):
        os.remove(f)
    render(os.path.join(d, "interior.pdf"), os.path.join(pv, "page"), 100, 1, 12)
    # cover full
    subprocess.run(["pdftoppm", "-r", "100", "-png", "-singlefile", os.path.join(d, "cover.pdf"),
                    os.path.join(pv, "cover-full")], check=True)
    # front crop at high res for the JPGs
    dpi = 300
    tmp = os.path.join(pv, "_hi")
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", os.path.join(d, "cover.pdf"), tmp], check=True)
    im = Image.open(tmp + ".png").convert("RGB")
    os.remove(tmp + ".png")
    s = dpi / 72
    fx, fy, fw, fh = g["front"]
    H = g["H"]
    front = im.crop((round(fx * s), round((H - fy - fh) * s), round((fx + fw) * s), round((H - fy) * s)))
    # exact-proportion front (for A+ content / social)
    ex = front.resize((1600, round(1600 * front.height / front.width)), Image.LANCZOS)
    ex.save(os.path.join(d, "cover-front-exact.jpg"), quality=92)
    # 1600x2560 preview: book on a soft backdrop
    th = spec.theme
    bg = tuple(int(v * 255) for v in th.light)
    canvas = Image.new("RGB", (1600, 2560), bg)
    maxw, maxh = 1360, 2240
    k = min(maxw / front.width, maxh / front.height)
    fr = front.resize((round(front.width * k), round(front.height * k)), Image.LANCZOS)
    x = (1600 - fr.width) // 2
    y = (2560 - fr.height) // 2
    shadow = Image.new("RGBA", (fr.width + 120, fr.height + 120), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((60, 60, 60 + fr.width, 60 + fr.height), fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    canvas.paste(shadow, (x - 60 + 18, y - 60 + 24), shadow)
    canvas.paste(fr, (x, y))
    canvas.save(os.path.join(d, "cover-front.jpg"), quality=92)
    # contact sheet: front cover + 12 pages
    pages = sorted(glob.glob(os.path.join(pv, "page-*.png")))
    thumbs = [front] + [Image.open(p).convert("RGB") for p in pages]
    tw = 300
    th_ = round(tw * front.height / front.width)
    cols = 7
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + 16) + 16, rows * (th_ + 16) + 16), (120, 120, 120))
    for i, t in enumerate(thumbs):
        t = t.resize((tw, th_), Image.LANCZOS)
        sheet.paste(t, (16 + (i % cols) * (tw + 16), 16 + (i // cols) * (th_ + 16)))
    sheet.save(os.path.join(pv, "contact-sheet.png"))


def money(x):
    return f"${x:,.2f}"


def listing_md(spec, listing, g, toc, n_natural):
    th = spec.theme
    w, h = spec.trim
    cost, cost_txt = print_cost(spec.pages, w, h)
    roy, rate = royalty(spec.price, cost)
    large = is_large_trim(w, h)
    kw = listing["keywords"]
    assert len(kw) == 7
    cats = listing["categories"]
    desc = listing["description_html"].strip()
    finish = "Matte" if th.key == "walter" else "Glossy (wipes clean in a kitchen)"
    contents = "\n".join(f"| {name} | {pg} |" for kind, name, pg in toc)
    md = f"""# KDP listing — {spec.title}

Copy each field into KDP exactly as written. Files are in this folder: `interior.pdf` (manuscript), `cover.pdf` (cover).

## 1. Paperback Details (first KDP tab)

| KDP field | Enter this |
|---|---|
| Language | English |
| Book Title | {spec.title} |
| Subtitle | {spec.subtitle} |
| Series | (leave empty) |
| Edition Number | (leave empty) |
| Author — first name / last name | {th.author.split()[0]} / {th.author.split()[1]} *(brand pen name — no biography or credentials anywhere)* |
| Contributors | (leave empty) |
| Publishing rights | "I own the copyright and I hold the necessary publishing rights" |
| Primary audience / sexually explicit | No |
| Reading age | {"(optional) leave empty, or set a range if you want children's categories" if "kids" in spec.slug else "(leave empty)"} |
| Primary marketplace | Amazon.com |
| Low-content book | **Yes — tick the "Low-content book" box under Categories** (KDP rejects low-content books that aren't marked) |
| Large-print book | No |

### Description (paste into the description box; KDP accepts this HTML)
```html
{desc}
```

### 7 keywords (one per box)
{chr(10).join(f"{i + 1}. {k}" for i, k in enumerate(kw))}

### Categories (choose up to 3 in KDP's category picker — names there may differ slightly; pick the closest match)
{chr(10).join(f"- {c}" for c in cats)}

## 2. Paperback Content (second tab)

| KDP field | Enter this |
|---|---|
| Print ISBN | **None needed.** Low-content books can't use the free KDP ISBN; choose to publish without an ISBN (or use your own if you buy one). Without an ISBN there is no "Look Inside" and no Expanded Distribution (not offered for low-content books anyway). |
| Publication date | (leave empty) |
| Ink and paper type | Black & white interior with **white** paper |
| Trim size | {w:g} x {h:g} in |
| Bleed settings | **No Bleed** |
| Paperback cover finish | {finish} |
| Manuscript | upload `interior.pdf` ({spec.pages} pages) |
| Book cover | "Upload a cover you already have" → `cover.pdf` ({g['W'] / 72:.3f} x {g['H'] / 72:.3f} in, spine {g['sw'] / 72:.4f} in) |
| AI-generated content | **Yes** (see below) |
| Book preview | Launch Previewer, check the pages, then Approve |

### AI disclosure (KDP asks: did you use AI tools in creating text, images and/or translations?)
Honest answer: **Yes.**
- **Text:** AI-generated. The guide pages and all page labels were written by Claude (Anthropic). Choose the option for the *entire work*; pick "with minimal or no editing" unless you edit it yourself before upload (then "with extensive editing").
- **Images:** AI-generated. The cover and interior graphics (icons, patterns, layout) were produced by code written by Claude; no stock or third-party images. Choose the same level as above.
- **Translations:** None.
- Tool name if asked: Claude (Anthropic).
- You remain responsible for the content meeting KDP's content guidelines; it was written to avoid health, legal and price claims and real brand names.

## 3. Paperback Rights & Pricing (third tab)

| KDP field | Enter this |
|---|---|
| Territories | All territories (worldwide rights) |
| Primary marketplace | Amazon.com |
| Royalty plan | 60% (available because the list price is $9.99 or more) |
| List price (Amazon.com) | **{money(spec.price)}** |
| Other marketplaces | let KDP convert from USD, then round to a .99 price |
| Expanded distribution | Not available for low-content books |

**Printing cost (Amazon.com, black ink, white paper, {"large" if large else "regular"} trim):** {cost_txt}
**Royalty per sale:** {int(rate * 100)}% x {money(spec.price)} − {money(cost)} = {money(round(rate * spec.price, 2))} − {money(cost)} = **{money(roy)}**

*(Formula and rates from KDP help pages, checked 2026-10-09 — KDP's pricing page shows the live figure; trust it if it differs.)*

## Book facts
- Pages: **{spec.pages}** (front guide + fill-in pages; {spec.pages - n_natural} Notes pages at the end)
- Trim: {w:g} x {h:g} in · paper: white · interior: black & white · no bleed
- Pen name: {th.author} · brand: {"Walter's Home Check" if th.key == 'walter' else 'Chef Sal Romano'}

### Contents
| Section | Page |
|---|---|
{contents}
"""
    return md, cost, roy


def build(spec_fn):
    spec = spec_fn()
    spec.disclaimer = disclaimer_for(spec)
    d = os.path.join(ROOT, spec.slug)
    os.makedirs(d, exist_ok=True)
    listing, toc, n_nat = build_interior(spec, os.path.join(d, "interior.pdf"))
    g = build_cover(spec, os.path.join(d, "cover.pdf"))
    ei, ii = validate_interior(os.path.join(d, "interior.pdf"), spec)
    ec, ic = validate_cover(os.path.join(d, "cover.pdf"), spec)
    previews(spec, d, g)
    md, cost, roy = listing_md(spec, listing, g, toc, n_nat)
    open(os.path.join(d, "listing.md"), "w").write(md)
    rep = dict(slug=spec.slug, interior_errors=ei, cover_errors=ec, interior=ii,
               cover={k: (tuple(float(x) for x in v) if isinstance(v, tuple) else v) for k, v in ic.items()})
    open(os.path.join(d, "previews", "validation.json"), "w").write(json.dumps(rep, indent=2, default=str))
    status = "PASS" if not ei and not ec else "FAIL"
    print(f"{status} {spec.slug}: {spec.pages}p {spec.trim} ${spec.price} cost {cost} royalty {roy}", ei, ec)
    return dict(spec=spec, cost=cost, roy=roy, status=status)


def index(rows):
    lines = ["# KDP books — index", "",
             "All paperbacks: black & white interior, white paper, no bleed, low-content (no ISBN needed). "
             "Royalty = 60% of list price − Amazon.com printing cost (see each listing.md for the math).", "",
             "| # | Brand | Title | Trim (in) | Pages | List price | Print cost | Royalty / sale | Validator | Folder |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        s = r["spec"]
        lines.append(f"| {i} | {s.theme.author} | {s.title} | {s.trim[0]:g} x {s.trim[1]:g} | {s.pages} | "
                     f"{money(s.price)} | {money(r['cost'])} | {money(r['roy'])} | {r['status']} | `{s.slug}/` |")
    lines += ["", "Each folder: `interior.pdf`, `cover.pdf`, `cover-front.jpg` (1600x2560 preview), "
              "`cover-front-exact.jpg` (true proportions), `listing.md`, `previews/` (first 12 pages, full cover, "
              "contact sheet, validation.json).", "",
              "Rules used: `RULES.md`. Market notes: `RESEARCH.md`. How to publish: `UPLOAD-STEPS.md`. "
              "Generator: `generator/` (run `python3 generator/build.py`)."]
    open(os.path.join(ROOT, "INDEX.md"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    filt = sys.argv[1] if len(sys.argv) > 1 else ""
    rows = []
    for fn in walter.SPECS + sal.SPECS:
        if filt and filt not in fn.__name__ and filt not in fn().slug:
            continue
        rows.append(build(fn))
    if not filt:
        index(rows)
