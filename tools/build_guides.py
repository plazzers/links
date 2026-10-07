"""Build the guide sites for Walter and Sal from Markdown.

    python3 tools/build_guides.py

Reads content/walter/*.md, content/sal/*.md and content/about/*.md and writes
(all generated files are committed):

    <channel>/guides/index.html            guides index (search + category chips)
    <channel>/guides/<slug>/index.html     one page per article (+ og.jpg)
    <channel>/guides/{guides.css,guides.js,search.json,feed.xml,og.jpg,avatar.webp}
    <channel>/about/index.html             about page
    sitemap.xml, robots.txt                for the whole site
    + the "Related guides" strip on the two free tools (between marker comments)

Idempotent: running it twice gives the same files. Needs markdown, pyyaml,
pillow (pip install markdown pyyaml pillow).
"""
import html
import io
import json
import math
import re
import sys
from datetime import date, datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import make_og  # noqa: E402
from guide_rules import CATEGORIES, all_articles, lint, plain_words, split, teasers  # noqa: E402

SITE = "https://plazzers.github.io/links/"
esc = html.escape

CH = {
    "walter": {
        "name": "Walter's Home Check",
        "short": "Walter",
        "tagline": "What homeowners miss",
        "theme": "#1C2B3A",
        "email": "waltershomecheck@outlook.com",
        "youtube": "https://www.youtube.com/@WaltersHomeCheck",
        "author_box": "Walter's Home Check — plain-English home checks from the YouTube channel. "
                      "We explain what to look at and when to call a licensed pro.",
        "disclaimer": "Educational content. Not a substitute for a professional inspection of your property.",
        "index_title": "Home Guides: Checklists & Warning Signs",
        "index_h1": "Home guides",
        "index_intro": "Plain-English guides to the warning signs most homeowners walk right past — "
                       "what you can look at yourself, and when it's time to call a licensed pro.",
        "index_desc": "Free home guides from Walter's Home Check: buying red flags, seasonal checklists, "
                      "home systems and older-home issues, in plain English.",
        "tool": ("../../house-age/", "FREE TOOL", "What to Check in a House Built in…",
                 "Pick the year your house was built and get the checklist for that era."),
        "free": ("hiIm1", "The Weekend Home Check", "25 things to check in 30 minutes. A free printable PDF."),
        "products": {
            "app": ("OZeda", "Walter's Home Check App",
                    "The whole room-by-room checklist on your phone. Photos, notes, PDF report."),
            "redflag": ("HAfRF", "The House Buyer's Red Flag Checklist",
                        "50 things to check before you buy — take it to every showing."),
            "manual": ("ABaxT", "The Home Check Manual",
                       "Room-by-room guide, seasonal calendar and home record page."),
        },
        "related_tool": ["buying-an-older-home-checklist", "knob-and-tube-wiring",
                         "lead-paint-in-older-homes", "polybutylene-and-galvanized-pipes"],
        "tool_dir": "house-age",
    },
    "sal": {
        "name": "Chef Sal Romano",
        "short": "Sal",
        "tagline": "What the restaurants won't tell you.",
        "theme": "#2A1E18",
        "email": "salromanochef@outlook.com",
        "youtube": "https://www.youtube.com/@ChefSalRomano",
        "author_box": "Chef Sal Romano — restaurant secrets and copycat recipes from the YouTube channel, "
                      "made for home cooks.",
        "disclaimer": "Recipes are inspired by popular restaurant dishes. Not affiliated with or endorsed by any restaurant.",
        "index_title": "Restaurant Secrets & Copycat Recipes",
        "index_h1": "Sal's guides",
        "index_intro": "How restaurants get you to spend more — and how to cook the dishes you love "
                       "at home for a fraction of the price.",
        "index_desc": "Free guides from Chef Sal Romano: menu tricks, what to order and what to skip, "
                      "and copycat restaurant dishes you can make at home.",
        "tool": ("../../restaurant-or-home/", "FREE CALCULATOR", "Restaurant or Home?",
                 "Pick the dishes and the people. See what you keep by cooking it yourself."),
        "free": ("dnY7F", "Sal's 25 Rules for Eating Out", "Order smarter, spend less. A free PDF."),
        "products": {
            "app": ("xM6XQ", "Sal's Kitchen App",
                    "All 33 restaurant favorites on your phone, with shopping list & cooking timers."),
            "cookbook": ("MQDaN", "Sal's Restaurant Copycat Cookbook",
                         "33 restaurant dishes at home for a fraction of the price — with exact amounts."),
            "italian": ("Lv425", "Sal's Italian Kitchen", "60 real Italian recipes, from antipasti to dolci."),
        },
        "related_tool": ["eating-out-vs-cooking-at-home", "how-to-eat-out-cheaper",
                         "restaurant-drink-markup", "sunday-marinara-sauce"],
        "tool_dir": "restaurant-or-home",
    },
}
YT_SVG = ('<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path fill="currentColor" '
          'd="M23 7.2a3 3 0 0 0-2.1-2.1C19 4.6 12 4.6 12 4.6s-7 0-8.9.5A3 3 0 0 0 1 7.2 31 31 0 0 0 .5 12a31 31 0 0 0 '
          '.5 4.8 3 3 0 0 0 2.1 2.1c1.9.5 8.9.5 8.9.5s7 0 8.9-.5a3 3 0 0 0 2.1-2.1 31 31 0 0 0 .5-4.8 31 31 0 0 0-.5-4.8z'
          'M9.7 15V9l5.8 3-5.8 3z"/></svg>')


