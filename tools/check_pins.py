"""Checks the output of tools/make_pins.py. Run from the repo root:

    python3 tools/check_pins.py

Prints every problem it finds and exits with status 1 if there are any.
Checks: pin images (size, format, color profile, file size), both bulk CSVs
(encoding, header, quoting, lengths, URLs, utm params, publish schedule) and
the content rules (no restaurant brand names, no repair prices on Walter's
pins, at most 10 Walter pins mention a product, no health claims).
"""
import csv
import io
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from PIL import Image, ImageCms

ROOT = Path(__file__).resolve().parent.parent
PINS = ROOT / "pins"
SITE = "https://plazzers.github.io/links/"
HEADER = ["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"]
START = datetime(2026, 10, 10)
SLOTS = (13, 17, 21)
LINK_BASES = {
    "walter": {SITE + "walter/", SITE + "walter/house-age/"},
    "sal": {SITE + "sal/", SITE + "sal/restaurant-or-home/"},
}
BRANDS = [
    "olive garden", "red lobster", "outback", "texas roadhouse", "longhorn", "chipotle", "qdoba",
    "panda express", "p\\.?f\\.? chang", "chick-fil-a", "mcdonald", "wendy's", "burger king", "ihop",
    "denny's", "applebee", "chili's", "buffalo wild wings", "wingstop", "cheesecake factory",
    "taco bell", "popeyes", "kfc", "a\\.?1 sauce", "hidden valley", "zuppa toscana", "cheddar bay",
    "bloomin", "five guys", "shake shack", "in-n-out", "waffle house", "cracker barrel", "carrabba",
    "maggiano", "benihana", "on the border", "panera", "domino", "pizza hut", "papa john",
    "starbucks", "dunkin", "arby", "culver", "raising cane", "hooters", "tgi friday",
    "ruby tuesday", "red robin", "perkins", "bob evans", "golden corral", "cheddar's", "smokey bones",
]
HEALTH = ["healthy", "healthier", "detox", "weight loss", "lose weight", "immunity", "medical", "diabetes",
          "cholesterol", "superfood", "anti-inflammatory"]

problems = []


def bad(msg):
    problems.append(msg)


def text_of(p):
    parts = [str(p.get(k, "")) for k in ("kicker", "headline", "body", "sub", "quote", "title", "description", "tag")]
    parts += [str(i) for i in p.get("items", [])] + [str(k) for k in p.get("keywords", [])]
    return " ".join(parts)


