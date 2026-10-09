"""Build the Faceless Creator Kit marketing site (creator-kit/) from Markdown.

    python3 tools/build_kit_site.py

Reads tools/kit_config.py (BUY_URL, FREE_URL, price), content/kit/*.md (guide
articles), tools/kit/ (CSS, JS, fonts) and source-assets/kit/ (screenshots),
and writes (all generated files are committed):

    creator-kit/index.html                     landing page (+ og.jpg)
    creator-kit/tools/index.html               the two free tools
    creator-kit/tools/title-scorer/            free YouTube title scorer (+ og.jpg)
    creator-kit/tools/pinterest-csv-checker/   free Pinterest CSV checker (+ og.jpg)
    creator-kit/guides/index.html              guide index with search
    creator-kit/guides/<slug>/index.html       one page per article (+ og.jpg)
    creator-kit/assets/                        css, js, fonts, images, icons
    sitemap.xml                                rebuilt via tools/build_guides.py (includes these pages)

Idempotent. Needs markdown, pyyaml, pillow (pip install markdown pyyaml pillow).
"""
import html
import io
import json
import math
import re
import shutil
import sys
from pathlib import Path

import markdown
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import kit_config as CFG  # noqa: E402
from guide_rules import plain_words, split  # noqa: E402
from kit_rules import CATEGORIES, all_articles, lint, lint_text  # noqa: E402

SITE = "https://plazzers.github.io/links/"
KIT = SITE + "creator-kit/"
OUT = ROOT / "creator-kit"
SRC = ROOT / "source-assets" / "kit"
FONTS = ROOT / "tools" / "fonts"
NAME = "Faceless Creator Kit"
THEME = "#1c1a27"
esc = html.escape

TOOLS = {
    "title-scorer": {
        "name": "YouTube Title Scorer",
        "short": "Score up to 3 YouTube titles out of 100. Every point is explained.",
        "kit": "Plan every video like this → Faceless Creator Kit",
    },
    "pinterest-csv-checker": {
        "name": "Pinterest CSV Checker",
        "short": "Check a Pinterest bulk-upload CSV before you upload it, and download a fixed copy.",
        "kit": "Make the pins and the CSV in one go → Pin Factory",
    },
}


# ---------------------------------------------------------------- helpers

def write(path, data):
    """Write only when the content changed (keeps git quiet)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    b = data.encode("utf-8") if isinstance(data, str) else data
    if not path.exists() or path.read_bytes() != b:
        path.write_bytes(b)


def store(url, medium, campaign):
    """A store link with the site's UTM tags (raw, not HTML-escaped)."""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}utm_source=kitsite&utm_medium={medium}&utm_campaign={campaign}"


def buy(medium, campaign):
    return esc(store(CFG.BUY_URL, medium, campaign))


def free(medium, campaign):
    return esc(store(CFG.FREE_URL, medium, campaign))


def jsonld(obj):
    return ('<script type="application/ld+json">'
            + json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>\n")


def fmt_date(d):
    return f"{d:%B} {d.day}, {d.year}"


# ---------------------------------------------------------------- images

def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def wrap(draw, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def og_card(title, kicker):
    """1200x630 share image in the kit's ink & coral look."""
    W, H = 1200, 630
    im = Image.new("RGB", (W, H), THEME)
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((700, -400, 1500, 300), fill=90)
    from PIL import ImageFilter
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    im.paste(Image.new("RGB", (W, H), "#ff6b4a"), (0, 0), glow)
    d = ImageDraw.Draw(im)
    logo = Image.open(SRC / "apple-touch-icon.png").convert("RGBA").resize((64, 64), Image.LANCZOS)
    im.paste(logo, (70, 62), logo)
    d.text((152, 106), NAME, font=font("SpaceGrotesk-Bold.ttf", 34), fill="#f2eff8", anchor="ls")
    d.text((70, 205), kicker.upper(), font=font("Inter-Bold.otf", 26), fill="#ff6b4a", anchor="ls")
    for size in (76, 70, 64, 58, 52, 46):
        f = font("SpaceGrotesk-Bold.ttf", size)
        lines = wrap(d, title, f, W - 140)
        if len(lines) <= 3:
            break
    y = 205 + 40 + size
    for line in lines:
        d.text((70, y), line, font=f, fill="#ffffff", anchor="ls")
        y += int(size * 1.12)
    d.text((70, 580), "plazzers.github.io/links/creator-kit", font=font("Inter-Medium.otf", 24), fill="#c9c5d8", anchor="ls")
    return im


def jpeg(im, q=84):
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=q, optimize=True, progressive=True)
    return buf.getvalue()


def webp(im, q=80):
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "WEBP", quality=q, method=6)
    return buf.getvalue()


def fit(im, w, ratio=None):
    """Resize to width w; with ratio (w/h), crop from the top first."""
    if ratio:
        h = round(im.width / ratio)
        if im.height > h:
            im = im.crop((0, 0, im.width, h))
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


SEQ = {
    "planner": [("app-09-board", "The board: every video from idea to published"),
                ("app-05-title-lab", "Title & thumbnail lab: three options, scored"),
                ("app-06-prompt", "Prompt builder: fill in your points, copy the prompt"),
                ("app-08-shorts", "Shorts planner: chapters become Shorts")],
    "pins": [("app-15-batch-paste", "Paste rows from your spreadsheet"),
             ("app-16-batch-grid", "Every pin renders at once"),
             ("app-17-batch-fix", "Click a pin to fix it"),
             ("app-18-export", "Export a ZIP and the Pinterest CSV")],
}
FEATURES = [("feature-1-planner-board", "The Channel Planner board"),
            ("feature-2-title-lab", "Title & thumbnail lab with explained scores"),
            ("feature-3-prompt-builder", "Prompt builder with three templates"),
            ("feature-4-pin-templates", "Eight Pinterest pin templates"),
            ("feature-5-batch-mode", "Batch mode: a spreadsheet becomes pins"),
            ("feature-6-export", "Export: images plus a bulk-upload CSV")]