def payhip(code, campaign):
    return f"https://payhip.com/b/{code}?utm_source=guides&amp;utm_medium=article&amp;utm_campaign={campaign}"


def jpeg(im):
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True, progressive=True)
    return buf.getvalue()


def write(path, text):
    """Write only when the content changed (keeps mtimes and git quiet)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = text.encode("utf-8") if isinstance(text, str) else text
    if not path.exists() or path.read_bytes() != data:
        path.write_bytes(data)


def fmt_date(d):
    return f"{d:%B} {d.day}, {d.year}"


# ---------------------------------------------------------------- articles

class Article:
    def __init__(self, path):
        self.channel = path.parent.name
        self.slug = path.stem
        fm, body = split(path.read_text(encoding="utf-8"))
        self.fm, self.md = fm, body
        self.title = fm["title"]
        self.seo_title = fm.get("seo_title") or self.title
        self.description = fm["description"]
        self.keyword = fm["keyword"]
        self.category = fm["category"]
        self.cat_label = CATEGORIES[self.channel][self.category]
        self.date, self.updated = fm["date"], fm["updated"]
        self.words = len(plain_words(body))
        self.minutes = max(1, math.ceil(self.words / 230))
        self.url = f"{SITE}{self.channel}/guides/{self.slug}/"
        self.headings = re.findall(r"^## (.+)$", body, re.M)

    @property
    def page_title(self):
        suffix = f" | {CH[self.channel]['name']}"
        return self.seo_title + suffix if len(self.seo_title + suffix) <= 60 else self.seo_title


def load():
    problems = [p for f in all_articles() for p in lint(f)]
    if problems:
        sys.exit("Content problems — fix these first:\n" + "\n".join(problems))
    arts = {"walter": [], "sal": []}
    for f in all_articles():
        a = Article(f)
        arts[a.channel].append(a)
    cat_order = {c: {k: i for i, k in enumerate(CATEGORIES[c])} for c in CATEGORIES}
    for c, lst in arts.items():
        lst.sort(key=lambda a: (-a.updated.toordinal(), cat_order[c][a.category], a.title))
    return arts


def related(a, pool):
    if a.fm.get("related"):
        by = {x.slug: x for x in pool}
        return [by[s] for s in a.fm["related"]][:3]
    words = set(re.findall(r"[a-z]{4,}", (a.keyword + " " + a.title).lower()))
    linked = set(re.findall(r"\]\(\.\./([a-z0-9-]+)/\)", a.md))

    def score(b):
        bw = set(re.findall(r"[a-z]{4,}", (b.keyword + " " + b.title).lower()))
        return (3 if b.category == a.category else 0) + len(words & bw) + (1 if b.slug in linked else 0)
    others = [b for b in pool if b.slug != a.slug]
    return sorted(others, key=lambda b: (-score(b), b.slug))[:3]


# ---------------------------------------------------------------- page parts

def head(ch, *, title, desc, url, og, og_alt, depth, og_type="website", extra="", noindex=False):
    c = CH[ch]
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="{c['theme']}">
<meta name="color-scheme" content="only light">
{'<meta name="robots" content="noindex">' if noindex else ''}<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{up}assets/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="{esc(c['name'])} guides" href="{SITE}{ch}/guides/feed.xml">
<link rel="stylesheet" href="{up}guides/guides.css">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(c['name'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{esc(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og}">
{extra}</head>
"""


