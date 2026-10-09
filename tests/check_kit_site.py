"""Checks for the Faceless Creator Kit site (creator-kit/). Run from the repo root:

    python3 tests/check_kit_site.py

Every page: title, description, canonical, Open Graph + Twitter tags, one H1,
og:image file exists (1200x630). Internal links and assets resolve. Store
links: every Payhip link equals BUY_URL or FREE_URL from tools/kit_config.py
plus utm_source=kitsite&utm_medium=<page>&utm_campaign=<slug>, and no other
file in the repo hard-codes them. Banned wording (guaranteed, testimonials,
ratings, income claims…) on every page, the launch plan and the pins YAML.
sitemap.xml lists every page. JSON-LD parses and never carries ratings or
reviews. Exits 1 on any problem.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import kit_config as CFG  # noqa: E402
from kit_rules import all_articles, lint, lint_text  # noqa: E402

SITE = "https://plazzers.github.io/links/"
KIT = ROOT / "creator-kit"
problems = []


def fail(where, msg):
    problems.append(f"[{where}] {msg}")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta, self.links, self.srcs, self.ld, self.h1, self.title = {}, [], [], [], 0, ""
        self._in_ld = self._in_title = False
        self.text = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            k = a.get("name") or a.get("property")
            if k:
                self.meta[k] = a.get("content", "")
        elif tag == "link":
            self.meta.setdefault("link:" + a.get("rel", ""), a.get("href", ""))
            if a.get("href"):
                self.srcs.append(a["href"])
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag in ("img", "script", "source") and (a.get("src") or a.get("srcset")):
            self.srcs.append(a.get("src") or a.get("srcset").split()[0])
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self.ld.append("")
        if tag in ("script", "style"):
            self._skip += 1
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_ld = False
        if tag in ("script", "style"):
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_ld:
            self.ld[-1] += data
        elif self._in_title:
            self.title += data
        elif not self._skip:
            self.text.append(data)


def url_of(path):
    return SITE + str(path.parent.relative_to(ROOT)).replace("\\", "/") + "/"


def walk_ld(obj, where):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("aggregateRating", "review", "reviews", "ratingValue", "reviewCount"):
                fail(where, f"JSON-LD carries {k}")
            walk_ld(v, where)
    elif isinstance(obj, list):
        for v in obj:
            walk_ld(v, where)


def check_store_link(href, where):
    for base, kind in ((CFG.BUY_URL, "BUY_URL"), (CFG.FREE_URL, "FREE_URL")):
        if href.split("?")[0] == base.split("?")[0] and href.startswith(base):
            q = parse_qs(urlparse(href).query)
            if q.get("utm_source") != ["kitsite"] or not q.get("utm_medium") or not q.get("utm_campaign"):
                fail(where, f"{kind} link without the right UTM tags: {href}")
            return kind
    fail(where, f"store link that isn't BUY_URL or FREE_URL from tools/kit_config.py: {href}")
    return None


def main():
    pages = sorted(KIT.rglob("index.html"))
    if len(pages) < 27:
        fail("site", f"only {len(pages)} pages (want landing, tools index, 2 tools, guides index, 22 guides)")
    kinds = set()
    for p in pages:
        where = str(p.relative_to(ROOT))
        src = p.read_text(encoding="utf-8")
        pg = Page()
        pg.feed(src)
        url = url_of(p)
        title = pg.title.strip()
        if not title or len(title) > 70:
            fail(where, f"<title> missing or too long ({len(title)})")
        d = pg.meta.get("description", "")
        if not 70 <= len(d) <= 160:
            fail(where, f"description length {len(d)}")
        if pg.meta.get("link:canonical") != url:
            fail(where, f"canonical is {pg.meta.get('link:canonical')}, want {url}")
        for k in ("og:title", "og:description", "og:url", "og:image", "og:type", "twitter:card", "twitter:image"):
            if not pg.meta.get(k):
                fail(where, f"missing meta {k}")
        if pg.meta.get("og:url") != url:
            fail(where, "og:url != canonical")
        og = pg.meta.get("og:image", "")
        if og.startswith(SITE):
            f = ROOT / og[len(SITE):]
            if not f.is_file():
                fail(where, f"og:image file missing: {og}")
            else:
                with Image.open(f) as im:
                    if im.size != (1200, 630):
                        fail(where, f"og:image is {im.size}")
        if pg.h1 != 1:
            fail(where, f"{pg.h1} h1 elements")
        if not re.search(r'<html lang="en">', src):
            fail(where, "missing lang")
        if re.search(r'(src|href)="/(?!/)', src):
            fail(where, "root-absolute path")
        if re.search(r"https?://(?!plazzers\.github\.io|payhip\.com|schema\.org)[^\"' ]+\.(?:js|css|woff2?)", src):
            fail(where, "loads something from another site")
        # links and assets
        for href in pg.links + pg.srcs:
            if href.startswith(("mailto:", "#")):
                continue
            if "payhip.com" in href:
                kinds.add(check_store_link(href, where))
                continue
            if href.startswith("http"):
                if href.startswith(SITE):
                    target = ROOT / urlparse(href).path[len("/links/"):]
                else:
                    continue
            else:
                full = urljoin(url, href)
                target = ROOT / urlparse(full).path[len("/links/"):]
            if target.is_dir() or str(target).endswith("/"):
                target = target / "index.html"
            if not target.exists():
                fail(where, f"broken link: {href}")
        # JSON-LD
        if not pg.ld:
            fail(where, "no JSON-LD")
        for block in pg.ld:
            try:
                walk_ld(json.loads(block), where)
            except json.JSONDecodeError as e:
                fail(where, f"JSON-LD does not parse: {e}")
        if p == KIT / "index.html":
            types = [g.get("@type") for b in pg.ld for g in json.loads(b).get("@graph", [])]
            if "Product" not in types:
                fail(where, "landing page has no Product JSON-LD")
            if not any("payhip.com" in h for h in pg.links):
                fail(where, "landing page has no Buy link")
        # wording
        for prob in lint_text(" ".join(pg.text) + " " + title + " " + d, where):
            problems.append(prob)
        if re.search(r"ratingValue|aggregateRating|★", src):
            fail(where, "rating markup")
    if kinds != {"BUY_URL", "FREE_URL"}:
        fail("site", f"store links used: {kinds} (want both BUY_URL and FREE_URL)")

    # store links only come from the config
    for base in (CFG.BUY_URL, CFG.FREE_URL):
        for f in list((ROOT / "tools").rglob("*")) + list((ROOT / "content" / "kit").rglob("*")) + list((ROOT / "tests").rglob("*")):
            if f.is_file() and f.suffix in (".py", ".js", ".md", ".yaml", ".css", ".html") and f.name not in ("kit_config.py",):
                if base in f.read_text(encoding="utf-8", errors="ignore"):
                    fail(str(f.relative_to(ROOT)), f"hard-codes {base} (use tools/kit_config.py)")
    for f in (ROOT / "tools" / "kit").glob("*.js"):
        if "payhip.com" in f.read_text():
            fail(str(f.relative_to(ROOT)), "Payhip link in a script")

    # articles, launch plan, pins
    for a in all_articles():
        problems.extend(lint(a))
    if len(all_articles()) != 22:
        fail("content/kit", f"{len(all_articles())} articles, want 22")
    plan = KIT / "launch" / "LAUNCH-PLAN.md"
    if not plan.is_file():
        fail("launch", "creator-kit/launch/LAUNCH-PLAN.md is missing")
    else:
        t = plan.read_text(encoding="utf-8")
        problems.extend(lint_text(t, "LAUNCH-PLAN.md"))
        for need in ("LAUNCH30", "Product Hunt", "affiliate", "BUY_URL", "FREE_URL"):
            if need.lower() not in t.lower():
                fail("LAUNCH-PLAN.md", f"doesn't mention {need}")
    problems.extend(lint_text((ROOT / "tools" / "pins_kit.yaml").read_text(encoding="utf-8").split("\npins:", 1)[1], "pins_kit.yaml"))

    # sitemap
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text for e in ET.parse(ROOT / "sitemap.xml").getroot().findall("s:url/s:loc", ns)]
    for p in pages:
        if url_of(p) not in locs:
            fail("sitemap.xml", f"missing {url_of(p)}")
    root_index = (ROOT / "index.html").read_text()
    if 'href="creator-kit/"' not in root_index:
        fail("index.html", "no 'Tools for creators' link")
    for ch in ("walter", "sal"):
        if "creator-kit" in (ROOT / ch / "index.html").read_text():
            fail(f"{ch}/index.html", "links to the creator kit (should only be on the root index)")

    if problems:
        print(f"{len(problems)} problem(s):\n" + "\n".join(problems))
        sys.exit(1)
    print(f"All kit site checks passed: {len(pages)} pages, {len(locs)} sitemap URLs.")


if __name__ == "__main__":
    main()