def build_assets():
    a = OUT / "assets"
    write(a / "kit.css", (ROOT / "tools" / "kit" / "kit.css").read_text())
    for js in ("kit.js", "title-scorer.js", "csv-checker.js"):
        write(a / js, (ROOT / "tools" / "kit" / js).read_text())
    for f in (ROOT / "tools" / "kit" / "fonts").iterdir():
        write(a / "fonts" / f.name, f.read_bytes())
    write(a / "favicon.svg", (SRC / "icon.svg").read_bytes())
    write(a / "apple-touch-icon.png", (SRC / "apple-touch-icon.png").read_bytes())
    img = a / "img"
    cover = Image.open(SRC / "cover-1280x720.png")
    write(img / "hero.webp", webp(cover, 82))
    write(img / "hero-640.webp", webp(fit(cover, 640), 80))
    for key, shots in SEQ.items():
        for n, (src, _) in enumerate(shots, 1):
            write(img / f"seq-{key}-{n}.webp", webp(fit(Image.open(SRC / f"{src}.png"), 960, 16 / 10), 78))
    for src, _ in FEATURES:
        write(img / f"{src}.webp", webp(fit(Image.open(SRC / f"{src}.png"), 1000), 78))
    og = cover.resize((1200, 675), Image.LANCZOS).crop((0, 22, 1200, 652))
    write(OUT / "og.jpg", jpeg(og))


# ---------------------------------------------------------------- page parts

def head(*, title, desc, url, og, og_alt, depth, og_type="website", extra=""):
    up = "../" * depth
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="{THEME}">
<meta name="color-scheme" content="only light">
<link rel="icon" href="{up}assets/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="{up}assets/apple-touch-icon.png">
<link rel="preload" href="{up}assets/fonts/space-grotesk-latin-700-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{up}assets/kit.css">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{NAME}">
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


def topbar(depth, current):
    up = "../" * depth
    nav = [("home", up, "The kit"), ("tools", f"{up}tools/", "Free tools"), ("guides", f"{up}guides/", "Guides")]
    links = "".join(f'<a href="{h}"{" aria-current=\"page\"" if k == current else ""}>{t}</a>' for k, h, t in nav)
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top"><div class="wrap top-in"><a class="brand" href="{up}"><img src="{up}assets/favicon.svg" width="30" height="30" alt="">{NAME}</a><nav aria-label="Site">{links}</nav></div></header>
"""


def footer(depth, scripts=()):
    up = "../" * depth
    tags = "".join(f'<script src="{up}assets/{s}" defer></script>\n' for s in scripts)
    return f"""<footer class="foot"><div class="wrap">
<nav aria-label="Footer"><a href="{up}">{NAME}</a><a href="{up}tools/title-scorer/">YouTube Title Scorer</a><a href="{up}tools/pinterest-csv-checker/">Pinterest CSV Checker</a><a href="{up}guides/">Guides</a></nav>
<p>An independent tool for creators. Not affiliated with or endorsed by YouTube, Google or Pinterest.</p>
<p>No cookies, no tracking on this site. The free tools run in your browser; nothing you type is sent anywhere.</p>
<p>© 2026 {NAME}</p>
</div></footer>
{tags}</body>
</html>
"""


def free_box(medium, campaign):
    return f"""<aside class="box box-free" aria-label="Free download">
<p class="box-kicker">Free download</p>
<p class="box-title">{esc(CFG.FREE_NAME)}</p>
<p>{esc(CFG.FREE_DESC)}</p>
<a class="btn btn-dark btn-small" href="{free(medium, campaign)}">Get it free</a>
</aside>
"""


def product_box(feature, medium, campaign, depth):
    up = "../" * depth
    if feature == "pins":
        title = "Make the pins and the CSV in one go"
        text = ("The Pin Factory in the Faceless Creator Kit turns spreadsheet rows into 1000×1500 pins in your "
                "brand, then exports the images and a Pinterest bulk-upload CSV with links, UTM tags and a schedule.")
    else:
        title = "Plan every video in one place"
        text = ("The Channel Planner in the Faceless Creator Kit keeps each video on a board, scores your titles, "
                "builds script prompts and descriptions, and turns chapters into Shorts. It runs in your browser.")
    return f"""<aside class="box box-product" aria-label="{NAME}">
<p class="box-kicker">{NAME}</p>
<p class="box-title">{title}</p>
<p>{text} One payment of ${CFG.PRICE}, no subscription.</p>
<div class="btns"><a class="btn btn-primary btn-small" href="{buy(medium, campaign)}">Get the kit — ${CFG.PRICE}</a><a class="btn btn-ghost btn-small" href="{up}#tools">See how it works</a></div>
</aside>
"""


def tool_box(tool, depth):
    up = "../" * depth
    t = TOOLS[tool]
    return f"""<aside class="box box-tool" aria-label="Free tool">