def topbar(ch, depth, current):
    c = CH[ch]
    up = "../" * depth
    nav = [("guides", f"{up}guides/", "Guides"), ("about", f"{up}about/", "About")]
    links = "".join(
        f'<a href="{h}"{" aria-current=\"page\"" if k == current else ""}>{t}</a>' for k, h, t in nav)
    if ch == "walter":
        brand = f'<a class="brand" href="{up}"><span class="brand-mark" aria-hidden="true">W</span>Walter\'s Home Check</a>'
    else:
        brand = f'<a class="brand" href="{up}"><span class="brand-eyebrow">Chef</span> Sal Romano</a>'
    stripe = '<div class="tricolore" aria-hidden="true"></div>' if ch == "sal" else ""
    return f"""<body class="{ch}">
<a class="skip" href="#main">Skip to content</a>
{stripe}<header class="top"><div class="wrap top-in">{brand}<nav aria-label="Site">{links}</nav></div></header>
"""


def footer(ch, depth):
    c = CH[ch]
    up = "../" * depth
    tool_href = f"{up}{c['tool_dir']}/"
    return f"""<footer class="foot"><div class="wrap">
<p class="disc">{esc(c['disclaimer'])}</p>
<p><a href="{up}">{esc(c['name'])} links</a> · <a href="{up}guides/">All guides</a> · <a href="{tool_href}">{esc(c['tool'][2])}</a> · <a href="{up}about/">About</a></p>
<p>Questions? <a href="mailto:{c['email']}">{c['email']}</a></p>
<p>© 2026 {esc(c['name'])}</p>
</div></footer>
<script src="{up}guides/guides.js" defer></script>
</body>
</html>
"""


def free_box(ch, campaign):
    code, title, sub = CH[ch]["free"]
    return f"""<aside class="box box-free" aria-label="Free PDF">
<p class="box-kicker">Free PDF</p>
<p class="box-title">{esc(title)}</p>
<p>{esc(sub)}</p>
<a class="btn btn-primary" href="{payhip(code, campaign)}">Get it free</a>
</aside>
"""


def product_cards(ch, keys, campaign, kicker):
    cards = "".join(
        f'<a class="pcard" href="{payhip(CH[ch]["products"][k][0], campaign)}"><b>{esc(CH[ch]["products"][k][1])}</b>'
        f'<span>{esc(CH[ch]["products"][k][2])}</span><span class="go" aria-hidden="true">→</span></a>'
        for k in keys)
    return f"""<aside class="box box-product" aria-label="{esc(kicker)}">
<p class="box-kicker">{esc(kicker)}</p>
{cards}
</aside>
"""


def tool_box(ch):
    href, label, title, sub = CH[ch]["tool"]
    return f"""<aside class="box box-tool" aria-label="{esc(label.title())}">
<a class="tool" href="{href}"><span class="box-kicker">{esc(label)}</span><b>{esc(title)}</b><span>{esc(sub)}</span></a>
</aside>
"""


def yt_box(ch):
    return f"""<aside class="box box-yt" aria-label="YouTube">
<p>Prefer to watch? {'Walter walks through checks like these' if ch == 'walter' else 'Sal shows tricks and dishes like these'} on YouTube.</p>
<a class="btn btn-yt" href="{CH[ch]['youtube']}">{YT_SVG} Watch on YouTube</a>
</aside>
"""


def glance_box(rec):
    return f"""<aside class="box box-glance" aria-label="At a glance">
<p class="box-kicker">At home, at a glance</p>
<dl><div><dt>Time</dt><dd>{esc(rec['time'])}</dd></div><div><dt>Cost</dt><dd>{esc(rec['cost'])}</dd></div><div><dt>Makes</dt><dd>{esc(rec['serves'])}</dd></div></dl>
<p class="small">Costs are rough supermarket estimates and change with prices where you live.</p>
</aside>
"""


