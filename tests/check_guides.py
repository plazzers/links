"""Checks for the guide sites (SPEC_V4_GUIDE_SITES.md §6). Run after the build:

    python3 tools/build_guides.py && python3 tests/check_guides.py

Content: front matter, title/description lengths, 900-1,600 words, banned words
and real chain names (tests/guide_rules.py). Built site: every internal link
resolves, Payhip links are exact and carry utm_source=guides&utm_medium=article&
utm_campaign=<slug>, sitemap lists every page, JSON-LD parses (Article, never
Recipe), feeds parse, share images are 1200x630, only the 3 free samples carry
a full recipe. Exits 1 on any problem.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_rules import BANNED, CHAINS, CONTENT, ROOT, all_articles, lint, split, teasers  # noqa: E402

SITE = "https://plazzers.github.io/links/"
PAYHIP = {
    "walter": {"hiIm1", "OZeda", "HAfRF", "ABaxT"},
    "sal": {"dnY7F", "xM6XQ", "MQDaN", "Lv425"},
}
WALTER_PRODUCT = {"app": "OZeda", "redflag": "HAfRF", "manual": "ABaxT"}
DISCLAIMER = {
    "walter": "Educational content. Not a substitute for a professional inspection of your property.",
    "sal": "Recipes are inspired by popular restaurant dishes. Not affiliated with or endorsed by any restaurant.",
}
FREE_SLUGS = {"sunday-marinara-sauce", "garlic-butter-sauce", "buttermilk-ranch-dressing"}
problems = []


def fail(where, msg):
    problems.append(f"[{where}] {msg}")


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links, self.srcs, self.ld, self.meta, self.text = [], [], [], {}, []
        self.title, self._in, self._buf, self.h1 = "", None, "", 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag in ("img", "script", "link") and (a.get("src") or (tag == "link" and a.get("href"))):
            if tag == "link" and a.get("rel") in ("canonical", "alternate"):
                pass
            else:
                self.srcs.append(a.get("src") or a.get("href"))
        if tag == "meta":
            k = a.get("name") or a.get("property")
            if k:
                self.meta[k] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.meta["canonical"] = a.get("href")
        if tag == "h1":
            self.h1 += 1
        if tag == "title" or (tag == "script" and a.get("type") == "application/ld+json"):
            self._in, self._buf = tag, ""
        elif tag in ("script", "style"):
            self._in = "skip"

    def handle_endtag(self, tag):
        if self._in == "title" and tag == "title":
            self.title = self._buf
        elif self._in == "script" and tag == "script":
            self.ld.append(self._buf)
        if tag in ("title", "script", "style"):
            self._in = None

    def handle_data(self, data):
        if self._in in ("title", "script"):
            self._buf += data
        elif self._in is None:
            self.text.append(data)


def resolve(page_path, href):
    """Map a relative href on page_path to a file in the repo (None = external)."""
    u = urlparse(href)
    if u.scheme in ("http", "https"):
        if href.startswith(SITE):
            rel = href[len(SITE):].split("#")[0].split("?")[0]
            p = ROOT / rel
        else:
            return None
    elif u.scheme in ("mailto", "tel") or href.startswith("#"):
        return None
    else:
        p = (page_path.parent / u.path).resolve() if u.path else page_path
    if p.is_dir() or str(p).endswith("/"):
        p = p / "index.html"
    return p


def check_page(path, where, campaign, channel):
    html = path.read_text(encoding="utf-8")
    pg = Page(html)
    if (pg.h1 != 1):
        fail(where, f"{pg.h1} h1 elements")
    if not pg.title or len(pg.title) > 60:
        fail(where, f"<title> {len(pg.title)} chars: {pg.title!r}")
    desc = pg.meta.get("description", "")
    if not desc or len(desc) > 155:
        fail(where, f"meta description {len(desc)} chars")
    for k in ("canonical", "og:title", "og:description", "og:url", "og:image", "twitter:card", "twitter:image"):
        if not pg.meta.get(k):
            fail(where, f"missing meta {k}")
    want_url = SITE + str(path.parent.relative_to(ROOT)).replace("\\", "/") + "/"
    if pg.meta.get("canonical") != want_url or pg.meta.get("og:url") != want_url:
        fail(where, f"canonical/og:url {pg.meta.get('canonical')} != {want_url}")
    og = resolve(path, pg.meta.get("og:image", ""))
    if not og or not og.exists():
        fail(where, f"og:image missing: {pg.meta.get('og:image')}")
    elif Image.open(og).size != (1200, 630):
        fail(where, f"og:image is {Image.open(og).size}")
    # JSON-LD
    types = []
    for raw in pg.ld:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            fail(where, f"JSON-LD does not parse: {e}")
            continue
        for node in data.get("@graph", [data]):
            types.append(node.get("@type"))
    if not types:
        fail(where, "no JSON-LD")
    if "Recipe" in types:
        fail(where, "uses Recipe schema (spec: Article only)")
    # links + assets resolve
    for href in pg.links + pg.srcs:
        target = resolve(path, href)
        if target is not None and not target.exists():
            fail(where, f"broken link: {href}")
    # Payhip: exact codes + utm
    for href in pg.links:
        if "payhip.com" not in href:
            continue
        u = urlparse(href)
        m = re.fullmatch(r"/b/(\w+)", u.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.scheme != "https" or u.netloc != "payhip.com" or not m or m.group(1) not in PAYHIP[channel]:
            fail(where, f"unexpected Payhip link {href}")
        if q != {"utm_source": "guides", "utm_medium": "article", "utm_campaign": campaign}:
            fail(where, f"Payhip link without exact utm (campaign {campaign}): {href}")
    # wording on the page
    text = re.sub(r"\s+", " ", " ".join(pg.text))
    for pat in BANNED:
        m = re.search(pat, text, re.I)
        if m:
            fail(where, f"banned wording on page: {m.group(0)!r}")
    for name in CHAINS:
        if re.search(r"(?<![A-Za-z])" + re.escape(name) + r"(?![a-z])", text, re.I if len(name) > 4 else 0):
            fail(where, f"chain name on page: {name}")
    if DISCLAIMER[channel] not in text:
        fail(where, "disclaimer missing")
    if re.search(r"\b(?:review|rating)s?\b.*\b\d(?:\.\d)? ?/ ?5\b", text, re.I) or '"aggregateRating"' in html:
        fail(where, "looks like a rating")
    return pg, html, text


def main():
    for f in all_articles():
        for p in lint(f):
            fail("content", p)
    arts = {"walter": sorted(CONTENT.glob("walter/*.md")), "sal": sorted(CONTENT.glob("sal/*.md"))}
    for ch, files in arts.items():
        if len(files) != 30:
            fail(ch, f"{len(files)} articles (want 30)")
    sal_cats = [split(f.read_text())[0].get("category") for f in arts["sal"]]
    if sal_cats.count("secrets") != 12 or sal_cats.count("copycat") != 18:
        fail("sal", f"want 12 secrets + 18 copycat, got {sal_cats.count('secrets')} + {sal_cats.count('copycat')}")

    pages = []
    rec = teasers()
    for ch, files in arts.items():
        for f in files:
            fm, _ = split(f.read_text())
            slug = f.stem
            path = ROOT / ch / "guides" / slug / "index.html"
            where = f"{ch}/{slug}"
            if not path.exists():
                fail(where, "page not built (run tools/build_guides.py)")
                continue
            pages.append(path)
            pg, html, text = check_page(path, where, slug, ch)
            codes = {re.search(r"/b/(\w+)", h).group(1) for h in pg.links if "payhip.com/b/" in h}
            free_code = "hiIm1" if ch == "walter" else "dnY7F"
            if free_code not in codes:
                fail(where, "free PDF box missing")
            if ch == "walter" and WALTER_PRODUCT[fm["product"]] not in codes:
                fail(where, "product box missing")
            if ch == "walter" and fm.get("house_age_tool") and "../../house-age/" not in pg.links:
                fail(where, "house-age tool link missing")
            if ch == "sal" and "../../restaurant-or-home/" not in pg.links:
                fail(where, "calculator link missing")
            if ch == "sal" and fm["category"] == "copycat":
                need = {"xM6XQ", "MQDaN"} | ({"Lv425"} if fm.get("italian") else set())
                if not need <= codes:
                    fail(where, f"dish boxes missing: {sorted(need - codes)}")
            yt = "https://www.youtube.com/@WaltersHomeCheck" if ch == "walter" else "https://www.youtube.com/@ChefSalRomano"
            if yt not in pg.links:
                fail(where, "Watch on YouTube missing")
            types = [n.get("@type") for raw in pg.ld for n in json.loads(raw).get("@graph", [json.loads(raw)])]
            if "Article" not in types or "BreadcrumbList" not in types:
                fail(where, f"JSON-LD types {types}")
            if not re.search(r"Last updated <time datetime=", html) or "min read" not in text:
                fail(where, "last-updated / reading time missing")
            if html.count('class="rcard"') != 3:
                fail(where, "want 3 related articles")
            if 'class="author"' not in html:
                fail(where, "author box missing")
            has_recipe = 'class="recipe"' in html
            if has_recipe != (slug in FREE_SLUGS):
                fail(where, "full recipe card on a page that is not a free sample" if has_recipe else "free sample card missing")
            if has_recipe and "Free from Sal's Restaurant Copycat Cookbook" not in text:
                fail(where, "free sample not labelled")
            # paid-recipe guard: teaser ingredient lines with amounts must not leak into any page
            for r in rec.values():
                if r.get("freeSample"):
                    continue
                for ing in r.get("ingredientNames", []):
                    if re.search(r"\d", ing) and len(ing) > 12 and ing in text:
                        fail(where, f"teaser ingredient line with amounts on page: {ing!r}")

    for ch in ("walter", "sal"):
        for sub, campaign in (("guides", "guides-index"), ("about", "about")):
            path = ROOT / ch / sub / "index.html"
            if not path.exists():
                fail(ch, f"{sub}/ not built")
                continue
            pages.append(path)
            check_page(path, f"{ch}/{sub}", campaign, ch)
        # search index + feed
        try:
            data = json.loads((ROOT / ch / "guides" / "search.json").read_text())
            if sorted(d["slug"] for d in data) != sorted(f.stem for f in arts[ch]):
                fail(ch, "search.json does not list every article")
        except Exception as e:  # noqa: BLE001
            fail(ch, f"search.json: {e}")
        try:
            items = ET.parse(ROOT / ch / "guides" / "feed.xml").getroot().findall("./channel/item")
            if len(items) != len(arts[ch]):
                fail(ch, f"feed.xml has {len(items)} items")
        except ET.ParseError as e:
            fail(ch, f"feed.xml does not parse: {e}")
        # link page button + tool strip
        if 'href="guides/"' not in (ROOT / ch / "index.html").read_text():
            fail(ch, "link page has no Read the guides button")
        tool = {"walter": "house-age", "sal": "restaurant-or-home"}[ch]
        if "Related guides" not in (ROOT / ch / tool / "index.html").read_text():
            fail(ch, "tool has no Related guides strip")

    # sitemap: parses, every URL exists, every page is listed
    try:
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        locs = [e.text for e in ET.parse(ROOT / "sitemap.xml").getroot().findall("s:url/s:loc", ns)]
    except (ET.ParseError, FileNotFoundError) as e:
        fail("sitemap", str(e))
        locs = []
    if len(set(locs)) != len(locs):
        fail("sitemap", "duplicate URLs")
    for loc in locs:
        if not loc.startswith(SITE) or not (ROOT / loc[len(SITE):] / "index.html").exists():
            fail("sitemap", f"URL has no page: {loc}")
    listed = {ROOT / loc[len(SITE):] / "index.html" for loc in locs}
    every = [p for p in ROOT.rglob("index.html")
             if not any(part in {"node_modules", ".git", "pins", "docs", "content-sources"} for part in p.relative_to(ROOT).parts)]
    for p in every:
        if p not in listed:
            fail("sitemap", f"page missing from sitemap: {p.relative_to(ROOT)}")
    robots = (ROOT / "robots.txt").read_text() if (ROOT / "robots.txt").exists() else ""
    if f"Sitemap: {SITE}sitemap.xml" not in robots:
        fail("robots.txt", "missing or has no Sitemap line")

    n = len(pages)
    if problems:
        print(f"{len(problems)} problem(s):\n" + "\n".join(problems))
        sys.exit(1)
    print(f"All guide checks passed: {n} pages, {len(locs)} sitemap URLs.")


if __name__ == "__main__":
    main()