<a href="{up}tools/{tool}/"><span class="box-kicker">Free tool</span><b>{esc(t['name'])}</b><span>{esc(t['short'])}</span> <span class="go">Try it →</span></a>
</aside>
"""


def org():
    return {"@type": "Organization", "name": NAME, "url": KIT,
            "logo": {"@type": "ImageObject", "url": KIT + "assets/apple-touch-icon.png"}}


def crumbs_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}


# ---------------------------------------------------------------- landing page

FAQ = [
    ("Is this a subscription?", "No. One payment, and you keep access to the app."),
    ("Do I need to install anything?", "No. It opens in your browser. You can optionally install it like an app from the browser so it has its own window and icon."),
    ("Where is my data stored? Can you see it?", "Only in your own browser, on your own device. Nothing is sent to us or anyone else. That also means you should download a backup now and then (one click)."),
    ("Can I use it on my phone and my computer?", "Yes. Each device keeps its own data; move it with Backup → Restore."),
    ("Does it work for more than one channel?", "Yes, add as many channels as you like, each with its own products, keywords and pin branding."),
    ("Which AI tool do the prompts work with?", "Any chat-style AI tool you already use for scripts. The kit builds the prompt; you paste it where you like."),
    ("Does it make videos, voices or avatars?", "No. It is a planning and production tool. It does not create videos, voices or avatars, and it does not post anything for you."),
    ("Does it post to Pinterest for me?", "No. It makes the pin images and the CSV file that Pinterest's own bulk upload accepts. You upload the CSV in your Pinterest account. You need a free place to host the images, for example GitHub Pages — step-by-step instructions are included."),
    ("Can I use the pins commercially?", "Yes. The pins you make are yours. The included fonts are open-source (SIL Open Font License)."),
    ("Will it get me more views or sales?", "It can't promise that. Results depend on your content, niche and consistency. The kit saves you time on planning and promotion; the videos are still yours to make."),
    ("How do I get access after buying?", "Payhip delivers a PDF quick-start guide with your personal access code. Open the app address in the guide, type the code once per browser, and you're in."),
    ("I lost my access code.", "Contact the seller through the Payhip store with your order details."),
]


def seq_html(key, depth):
    up = "../" * depth
    imgs = "".join(
        f'<img src="{up}assets/img/seq-{key}-{n}.webp" width="960" height="600" alt="{esc(alt)}" loading="lazy" decoding="async">'
        for n, (_, alt) in enumerate(SEQ[key], 1))
    steps = "".join(f"<li>{esc(alt.split(':')[0])}</li>" for _, alt in SEQ[key])
    return (f'<figure class="seq-fig"><div class="seq" role="img" aria-label="{esc("; ".join(a for _, a in SEQ[key]))}">{imgs}</div>'
            f'<figcaption><ol class="seq-steps">{steps}</ol></figcaption></figure>')


def landing():
    url = KIT
    title = "Faceless Creator Kit — YouTube Planner + Pinterest Pin Factory"
    desc = ("A browser app for faceless and AI-avatar YouTubers: plan every video on one board and turn a "
            "spreadsheet into Pinterest pins with a ready-to-upload CSV.")
    price = f"{float(CFG.PRICE):.2f}"
    ld = jsonld({"@context": "https://schema.org", "@graph": [
        {"@type": "Product", "name": NAME, "description": desc, "url": url,
         "image": [KIT + "og.jpg", KIT + "assets/img/hero.webp"], "brand": {"@type": "Brand", "name": NAME},
         "category": "Software", "offers": {"@type": "Offer", "price": price, "priceCurrency": "USD",
                                            "availability": "https://schema.org/InStock", "url": store(CFG.BUY_URL, "landing", "jsonld")}},
        {"@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]},
        org()]})
    faq = "".join(f"<details><summary>{esc(q)}</summary><div><p>{esc(a)}</p></div></details>" for q, a in FAQ)
    gallery = "".join(
        f'<figure class="card"><img class="shot-sm" src="assets/img/{s}.webp" width="1000" height="625" alt="{esc(a)}" loading="lazy" decoding="async"><figcaption class="small" style="margin-top:8px">{esc(a)}</figcaption></figure>'
        for s, a in FEATURES)
    return (head(title=title, desc=desc, url=url, og=KIT + "og.jpg", og_alt="Faceless Creator Kit: Channel Planner and Pin Factory", depth=0, extra=ld)
            + topbar(0, "home") + f"""<main id="main">
<section class="hero"><div class="wrap hero-grid">
<div>
<p class="kicker">For faceless &amp; AI-avatar YouTubers</p>
<h1>Plan every video. Make Pinterest pins in bulk.</h1>
<p class="lead">The Faceless Creator Kit is a browser app with two tools: a <b>Channel Planner</b> that takes each video from idea to published, and a <b>Pin Factory</b> that turns a spreadsheet into Pinterest pins plus a ready-to-upload CSV.</p>
<div class="btns"><a class="btn btn-primary" href="{buy('landing', 'hero')}">Get the kit — ${CFG.PRICE}</a><a class="btn btn-ghost" href="tools/">Try the free tools</a></div>
<p class="note">One-time payment · No account · Your data stays on your device · Works offline</p>
<ul class="chips"><li>Channel Planner</li><li>Pin Factory</li><li>8 pin templates</li><li>Bulk CSV export</li></ul>
</div>
<picture><source media="(max-width: 700px)" srcset="assets/img/hero-640.webp"><img class="shot" src="assets/img/hero.webp" width="1280" height="720" alt="The Faceless Creator Kit: title lab with scored titles and two example Pinterest pins" fetchpriority="high"></picture>
</div></section>

<section class="sec"><div class="wrap">
<h2>Running a faceless channel means a lot of small, repeated jobs</h2>
<div class="grid2">
<div class="card problem"><h3>Before</h3><ul class="ticks crosses">
<li>Video ideas in one app, scripts in another, titles in a sticky note.</li>
<li>Rewriting the same AI script prompt from scratch for every video.</li>
<li>Guessing between three titles at midnight.</li>
<li>Designing Pinterest pins one by one, then a CSV that Pinterest rejects.</li>
</ul></div>
<div class="card"><h3>With the kit</h3><ul class="ticks">
<li>One board for every video and every channel, from idea to published.</li>
<li>Prompt templates you fill in, then copy into the AI tool you already use.</li>
<li>Titles scored with simple rules, and every point explained.</li>
<li>A spreadsheet becomes a batch of branded pins and a checked bulk-upload CSV.</li>
</ul></div>
</div>
</div></section>