def free_sample(rec, campaign):
    ings = "".join(f"<li>{esc(i)}</li>" for i in rec["ingredients"])
    steps = "".join(f"<li>{esc(s)}</li>" for s in rec["steps"])
    return f"""<section class="recipe" aria-labelledby="recipe-title">
<p class="recipe-flag">Free from Sal's Restaurant Copycat Cookbook</p>
<h2 id="recipe-title">{esc(rec['title'])}: the full recipe</h2>
<dl class="recipe-meta"><div><dt>Makes</dt><dd>{esc(rec['serves'])}</dd></div><div><dt>Time</dt><dd>{esc(rec['time'])}</dd></div><div><dt>Cost</dt><dd>{esc(rec['cost'])}</dd></div></dl>
<h3>Ingredients</h3>
<ul>{ings}</ul>
<h3>Method</h3>
<ol>{steps}</ol>
<p class="recipe-tip"><b>Sal's tip:</b> {esc(rec['tip'])}</p>
<p class="small">This is one of three free samples. The other recipes are in <a href="{payhip('MQDaN', campaign)}">Sal's Restaurant Copycat Cookbook</a>.</p>
</section>
"""


MD = markdown.Markdown(extensions=["tables", "sane_lists", "toc", "attr_list"],
                       extension_configs={"toc": {"permalink": False, "toc_depth": "2"}})


def render_body(a):
    MD.reset()
    body = MD.convert(a.md)
    toc = [(t["id"], t["name"]) for t in MD.toc_tokens]
    body = re.sub(r"<table>", '<div class="table"><table>', body).replace("</table>", "</table></div>")
    body = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" rel="noopener"', body)
    ch, rec = a.channel, None
    if ch == "sal" and a.category == "copycat":
        rec = teasers()[a.fm["recipe"]]
    if a.fm.get("free_sample"):
        body = body.replace("<p>[[free-sample]]</p>", free_sample(rec, a.slug))
        before = len(re.findall(r"^## ", a.md.split("[[free-sample]]")[0], re.M))
        toc.insert(before, ("recipe-title", "The full recipe (free)"))

    parts = re.split(r"(?=<h2[ >])", body)  # parts[0] = intro, then one part per h2 section
    intro, sections = parts[0], parts[1:]
    n = len(sections)
    extra = {}  # section index -> html to insert BEFORE that section

    def add(i, s):
        extra[i] = extra.get(i, "") + s
    if rec:
        intro += glance_box(rec)
    add(1 if n > 2 else 0, free_box(ch, a.slug))
    if ch == "sal" or a.fm.get("house_age_tool"):
        add(max(2, min(n - 1, (n + 1) // 2 + 1)), tool_box(ch))
    if ch == "walter":
        keys, kicker = [a.fm["product"]], "Go further"
    elif a.category == "copycat":
        keys = ["cookbook", "app"] + (["italian"] if a.fm.get("italian") else [])
        kicker = "Get the full recipe"
    else:
        keys, kicker = ["cookbook", "app"], "Cook it at home instead"
    tail = product_cards(ch, keys, a.slug, kicker) + yt_box(ch)
    out = intro + "".join(extra.get(i, "") + s for i, s in enumerate(sections)) + tail
    return out, toc


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>\n"


def org(ch):
    return {"@type": "Organization", "name": CH[ch]["name"], "url": f"{SITE}{ch}/",
            "logo": {"@type": "ImageObject", "url": f"{SITE}{ch}/assets/apple-touch-icon.png"},
            "sameAs": [CH[ch]["youtube"]]}


def article_page(a, pool):
    ch, c = a.channel, CH[a.channel]
    body, toc = render_body(a)
    og = f"{a.url}og.jpg"
    ld = jsonld({"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "headline": a.title, "description": a.description, "image": [og],
         "datePublished": a.date.isoformat(), "dateModified": a.updated.isoformat(),
         "author": {"@type": "Organization", "name": c["name"], "url": f"{SITE}{ch}/about/"},
         "publisher": org(ch), "mainEntityOfPage": a.url, "url": a.url, "keywords": a.keyword,
         "articleSection": a.cat_label, "wordCount": a.words, "inLanguage": "en"},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": c["name"], "item": f"{SITE}{ch}/"},
            {"@type": "ListItem", "position": 2, "name": "Guides", "item": f"{SITE}{ch}/guides/"},
            {"@type": "ListItem", "position": 3, "name": a.title, "item": a.url}]},
    ]})
    extra = (f'<meta property="article:published_time" content="{a.date.isoformat()}">\n'
             f'<meta property="article:modified_time" content="{a.updated.isoformat()}">\n'
             f'<meta property="article:section" content="{esc(a.cat_label)}">\n' + ld)
    toc_html = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in toc)
    srcs = a.fm.get("sources") or []
    sources = ""
    if srcs:
        items = "".join(f'<li><a href="{esc(s["url"])}" rel="noopener">{esc(s["title"])}</a></li>' for s in srcs)
        sources = f'<section class="sources" aria-labelledby="sources"><h2 id="sources">Sources &amp; further reading</h2><ul>{items}</ul></section>\n'
    rel = "".join(
        f'<li><a class="rcard" href="../{r.slug}/"><span class="chip">{esc(r.cat_label)}</span>'
        f'<b>{esc(r.title)}</b><span>{r.minutes} min read</span></a></li>' for r in related(a, pool))
    return (head(ch, title=a.page_title, desc=a.description, url=a.url, og=og, og_alt=a.title, depth=2,
                 og_type="article", extra=extra)
            + topbar(ch, 2, "guides") + f"""<main id="main" class="wrap">
<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../../">{esc(c['name'])}</a></li><li><a href="../">Guides</a></li><li><a href="../?c={a.category}">{esc(a.cat_label)}</a></li></ol></nav>
<div class="layout">
<article class="article">
<header class="art-head">
<p class="chip">{esc(a.cat_label)}</p>
<h1>{esc(a.title)}</h1>
<p class="dek">{esc(a.description)}</p>
<p class="meta"><span>Last updated <time datetime="{a.updated.isoformat()}">{fmt_date(a.updated)}</time></span><span>{a.minutes} min read</span>
<button class="share" type="button" data-title="{esc(a.title)}" data-url="{a.url}"><svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3v12M7 8l5-5 5 5M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>Share</button></p>
<p class="share-status" role="status" aria-live="polite"></p>
</header>
<details class="toc toc-m"><summary>On this page</summary><nav aria-label="Table of contents"><ol>{toc_html}</ol></nav></details>
<nav class="toc toc-d" aria-label="On this page"><p class="toc-h">On this page</p><ol>{toc_html}</ol></nav>
<div class="prose">
{body}</div>
{sources}<section class="author" aria-label="About the author">
<img src="../avatar.webp" width="64" height="64" alt="{esc(c['short'])}, host of {esc(c['name'])}" loading="lazy" decoding="async">
<div><p class="author-name">{esc(c['name'])}</p><p>{esc(c['author_box'])}</p><p><a href="../../about/">About this site</a> · <a href="{c['youtube']}">YouTube channel</a></p></div>
</section>
<p class="disclaimer">{esc(c['disclaimer'])}</p>
</article>
</div>
<section class="related" aria-labelledby="related"><h2 id="related">Related guides</h2><ul class="rgrid">{rel}</ul></section>
</main>
""" + footer(ch, 2))