def check_channel(channel):
    data = yaml.safe_load((ROOT / "tools" / f"pins_{channel}.yaml").read_text(encoding="utf-8"))["pins"]
    slugs = [p["slug"] for p in data]
    for s, n in Counter(slugs).items():
        if n > 1:
            bad(f"{channel}: slug used twice: {s}")
    if len(data) != 60:
        bad(f"{channel}: {len(data)} pins in the YAML, expected 60")

    # content rules
    for p in data:
        t = text_of(p).lower()
        for b in BRANDS:
            if re.search(r"\b" + b, t):
                bad(f"{channel}/{p['slug']}: restaurant brand name '{b}'")
        for h in HEALTH:
            if re.search(r"\b" + h + r"\b", t):
                bad(f"{channel}/{p['slug']}: possible health claim '{h}'")
        if channel == "walter" and "$" in t:
            bad(f"walter/{p['slug']}: a price ($) on a Walter pin")
    if channel == "walter":
        mentions = [p["slug"] for p in data if p.get("product")]
        named = [p["slug"] for p in data
                 if re.search(r"Weekend Home Check|Before the First Freeze|Red Flag Checklist|Home Check Manual|Home Check App",
                              p["description"])]
        if len(mentions) > 10:
            bad(f"walter: {len(mentions)} pins mention a product (max 10)")
        for s in set(named) - set(mentions):
            bad(f"walter/{s}: mentions a product but has no 'product: true'")
        counts = Counter(p["type"] for p in data)
        want = {"quick": 20, "buyer": 15, "older": 12, "seasonal": 8, "list": 5}
        if counts != Counter(want):
            bad(f"walter: content mix {dict(counts)} != {want}")
    else:
        counts = Counter(p["type"] for p in data)
        want = {"recipe": 33, "trick": 16, "money": 11}
        if counts != Counter(want):
            bad(f"sal: content mix {dict(counts)} != {want}")

    # images
    folder = PINS / channel
    files = sorted(folder.glob("*.jpg"))
    expected = {f"{i:03d}-{s}.jpg" for i, s in enumerate(slugs, 1)}
    if {f.name for f in files} != expected:
        bad(f"{channel}: image files don't match the YAML "
            f"(missing {sorted(expected - {f.name for f in files})[:3]}, extra {sorted({f.name for f in files} - expected)[:3]})")
    for f in files:
        size = f.stat().st_size
        with Image.open(f) as im:
            if im.format != "JPEG" or im.size != (1000, 1500) or im.mode != "RGB":
                bad(f"{f.name}: {im.format} {im.size} {im.mode}, expected JPEG 1000x1500 RGB")
            icc = im.info.get("icc_profile")
            desc = ImageCms.getProfileDescription(ImageCms.ImageCmsProfile(io.BytesIO(icc))) if icc else ""
            if "sRGB" not in desc:
                bad(f"{f.name}: no sRGB color profile")
        if size >= 350_000:
            bad(f"{f.name}: {size // 1024} KB (max 350 KB)")

    # CSV
    path = PINS / f"pinterest-bulk-{channel}.csv"
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        bad(f"{path.name}: not UTF-8 ({e})")
        return
    if raw.startswith(b"\xef\xbb\xbf"):
        bad(f"{path.name}: has a byte-order mark")
    rows = list(csv.reader(io.StringIO(text, newline="")))
    if rows[0] != HEADER:
        bad(f"{path.name}: header is {rows[0]}")
    body = rows[1:]
    if len(body) != 60:
        bad(f"{path.name}: {len(body)} rows, expected 60")
    # every field quoted: re-writing with QUOTE_ALL must give the same text
    buf = io.StringIO()
    csv.writer(buf, quoting=csv.QUOTE_ALL).writerows(rows)
    if buf.getvalue() != text:
        bad(f"{path.name}: not every field is quoted the standard way")
    dates = []
    for n, r in enumerate(body, 2):
        if len(r) != 8:
            bad(f"{path.name} line {n}: {len(r)} columns")
            continue
        title, media, board, thumb, desc, link, date, kw = r
        where = f"{path.name} line {n}"
        if not title or len(title) > 100:
            bad(f"{where}: title length {len(title)}")
        if not desc or len(desc) > 500:
            bad(f"{where}: description length {len(desc)}")
        if not board:
            bad(f"{where}: no board")
        if thumb:
            bad(f"{where}: Thumbnail should be empty")
        prefix = SITE + f"pins/{channel}/"
        if not media.startswith(prefix) or not (folder / media[len(prefix):]).is_file():
            bad(f"{where}: Media URL doesn't point to a pin in the repo: {media}")
        base, _, query = link.partition("?")
        slug = media[len(prefix):-4].split("-", 1)[-1]
        if base not in LINK_BASES[channel]:
            bad(f"{where}: link goes to {base}")
        if query != f"utm_source=pinterest&utm_medium=pin&utm_campaign={slug}":
            bad(f"{where}: link utm params are '{query}'")
        k = [x.strip() for x in kw.split(",")]
        if not 5 <= len(k) <= 8 or not all(k):
            bad(f"{where}: {len(k)} keywords")
        try:
            dt = datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
            dates.append(dt)
        except ValueError:
            bad(f"{where}: publish date '{date}' is not ISO 8601 (YYYY-MM-DDTHH:MM:SS)")
    if dates:
        if dates != sorted(dates) or len(set(dates)) != len(dates):
            bad(f"{path.name}: publish dates not ascending and unique")
        want = [START + timedelta(days=i // 3, hours=SLOTS[i % 3]) for i in range(len(dates))]
        if dates != want:
            bad(f"{path.name}: publish dates aren't 3 a day at 13/17/21 UTC from 2026-10-10")
        if not desc_ok_cta(body):
            bad(f"{path.name}: some descriptions don't end with a call to action")
    # no two neighbours from the same type + topic
    by_file = {f"{i:03d}-{p['slug']}.jpg": p for i, p in enumerate(data, 1)}
    seq = [by_file.get(r[1].rsplit("/", 1)[-1]) for r in body]
    same = sum(1 for a, b in zip(seq, seq[1:]) if a and b and a["type"] == b["type"] and a.get("topic") == b.get("topic"))
    if same:
        bad(f"{path.name}: {same} back-to-back pins with the same type and topic")
    print(f"{channel}: {len(files)} images, {len(body)} CSV rows, "
          f"largest image {max(f.stat().st_size for f in files) // 1024} KB, "
          f"longest title {max(len(r[0]) for r in body)}, longest description {max(len(r[4]) for r in body)}, "
          f"dates {body[0][6]} .. {body[-1][6]}")


def desc_ok_cta(body):
    """The last sentence of each description should point somewhere (a soft CTA)."""
    words = ("Walter", "Sal", "page", "tool", "calculator", "Cookbook", "checklist", "Checklist", "Mangia")
    for r in body:
        last = re.split(r"(?<=[.!?])\s+", r[4].strip())[-1]
        if not any(w in last for w in words):
            return False
    return True


if __name__ == "__main__":
    for ch in ("walter", "sal"):
        check_channel(ch)
    for f in ("index.html", "contact-walter.jpg", "contact-sal.jpg"):
        if not (PINS / f).is_file():
            bad(f"pins/{f} is missing")
    gallery = (PINS / "index.html").read_text(encoding="utf-8") if (PINS / "index.html").is_file() else ""
    if 'name="robots" content="noindex' not in gallery:
        bad("pins/index.html has no noindex robots tag")
    if problems:
        print(f"\n{len(problems)} problem(s):")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    print("All checks passed.")