<section class="sec sec-alt" id="tools"><div class="wrap">
<h2>Two tools in one app</h2>
<p class="intro">Real screenshots from the app, using the built-in demo channel.</p>
<div class="feature">
<div class="feature-text"><span class="tag">Tool 1</span><h3>Channel Planner</h3>
<ul class="ticks">
<li><b>Board</b> for every video: Idea → Script → Voice/Avatar → Edit → Thumbnail → Scheduled → Published. As many channels as you like.</li>
<li><b>Prompt builder</b> with three templates (listicle explainer, story/insider reveal, how-to). Edit them or add your own.</li>
<li><b>Description builder</b>: hook, product links, chapters checked against YouTube's chapter rules, disclaimer and hashtags.</li>
<li><b>Title &amp; thumbnail lab</b>: compare three titles, each scored out of 100 with the reasons shown.</li>
<li><b>Shorts planner</b>, calendar, topics bank with a "you already made this" warning, and a weekly review with small trend lines.</li>
</ul></div>
{seq_html('planner', 0)}
</div>
<div class="feature flip">
<div class="feature-text"><span class="tag">Tool 2</span><h3>Pin Factory</h3>
<ul class="ticks">
<li><b>8 pin templates</b> at Pinterest's 2:3 size (1000 × 1500): Bold Headline, Numbered List, Quick Tip, Recipe/Product Card, Quote, Before → After, Money Compare and Checklist.</li>
<li><b>Brand kit</b> per channel: colors, 6 included fonts, your logo or photo, your website and a call-to-action tag.</li>
<li><b>Batch mode</b>: paste rows from Google Sheets or Excel (or upload a CSV) and render every pin at once. Click any pin to fix it.</li>
<li><b>Export</b>: all images in one ZIP plus a Pinterest bulk-upload CSV with your image links, UTM-tagged links, a posting schedule and length checks.</li>
</ul></div>
{seq_html('pins', 0)}
</div>
</div></section>

<section class="sec"><div class="wrap">
<h2>How it works</h2>
<ol class="steps">
<li><h3>Set up your channel</h3><p>Name, niche, colors, the products you link to and your keywords. A demo channel shows every feature filled in.</p></li>
<li><h3>Plan each video</h3><p>Move it across the board, pick the best title, build the script prompt and the description, and plan the Shorts.</p></li>
<li><h3>Promote it on Pinterest</h3><p>Paste your pin ideas, render them in your brand, export the images and the CSV, and upload it in your Pinterest account.</p></li>
</ol>
</div></section>

<section class="sec sec-alt"><div class="wrap">
<h2>A closer look</h2>
<div class="grid2 gallery">{gallery}</div>
</div></section>

<section class="sec"><div class="wrap grid2">
<div><h2>What you get</h2><ul class="ticks">
<li>Lifetime access to the web app (Channel Planner + Pin Factory)</li>
<li>A PDF quick-start guide with your personal access code</li>
<li>A demo channel so you can see every feature filled in</li>
<li>Future updates to the app at the same address</li>
</ul>
<h2 style="margin-top:1.4em">Requirements</h2><ul class="ticks">
<li>A recent Chrome, Edge, Safari or Firefox on a computer, tablet or phone.</li>
<li>Works offline after the first visit; can be installed like an app.</li>
<li>No account, no cloud. Use the built-in backup to keep a copy or move devices.</li>
<li>For Pinterest bulk upload: a free place to host images, such as GitHub Pages (instructions included).</li>
</ul></div>
<div><h2>Who it's for</h2><ul class="ticks">
<li>Creators running one or several faceless or AI-avatar YouTube channels.</li>
<li>People who use Pinterest (or want to) to send viewers to their videos and products.</li>
<li>Anyone who'd rather not pay for several subscriptions to plan and promote.</li>
</ul>
<h2 style="margin-top:1.4em">Who it's not for</h2><ul class="ticks crosses">
<li>You want software that makes the videos, voices or avatars. This kit plans; it doesn't produce footage.</li>
<li>You want something that posts to Pinterest automatically. You upload the CSV yourself.</li>
<li>You need a team workspace synced in the cloud. Data lives on one device at a time.</li>
<li>You're looking for a promise of views or income. Nobody honest can make one.</li>
</ul></div>
</div></section>

<section class="sec sec-alt"><div class="wrap narrow">
<h2>A note from the maker</h2>
<p>The kit started as a tool for a simple problem: planning faceless videos in one place and promoting them on Pinterest without design software or a stack of subscriptions. It's a small, independent product. It does a few jobs carefully, it keeps your data on your device, and it tells you plainly what it doesn't do.</p>
<p>If something is unclear before you buy, try the free tools first — the title scorer uses the same rules as the app.</p>
</div></section>

<section class="sec"><div class="wrap narrow faq">
<h2>FAQ</h2>
{faq}
</div></section>

<section class="sec sec-night" id="price"><div class="wrap">
<div class="price-box">
<p class="kicker">{NAME}</p>
<p class="price">${CFG.PRICE}<small>one-time</small></p>
<ul class="ticks">
<li>Channel Planner + Pin Factory</li>
<li>8 pin templates, batch mode, ZIP + CSV export</li>
<li>Quick-start PDF and demo channel</li>
<li>Future updates at the same address</li>
<li>No subscription, no account</li>
</ul>
<a class="btn btn-primary" href="{buy('landing', 'price')}">Buy the kit — ${CFG.PRICE}</a>
<p class="small">Checkout on Payhip. You get the quick-start PDF with your access code.</p>
</div>
</div></section>