# ---------------------------------------------------------------- index, about

def card(a, hidden=False):
    return (f'<li class="gcard" data-slug="{a.slug}" data-cat="{a.category}"><a href="{a.slug}/">'
            f'<span class="chip">{esc(a.cat_label)}</span><b>{esc(a.title)}</b>'
            f'<span class="gdesc">{esc(a.description)}</span><span class="gmeta">{a.minutes} min read</span></a></li>')


def index_page(ch, arts):
    c = CH[ch]
    url = f"{SITE}{ch}/guides/"
    starts = [a for a in arts if a.fm.get("start_here")][:3]
    chips = '<button type="button" class="fchip" data-cat="" aria-pressed="true">All</button>' + "".join(
        f'<button type="button" class="fchip" data-cat="{k}" aria-pressed="false">{esc(v)}</button>'
        for k, v in CATEGORIES[ch].items())
    ld = jsonld({"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": f"{c['name']} — {c['index_title']}", "url": url,
         "description": c["index_desc"], "publisher": org(ch),
         "mainEntity": {"@type": "ItemList", "itemListElement": [
             {"@type": "ListItem", "position": i + 1, "url": a.url} for i, a in enumerate(arts)]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": c["name"], "item": f"{SITE}{ch}/"},
            {"@type": "ListItem", "position": 2, "name": "Guides", "item": url}]}]})
    title = f"{c['index_title']} | {c['name']}"
    if len(title) > 60:
        title = c["index_title"]
    return (head(ch, title=title, desc=c["index_desc"], url=url, og=f"{url}og.jpg",
                 og_alt=f"{c['name']} guides", depth=1, extra=ld)
            + topbar(ch, 1, "guides") + f"""<main id="main" class="wrap">
<header class="hero">
<p class="kicker">{esc(c['name'])}</p>
<h1>{esc(c['index_h1'])}</h1>
<p class="lead">{esc(c['index_intro'])}</p>
<form class="search" role="search" action="./" onsubmit="return false">
<label for="q">Search the guides</label>
<input id="q" name="q" type="search" placeholder="{'e.g. basement, radon, roof' if ch == 'walter' else 'e.g. alfredo, menu, drinks'}" autocomplete="off">
</form>
</header>
<section aria-labelledby="start"><h2 id="start">Start here</h2>
<ul class="ggrid start">{''.join(card(a) for a in starts)}</ul></section>
{free_box(ch, 'guides-index')}
<section aria-labelledby="all"><h2 id="all">Latest guides</h2>
<div class="chips" role="group" aria-label="Filter by category">{chips}</div>
<p class="count" id="count" role="status" aria-live="polite">{len(arts)} guides</p>
<ul class="ggrid" id="list">{''.join(card(a) for a in arts)}</ul>
<p class="empty" id="empty" hidden>Nothing matches that yet. Try another word, or <a href="./">see all guides</a>.</p>
</section>
{tool_box(ch).replace('../../', '../')}
</main>
""" + footer(ch, 1))


def about_page(ch, arts):
    c = CH[ch]
    fm, md = split((ROOT / "content" / "about" / f"{ch}.md").read_text(encoding="utf-8"))
    MD.reset()
    body = MD.convert(md)
    url = f"{SITE}{ch}/about/"
    ld = jsonld({"@context": "https://schema.org", "@type": "AboutPage", "name": fm["title"], "url": url,
                 "description": fm["description"], "publisher": org(ch)})
    return (head(ch, title=fm["seo_title"], desc=fm["description"], url=url, og=f"{SITE}{ch}/guides/og.jpg",
                 og_alt=c["name"], depth=1, extra=ld)
            + topbar(ch, 1, "about") + f"""<main id="main" class="wrap narrow">
<header class="art-head"><h1>{esc(fm['title'])}</h1></header>
<div class="prose">
{body}
</div>
{free_box(ch, 'about')}
<section class="author" aria-label="About the channel">
<img src="../guides/avatar.webp" width="64" height="64" alt="{esc(c['short'])}, host of {esc(c['name'])}" loading="lazy" decoding="async">
<div><p class="author-name">{esc(c['name'])}</p><p>{esc(c['author_box'])}</p><p><a href="mailto:{c['email']}">{c['email']}</a> · <a href="{c['youtube']}">YouTube channel</a></p></div>
</section>
</main>
""" + footer(ch, 1))


# ---------------------------------------------------------------- feeds, sitemap

def rfc822(d):
    return format_datetime(datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc))


def feed(ch, arts):
    c = CH[ch]
    last = max(a.updated for a in arts)
    items = "".join(f"""  <item>
    <title>{esc(a.title)}</title>
    <link>{a.url}</link>
    <guid isPermaLink="true">{a.url}</guid>
    <pubDate>{rfc822(a.date)}</pubDate>
    <category>{esc(a.cat_label)}</category>
    <description>{esc(a.description)}</description>
  </item>
""" for a in sorted(arts, key=lambda a: (-a.date.toordinal(), a.slug)))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
<channel>
  <title>{esc(c['name'])} — Guides</title>
  <link>{SITE}{ch}/guides/</link>
  <atom:link href="{SITE}{ch}/guides/feed.xml" rel="self" type="application/rss+xml"/>
  <description>{esc(c['index_desc'])}</description>
  <language>en</language>
  <lastBuildDate>{rfc822(last)}</lastBuildDate>
{items}</channel>
</rss>
"""


def sitemap(arts):
    urls = [("", None), ("walter/", None), ("sal/", None), ("walter/house-age/", None),
            ("sal/restaurant-or-home/", None)]
    for ch in ("walter", "sal"):
        urls.append((f"{ch}/guides/", max(a.updated for a in arts[ch])))
        urls.append((f"{ch}/about/", None))
        urls += [(f"{ch}/guides/{a.slug}/", a.updated) for a in arts[ch]]
    rows = "".join(f"  <url><loc>{SITE}{u}</loc>{f'<lastmod>{d.isoformat()}</lastmod>' if d else ''}</url>\n"
                   for u, d in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}</urlset>\n'


ROBOTS = f"""# Crawlers read robots.txt from the root of the host (plazzers.github.io/robots.txt);
# this copy documents the intent and points to the sitemap for Search Console.
User-agent: *
Allow: /