<section class="sec"><div class="wrap">
<h2>Not ready? Start free.</h2>
<div class="grid3">
<a class="card rcard" href="tools/title-scorer/"><span class="chip">Free tool</span><b>YouTube Title Scorer</b><span>{esc(TOOLS['title-scorer']['short'])}</span></a>
<a class="card rcard" href="tools/pinterest-csv-checker/"><span class="chip">Free tool</span><b>Pinterest CSV Checker</b><span>{esc(TOOLS['pinterest-csv-checker']['short'])}</span></a>
<a class="card rcard" href="guides/"><span class="chip">Free guides</span><b>Guides for faceless creators</b><span>Pinterest bulk uploads, titles, thumbnails, Shorts and a weekly workflow.</span></a>
</div>
{free_box('landing', 'starter-pack')}
<div class="btns"><a class="btn btn-primary" href="{buy('landing', 'final')}">Get the kit — ${CFG.PRICE}</a></div>
</div></section>
</main>
""" + footer(0))


# ---------------------------------------------------------------- tools

def tools_index():
    url = KIT + "tools/"
    title = "Free Tools for YouTube & Pinterest Creators"
    desc = "Two free browser tools: score your YouTube titles and check a Pinterest bulk-upload CSV before you upload it. No sign-up, nothing uploaded."
    ld = jsonld({"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": title, "url": url, "description": desc, "publisher": org()},
        crumbs_ld([(NAME, KIT), ("Free tools", url)])]})
    cards = "".join(
        f'<li class="gcard"><a href="{k}/"><span class="chip">Free tool</span><b>{esc(t["name"])}</b><span class="gdesc">{esc(t["short"])}</span><span class="gmeta">Runs in your browser · no sign-up</span></a></li>'
        for k, t in TOOLS.items())
    return (head(title=title, desc=desc, url=url, og=KIT + "og.jpg", og_alt=NAME, depth=1, extra=ld)
            + topbar(1, "tools") + f"""<main id="main" class="wrap">
<header class="art-head" style="padding-top:32px"><p class="kicker">Free tools</p><h1>Free tools for YouTube &amp; Pinterest creators</h1>
<p class="dek">Small, honest tools that run entirely in your browser. Nothing you paste is uploaded.</p></header>
<ul class="ggrid" style="grid-template-columns:repeat(auto-fit,minmax(260px,1fr))">{cards}</ul>
{free_box('tools', 'tools-index')}
{product_box('planner', 'tools', 'tools-index', 1)}
</main>
""" + footer(1))


TITLE_HOWTO = """
<h2>How the score works</h2>
<p>The score is a checklist, not a prediction. It adds up seven simple rules, the same ones the Title &amp; Thumbnail Lab in the Faceless Creator Kit uses, and shows you every point so you can decide for yourself:</p>
<div class="table"><table><thead><tr><th>Rule</th><th>Points</th><th>Why it's there</th></tr></thead><tbody>
<tr><td>Length 40–65 characters</td><td>20</td><td>Long titles get cut off in many places YouTube shows them; very short ones often say too little.</td></tr>
<tr><td>Has a number</td><td>15</td><td>"7 things" or "in 10 minutes" sets a clear expectation.</td></tr>
<tr><td>A curiosity or pain word</td><td>15</td><td>Words like <i>mistake</i>, <i>hidden</i> or <i>why</i> name the problem the video solves.</td></tr>
<tr><td>Strong start</td><td>15</td><td>"In this video…" wastes the first words; lead with the payoff.</td></tr>
<tr><td>At most 2 ALL CAPS words</td><td>10</td><td>One emphasized word can help; a shouting title looks like spam.</td></tr>
<tr><td>No clickbait words</td><td>10</td><td>"Shocking" and "you won't believe" promise more than most videos deliver.</td></tr>
<tr><td>Your keyword</td><td>15</td><td>The phrase people actually search for should be in the title.</td></tr>
</tbody></table></div>
<p>A high score doesn't mean a video will do well, and a lower one isn't automatically bad: a story title without a number can be the right call. Use the reasons, not just the number.</p>
<h2>How to use it in five minutes</h2>
<ol>
<li><b>Write three different angles</b>, not three versions of one sentence: a list ("7 Things…"), a mistake ("The Mistake That…") and a question or how-to.</li>
<li><b>Add your keyword</b> — the two or three words someone would type into YouTube search to find this video.</li>
<li><b>Read the orange and red lines.</b> Fix the cheap ones first: move the payoff to the front, cut filler words, add the number you already have in the video.</li>
<li><b>Check it still sounds like a person wrote it.</b> If a rewrite only exists to tick a box, keep the clearer original.</li>
<li><b>Copy the best title</b> and pair it with thumbnail text that adds something new — 2 to 5 words that don't repeat the title.</li>
</ol>
<h2>Tips for faceless channels</h2>
<p>Without a face on the thumbnail, the title and the thumbnail text carry the whole promise. Be specific about the payoff ("Without a Telescope", "Before You Buy"), keep one idea per title, and make sure the first 30 seconds of the video deliver exactly what the title says. Viewers who feel tricked leave early, and that hurts more than a modest title ever will.</p>
<p>Use the share button to send your three options to a friend or collaborator — the link opens with the same titles filled in. Nothing is stored anywhere except in that link.</p>
"""

CSV_HOWTO = """
<h2>What this checker looks at</h2>
<ul>
<li><b>The header</b> — Pinterest's template is <code>Title, Media URL, Pinterest board, Thumbnail, Description, Link, Publish date, Keywords</code>. Misspelled or extra columns are the most common reason a file is rejected.</li>
<li><b>Lengths</b> — titles up to 100 characters and descriptions up to 500. Longer ones are shortened at a word or sentence break in the corrected file.</li>
<li><b>Media URLs</b> — every pin needs a public, direct link to the image file. Sharing pages from Google Drive, Dropbox or iCloud open a web page, not the image, so Pinterest can't fetch them.</li>
<li><b>Links</b> — the destination must be a full web address starting with https://.</li>
<li><b>Publish dates</b> — the format is <code>YYYY-MM-DDTHH:MM:SS</code> (for example <code>2026-10-12T14:00:00</code>), and the date must be in the future. Common spreadsheet formats like <code>2026-10-12 14:00</code> are converted for you.</li>
<li><b>Duplicates</b> — exact duplicate rows are removed; repeated images or titles are flagged.</li>
<li><b>Boards</b> — you get the list of board names in the file. They must already exist in your account, spelled exactly the same. Names that differ only in capitals or spaces are merged.</li>
<li><b>File size</b> — Pinterest takes up to 200 pins per file; bigger files are split.</li>
</ul>
<h2>How to bulk upload after the check</h2>
<ol>
<li>Use a Pinterest <b>business account</b> (free; you can convert a personal account in settings).</li>
<li>Create every board listed above, with exactly those names.</li>
<li>Open Pinterest, choose <b>Create → Create Pins in bulk</b> and upload the corrected CSV.</li>
<li>Pinterest fetches your images and schedules each pin for its publish date. If a row fails, Pinterest tells you which one — fix that row and upload just the failed rows again.</li>
</ol>
<p>Menus change from time to time; if a button has moved, Pinterest's help center has the current steps.</p>
<h2>Privacy</h2>
<p>The checker runs entirely in your browser. Your file is read on your device and the corrected file is created on your device — nothing is uploaded, stored or tracked. You can even use it offline once the page has loaded.</p>
"""


def tool_page(key):
    t = TOOLS[key]
    url = f"{KIT}tools/{key}/"
    if key == "title-scorer":
        title = "Free YouTube Title Scorer — Compare 3 Titles"
        desc = "Paste up to three YouTube titles and get a score out of 100 with every point explained: length, numbers, keyword, clickbait and more. Free."
        h1 = "YouTube Title Scorer"
        dek = "Paste up to three title ideas. Each gets a score out of 100, and every point is explained — no black box."
        ui = """<div class="tool-ui" id="tool">
<div class="field"><label for="t1">Title A</label><input id="t1" name="t1" type="text" maxlength="150" autocomplete="off" placeholder="e.g. 7 Things You Can See Tonight Without a Telescope"></div>
<div class="field"><label for="t2">Title B <span class="small">(optional)</span></label><input id="t2" name="t2" type="text" maxlength="150" autocomplete="off"></div>
<div class="field"><label for="t3">Title C <span class="small">(optional)</span></label><input id="t3" name="t3" type="text" maxlength="150" autocomplete="off"></div>
<div class="field"><label for="kw">Keyword</label><input id="kw" name="kw" type="text" autocomplete="off" placeholder="e.g. telescope"><p class="hint">The words people would search for. Separate several with commas.</p></div>
<div class="btns"><button type="button" class="btn btn-dark btn-small" id="example">Try an example</button><button type="button" class="btn btn-primary btn-small" id="copy-best" hidden>Copy the best title</button><button type="button" class="btn btn-ghost btn-small" id="share-link">Share these titles</button></div>
<p class="status" id="tool-status" role="status" aria-live="polite"></p>
<div class="results" id="results" aria-live="polite"></div>
</div>"""
        howto, script, feature, related = TITLE_HOWTO, "title-scorer.js", "planner", ["youtube-title-formulas", "youtube-thumbnail-text-rules", "plan-a-faceless-youtube-channel"]
    else:
        title = "Free Pinterest Bulk Upload CSV Checker & Fixer"
        desc = "Check your Pinterest bulk-upload CSV for header, length, URL, date and duplicate errors, then download a corrected file. Free, runs in your browser."
        h1 = "Pinterest CSV Checker"
        dek = "Paste or open your Pinterest bulk-upload CSV. See every problem, the board list, and download a corrected copy — before Pinterest rejects it."
        ui = """<div class="tool-ui" id="tool">
<div class="field"><label for="csv">Your CSV</label><textarea id="csv" name="csv" spellcheck="false" placeholder="Title,Media URL,Pinterest board,Thumbnail,Description,Link,Publish date,Keywords"></textarea><p class="hint">Paste the file's contents, or open the file. It stays on your device.</p></div>
<div class="btns"><label class="file-label">Open a CSV file<input id="file" type="file" accept=".csv,text/csv,text/plain"></label><button type="button" class="btn btn-dark btn-small" id="run">Check it</button><button type="button" class="btn btn-ghost btn-small" id="sample">Load a broken example</button></div>
<p class="status" id="tool-status" role="status" aria-live="polite"></p>
<div id="report" aria-live="polite"></div>
</div>"""
        howto, script, feature, related = CSV_HOWTO, "csv-checker.js", "pins", ["pinterest-bulk-upload-csv", "pinterest-bulk-csv-errors", "host-pinterest-images-github-pages"]
    arts = {a.slug: a for a in ARTS}
    rel = "".join(f'<li><a class="rcard" href="../../guides/{s}/"><span class="chip">{esc(arts[s].cat_label)}</span><b>{esc(arts[s].title)}</b><span>{arts[s].minutes} min read</span></a></li>' for s in related)
    ld = jsonld({"@context": "https://schema.org", "@graph": [
        {"@type": "WebApplication", "name": t["name"], "url": url, "description": desc, "applicationCategory": "UtilitiesApplication",
         "operatingSystem": "Any (runs in the browser)", "isAccessibleForFree": True, "publisher": org(),
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
        crumbs_ld([(NAME, KIT), ("Free tools", KIT + "tools/"), (t["name"], url)])]})
    return (head(title=title, desc=desc, url=url, og=url + "og.jpg", og_alt=t["name"], depth=2, extra=ld)
            + topbar(2, "tools") + f"""<main id="main" class="wrap">