Sitemap: {SITE}sitemap.xml
"""


# ---------------------------------------------------------------- tools strip, link pages

def tool_strip(ch, arts):
    by = {a.slug: a for a in arts}
    cards = "".join(
        f'\n    <a class="card" href="../guides/{s}/"><b>{esc(by[s].title)}</b><span>{esc(by[s].description)}</span></a>'
        for s in CH[ch]["related_tool"] if s in by)
    return (f'<!-- related-guides:start (generated by tools/build_guides.py) -->\n'
            f'  <section class="cta related-guides" aria-labelledby="related-guides">\n'
            f'    <h2 id="related-guides">Related guides</h2>{cards}\n'
            f'    <a class="card" href="../guides/"><b>All guides →</b><span>{len(arts)} free guides from {esc(CH[ch]["name"])}.</span></a>\n'
            f'  </section>\n  <!-- related-guides:end -->')


def patch_between(path, block, anchor):
    src = path.read_text(encoding="utf-8")
    pat = re.compile(r"<!-- related-guides:start.*?<!-- related-guides:end -->", re.S)
    if pat.search(src):
        new = pat.sub(lambda m: block, src)
    else:
        new = src.replace(anchor, "  " + block + "\n" + anchor, 1)
    write(path, new)


# ---------------------------------------------------------------- main

def main():
    arts = load()
    for ch in ("walter", "sal"):
        gdir = ROOT / ch / "guides"
        gdir.mkdir(parents=True, exist_ok=True)
        css = (ROOT / "tools" / "guides" / "guides.css").read_text()
        theme = (ROOT / "tools" / "guides" / f"theme-{ch}.css").read_text()
        write(gdir / "guides.css", theme + css)
        write(gdir / "guides.js", (ROOT / "tools" / "guides" / "guides.js").read_text())
        buf = io.BytesIO()
        make_og.avatar_webp(ch, buf)
        write(gdir / "avatar.webp", buf.getvalue())
        live = {a.slug for a in arts[ch]}
        for old in gdir.iterdir():  # remove pages for deleted articles
            if old.is_dir() and old.name not in live:
                for f in old.iterdir():
                    f.unlink()
                old.rmdir()
        for a in arts[ch]:
            out = gdir / a.slug
            write(out / "index.html", article_page(a, arts[ch]))
            write(out / "og.jpg", jpeg(make_og.guide_og(ch, a.title, a.cat_label)))
        write(gdir / "og.jpg", jpeg(make_og.guide_og(ch, CH[ch]["index_title"], "Free guides")))
        write(gdir / "index.html", index_page(ch, arts[ch]))
        write(gdir / "search.json", json.dumps([
            {"slug": a.slug, "title": a.title, "description": a.description, "keyword": a.keyword,
             "category": a.category, "headings": [re.sub(r"[*_`]", "", h) for h in a.headings]}
            for a in arts[ch]], ensure_ascii=False, indent=0) + "\n")
        write(gdir / "feed.xml", feed(ch, arts[ch]))
        write(ROOT / ch / "about" / "index.html", about_page(ch, arts[ch]))
        patch_between(ROOT / ch / CH[ch]["tool_dir"] / "index.html", tool_strip(ch, arts[ch]), "</main>")
    write(ROOT / "sitemap.xml", sitemap(arts))
    write(ROOT / "robots.txt", ROBOTS)
    n = sum(len(v) for v in arts.values())
    print(f"Built {n} articles ({len(arts['walter'])} Walter, {len(arts['sal'])} Sal), indexes, about pages, feeds, sitemap.")


if __name__ == "__main__":
    main()