<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../../">{NAME}</a></li><li><a href="../">Free tools</a></li></ol></nav>
<header class="art-head"><p class="kicker">Free tool · runs in your browser</p><h1>{h1}</h1><p class="dek">{dek}</p></header>
{ui}
<section class="cta-band" aria-label="{NAME}">
<h2>{esc(t['kit'])}</h2>
<p>{'The Faceless Creator Kit puts this lab next to your video board, prompt builder, description builder and Shorts planner — for every video, on every channel.' if key == 'title-scorer' else 'The Pin Factory in the Faceless Creator Kit renders a batch of branded pins from your spreadsheet and exports a CSV that already passes these checks: lengths, UTM links, schedule and all.'}</p>
<div class="btns"><a class="btn btn-primary" href="{buy('tool', key)}">Get the kit — ${CFG.PRICE}</a><a class="btn btn-ghost" href="../../#tools">See the app</a></div>
</section>
<div class="prose howto">
{howto}
</div>
{free_box('tool', key)}
<section class="related" aria-labelledby="related"><h2 id="related">Related guides</h2><ul>{rel}</ul></section>
</main>
""" + footer(2, (script,)))


# ---------------------------------------------------------------- guides

class Article:
    def __init__(self, path):
        self.slug = path.stem
        fm, body = split(path.read_text(encoding="utf-8"))
        self.fm, self.md = fm, body
        self.title = fm["title"]
        self.seo_title = fm.get("seo_title") or self.title
        self.description = fm["description"]
        self.keyword = fm["keyword"]
        self.category = fm["category"]
        self.cat_label = CATEGORIES[self.category]
        self.date, self.updated = fm["date"], fm["updated"]
        self.words = len(plain_words(body))
        self.minutes = max(1, math.ceil(self.words / 230))
        self.url = f"{KIT}guides/{self.slug}/"
        self.headings = [re.sub(r"[*_`]", "", h) for h in re.findall(r"^## (.+)$", body, re.M)]

    @property
    def page_title(self):
        s = " | Creator Kit Guides"
        return self.seo_title + s if len(self.seo_title + s) <= 60 else self.seo_title


def load():
    problems = [p for f in all_articles() for p in lint(f)]
    if problems:
        sys.exit("Content problems — fix these first:\n" + "\n".join(problems))
    arts = [Article(f) for f in all_articles()]
    order = {k: i for i, k in enumerate(CATEGORIES)}
    arts.sort(key=lambda a: (-a.updated.toordinal(), order[a.category], a.title))
    return arts


def related(a, pool):
    words = set(re.findall(r"[a-z]{4,}", (a.keyword + " " + a.title).lower()))
    linked = set(re.findall(r"\]\(\.\./([a-z0-9-]+)/\)", a.md))

    def score(b):
        bw = set(re.findall(r"[a-z]{4,}", (b.keyword + " " + b.title).lower()))
        return (3 if b.category == a.category else 0) + len(words & bw) + (1 if b.slug in linked else 0)
    return sorted((b for b in pool if b.slug != a.slug), key=lambda b: (-score(b), b.slug))[:3]


MD = markdown.Markdown(extensions=["tables", "sane_lists", "toc", "fenced_code", "attr_list"],
                       extension_configs={"toc": {"permalink": False, "toc_depth": "2"}})


def render_body(a):
    MD.reset()
    body = MD.convert(a.md)
    toc = [(t["id"], t["name"]) for t in MD.toc_tokens]
    body = body.replace("<table>", '<div class="table"><table>').replace("</table>", "</table></div>")
    body = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" rel="noopener"', body)
    parts = re.split(r"(?=<h2[ >])", body)
    intro, sections = parts[0], parts[1:]
    n = len(sections)
    extra = {}
    extra[min(2, n - 1)] = free_box("guide", a.slug)
    mid = max(3, min(n - 1, (n + 1) // 2 + 1))
    extra[mid] = extra.get(mid, "") + tool_box(a.fm["tool"], 2)
    out = intro + "".join(extra.get(i, "") + s for i, s in enumerate(sections)) + product_box(a.fm["feature"], "guide", a.slug, 2)
    return out, toc


def article_page(a, pool):
    body, toc = render_body(a)
    og = a.url + "og.jpg"
    ld = jsonld({"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "headline": a.title, "description": a.description, "image": [og],
         "datePublished": a.date.isoformat(), "dateModified": a.updated.isoformat(),
         "author": {"@type": "Organization", "name": NAME, "url": KIT}, "publisher": org(),
         "mainEntityOfPage": a.url, "url": a.url, "keywords": a.keyword, "articleSection": a.cat_label,
         "wordCount": a.words, "inLanguage": "en"},
        crumbs_ld([(NAME, KIT), ("Guides", KIT + "guides/"), (a.title, a.url)])]})
    extra = (f'<meta property="article:published_time" content="{a.date.isoformat()}">\n'
             f'<meta property="article:modified_time" content="{a.updated.isoformat()}">\n' + ld)
    toc_html = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in toc)
    rel = "".join(f'<li><a class="rcard" href="../{r.slug}/"><span class="chip">{esc(r.cat_label)}</span><b>{esc(r.title)}</b><span>{r.minutes} min read</span></a></li>'
                  for r in related(a, pool))
    return (head(title=a.page_title, desc=a.description, url=a.url, og=og, og_alt=a.title, depth=2, og_type="article", extra=extra)
            + topbar(2, "guides") + f"""<main id="main" class="wrap">
<nav class="crumbs" aria-label="Breadcrumb"><ol><li><a href="../../">{NAME}</a></li><li><a href="../">Guides</a></li><li><a href="../?c={a.category}">{esc(a.cat_label)}</a></li></ol></nav>
<div class="layout">
<article class="article">
<header class="art-head">
<p class="chip">{esc(a.cat_label)}</p>
<h1>{esc(a.title)}</h1>
<p class="dek">{esc(a.description)}</p>
<p class="meta"><span>Last updated <time datetime="{a.updated.isoformat()}">{fmt_date(a.updated)}</time></span><span>{a.minutes} min read</span>
<button class="share" type="button" data-title="{esc(a.title)}" data-url="{a.url}">Share</button></p>
<p class="share-status" role="status" aria-live="polite"></p>
</header>
<details class="toc toc-m"><summary>On this page</summary><nav aria-label="Table of contents"><ol>{toc_html}</ol></nav></details>
<div class="prose">
{body}</div>
<p class="small">Platforms change their menus and limits from time to time. This guide was checked on {fmt_date(a.updated)}; if something looks different, the platform's own help pages have the current details.</p>
</article>
<nav class="toc toc-d" aria-label="On this page"><p class="toc-h">On this page</p><ol>{toc_html}</ol></nav>
</div>
<section class="related" aria-labelledby="related"><h2 id="related">Related guides</h2><ul>{rel}</ul></section>
</main>
""" + footer(2, ("kit.js",)))


def guides_index(arts):
    url = KIT + "guides/"
    title = "Guides for Faceless YouTube & Pinterest Creators"
    desc = "Free, practical guides for faceless YouTubers: Pinterest bulk uploads, CSV fixes, title formulas, thumbnails, Shorts and a weekly workflow."
    ld = jsonld({"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": title, "url": url, "description": desc, "publisher": org(),
         "mainEntity": {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": a.url} for i, a in enumerate(arts)]}},
        crumbs_ld([(NAME, KIT), ("Guides", url)])]})

    def card(a):
        text = " ".join([a.title, a.description, a.keyword, a.cat_label] + a.headings)
        return (f'<li class="gcard" data-cat="{a.category}" data-text="{esc(text)}"><a href="{a.slug}/"><span class="chip">{esc(a.cat_label)}</span>'
                f'<b>{esc(a.title)}</b><span class="gdesc">{esc(a.description)}</span><span class="gmeta">{a.minutes} min read</span></a></li>')
    starts = [a for a in arts if a.fm.get("start_here")][:3]
    start_cards = "".join(f'<li><a class="rcard" href="{a.slug}/"><span class="chip">{esc(a.cat_label)}</span><b>{esc(a.title)}</b><span>{a.minutes} min read</span></a></li>' for a in starts)
    chips = '<button type="button" class="fchip" data-cat="" aria-pressed="true">All</button>' + "".join(
        f'<button type="button" class="fchip" data-cat="{k}" aria-pressed="false">{esc(v)}</button>' for k, v in CATEGORIES.items())
    return (head(title=title, desc=desc, url=url, og=url + "og.jpg", og_alt="Creator Kit guides", depth=1, extra=ld)
            + topbar(1, "guides") + f"""<main id="main" class="wrap">
<header class="art-head" style="padding-top:32px"><p class="kicker">Free guides</p><h1>Guides for faceless creators</h1>
<p class="dek">Step-by-step help with the unglamorous parts: planning, titles, thumbnails, Shorts, Pinterest bulk uploads and selling a first product. No hype, no income claims.</p>
<form class="search" role="search" action="./" onsubmit="return false"><label for="q">Search the guides</label><input id="q" name="q" type="search" placeholder="e.g. csv, thumbnail, shorts" autocomplete="off"></form>
</header>
<section class="related" aria-labelledby="start"><h2 id="start">Start here</h2><ul>{start_cards}</ul></section>
<section aria-labelledby="all" style="margin-top:36px"><h2 id="all">All guides</h2>
<div class="fchips" role="group" aria-label="Filter by category">{chips}</div>
<p class="count" id="count" role="status" aria-live="polite">{len(arts)} guides</p>
<ul class="ggrid" id="list">{''.join(card(a) for a in arts)}</ul>
<p class="empty" id="empty" hidden>Nothing matches that yet. Try another word, or <a href="./">see all guides</a>.</p>
</section>
<div class="grid2">{tool_box('title-scorer', 1)}{tool_box('pinterest-csv-checker', 1)}</div>
{product_box('planner', 'guide', 'guides-index', 1)}
</main>
""" + footer(1, ("kit.js",)))


# ---------------------------------------------------------------- sitemap

def sitemap_entries():
    """(path relative to the site root, lastmod or None) for every kit page.
    Used by tools/build_guides.py when it writes sitemap.xml."""
    arts = [Article(f) for f in all_articles()]
    last = max(a.updated for a in arts) if arts else None
    out = [("creator-kit/", None), ("creator-kit/tools/", None), ("creator-kit/tools/title-scorer/", None),
           ("creator-kit/tools/pinterest-csv-checker/", None), ("creator-kit/guides/", last)]
    out += [(f"creator-kit/guides/{a.slug}/", a.updated) for a in sorted(arts, key=lambda a: a.slug)]
    return out


# ---------------------------------------------------------------- main

ARTS = []


def main():
    global ARTS
    ARTS = load()
    build_assets()
    pages = {OUT / "index.html": landing(), OUT / "tools" / "index.html": tools_index(),
             OUT / "guides" / "index.html": guides_index(ARTS)}
    for key, t in TOOLS.items():
        pages[OUT / "tools" / key / "index.html"] = tool_page(key)
        write(OUT / "tools" / key / "og.jpg", jpeg(og_card(t["name"], "Free tool")))
    gdir = OUT / "guides"
    live = {a.slug for a in ARTS}
    if gdir.is_dir():
        for old in gdir.iterdir():
            if old.is_dir() and old.name not in live:
                shutil.rmtree(old)
    for a in ARTS:
        pages[gdir / a.slug / "index.html"] = article_page(a, ARTS)
        write(gdir / a.slug / "og.jpg", jpeg(og_card(a.title, a.cat_label + " guide")))
    write(gdir / "og.jpg", jpeg(og_card("Guides for faceless YouTube & Pinterest creators", "Free guides")))
    problems = []
    for path, text in pages.items():
        visible = re.sub(r"<[^>]+>", " ", text)
        problems += lint_text(visible, str(path.relative_to(ROOT)))
        write(path, text)
    if problems:
        sys.exit("Banned wording in built pages:\n" + "\n".join(problems))
    import build_guides  # rebuilds sitemap.xml including the kit pages
    build_guides.write(ROOT / "sitemap.xml", build_guides.sitemap(build_guides.load()))
    print(f"Built creator-kit/: landing, 2 tools, tools index, guides index, {len(ARTS)} articles; sitemap updated.")


if __name__ == "__main__":
    main()
