"""Content rules for the guide articles (content/walter/*.md, content/sal/*.md).

Shared by tools/build_guides.py (refuses to build broken content) and
tests/check_guides.py (the full check). Run on its own to lint just the
Markdown:  python3 tests/guide_rules.py [file.md ...]
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
TEASERS = ROOT / "content-sources" / "sal" / "copycat-teasers.json"

CATEGORIES = {
    "walter": {"buying": "Buying a house", "seasonal": "Seasonal", "systems": "Systems",
               "older-homes": "Older homes", "habits": "Habits"},
    "sal": {"secrets": "Restaurant secrets", "copycat": "Copycat dishes"},
}
WALTER_PRODUCTS = {"app", "redflag", "manual"}
FREE_SAMPLES = {30, 31, 33}  # recipe numbers marked freeSample in copycat-teasers.json

# Real restaurant / chain names that must never appear on the guide sites.
CHAINS = [
    "Olive Garden", "Red Lobster", "Outback", "Texas Roadhouse", "LongHorn", "Applebee's", "Applebees",
    "Chili's", "TGI Friday", "Cheesecake Factory", "Cracker Barrel", "Panera", "Chipotle Mexican", "Chipotle's",
    "Qdoba", "Moe's", "Taco Bell", "Del Taco", "El Pollo Loco", "Panda Express", "P.F. Chang", "PF Chang",
    "Benihana", "McDonald", "Burger King", "Wendy's", "Five Guys", "In-N-Out", "Shake Shack", "Whataburger",
    "Culver's", "Sonic Drive", "Jack in the Box", "Carl's Jr", "Hardee's", "Arby's", "KFC",
    "Kentucky Fried", "Popeyes", "Chick-fil-A", "Raising Cane", "Zaxby", "Church's Chicken", "Subway",
    "Jersey Mike", "Jimmy John", "Pizza Hut", "Domino's", "Papa John", "Little Caesars", "Papa Murphy",
    "Buffalo Wild Wings", "Wingstop", "Hooters", "Denny's", "IHOP", "Waffle House", "Perkins",
    "Bob Evans", "Golden Corral", "Red Robin", "Ruby Tuesday", "Cheddar's", "BJ's Restaurant",
    "Fazoli", "Buca di Beppo", "Macaroni Grill", "Old Spaghetti Factory", "Bertucci", "Maggiano",
    "Carrabba", "Bonefish", "Ruth's Chris", "Morton's", "Capital Grille", "Fogo de Ch", "Starbucks",
    "Dunkin", "Dairy Queen", "Steak 'n Shake", "Steak n Shake", "Long John Silver", "Bojangles",
    "Sbarro", "Noodles & Company", "First Watch", "Smokey Bones", "Famous Dave", "Logan's Roadhouse",
]
# Spec-mandated words plus invented-biography phrases (honesty rule, SPEC_V4 §4).
BANNED = [
    r"licensed inspector", r"michelin", r"guaranteed?", r"\bcure[ds]?\b", r"\bcuring\b",
    r"\bforty[- ]years?\b", r"\b\d{2}[- ]years? (?:as|in (?:the|my)|of experience|in restaurant|running)",
    r"\b\d{2}-year[- ](?:restaurant|veteran|inspector|career)", r"\byears as an? (?:home )?inspector",
    r"\bI(?:'ve| have)? inspected\b", r"\bas an? (?:home )?inspector\b", r"\bin my (?:career|restaurant|kitchen in)",
    r"\bmy (?:own )?restaurant\b", r"\bwhen I ran\b", r"\bran (?:my|the) kitchen", r"\bmy grandkids?\b",
    r"\bmy (?:wife|late wife)\b", r"\bAngela\b", r"\bfrom Romano's\b", r"\bMilan\b", r"\bNew Jersey\b",
    r"\bstarred\b", r"\btestimonial", r"\b\d(?:\.\d)? ?(?:out of 5|stars?)\b", r"\bcertified (?:master )?inspector",
]
# Sal copycat articles that are not free samples must not carry recipe quantities.
QUANTITY = re.compile(
    r"(?:\b\d+(?:[./]\d+)?|½|¼|¾|⅓|\bone|\btwo|\bthree|\bhalf an?)\s*(?:-\s*)?"
    r"(?:cups?|tbsps?|tablespoons?|tsps?|teaspoons?|oz\b|ounces?|lbs?\b|pounds?|grams?|g\b|ml\b|"
    r"cloves?|sticks? of butter|cans? of|packets?|pinch(?:es)?|sprigs?)\b", re.I)

REQUIRED = ["title", "description", "keyword", "category", "date", "updated"]
MIN_WORDS, MAX_WORDS = 900, 1600


def teasers():
    return {r["num"]: r for r in json.loads(TEASERS.read_text())["recipes"]}


def split(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("missing YAML front matter")
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def plain_words(body):
    t = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    t = re.sub(r"^\[\[[\w-]+\]\]$", " ", t, flags=re.M)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#*_>`|]", " ", t)
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.\-]*", t)


def lint(path):
    """Return a list of problems for one Markdown article."""
    path = Path(path)
    channel = path.parent.name
    errs = []
    try:
        fm, body = split(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [f"{path.name}: {e}"]
    e = lambda m: errs.append(f"{channel}/{path.name}: {m}")  # noqa: E731
    slug = path.stem
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        e("file name must be a lowercase-hyphen slug")
    for k in REQUIRED:
        if not fm.get(k):
            e(f"missing front matter: {k}")
    title, desc = str(fm.get("title", "")), str(fm.get("description", ""))
    seo = str(fm.get("seo_title") or title)
    if len(seo) > 60:
        e(f"<title> text is {len(seo)} chars (> 60); shorten title or add seo_title")
    if len(title) > 75:
        e(f"title is {len(title)} chars (> 75)")
    if not (70 <= len(desc) <= 155):
        e(f"description is {len(desc)} chars (want 70-155)")
    if fm.get("category") not in CATEGORIES.get(channel, {}):
        e(f"category {fm.get('category')!r} not in {list(CATEGORIES.get(channel, {}))}")
    for k in ("date", "updated"):
        if k in fm and not isinstance(fm[k], date):
            e(f"{k} must be a YYYY-MM-DD date")
    words = len(plain_words(body))
    if not (MIN_WORDS <= words <= MAX_WORDS):
        e(f"{words} words (want {MIN_WORDS}-{MAX_WORDS})")
    if re.search(r"^# ", body, re.M):
        e("body must not contain an H1 (# ) — the title is the H1")
    if len(re.findall(r"^## ", body, re.M)) < 3:
        e("needs at least 3 ## sections")
    if re.search(r"payhip\.com", body, re.I):
        e("no Payhip links in the body — product boxes are added by the build")
    if re.search(r"\]\(/", body):
        e("use relative links (../slug/), not root-absolute ones")

    text = title + "\n" + desc + "\n" + body + "\n" + yaml.safe_dump(fm.get("sources") or [])
    for pat in BANNED:
        m = re.search(pat, text, re.I)
        if m:
            e(f"banned wording: {m.group(0)!r}")
    for name in CHAINS:
        if re.search(r"(?<![A-Za-z])" + re.escape(name) + r"(?![a-z])", text, re.I if len(name) > 4 else 0):
            e(f"names a real restaurant chain: {name!r}")

    srcs = fm.get("sources") or []
    if not isinstance(srcs, list) or any(not (isinstance(s, dict) and s.get("title") and str(s.get("url", "")).startswith("https://")) for s in srcs):
        e("sources must be a list of {title, url (https://...)}")

    if channel == "walter":
        if fm.get("product") not in WALTER_PRODUCTS:
            e(f"product must be one of {sorted(WALTER_PRODUCTS)}")
        if re.search(r"\$\s?\d", body):
            e("no prices in Walter's articles")
        if not srcs:
            e("Walter articles need at least one authoritative source")
    if channel == "sal" and fm.get("category") == "copycat":
        rec = teasers().get(fm.get("recipe"))
        if not rec:
            e("copycat articles need recipe: <number from copycat-teasers.json>")
        free = bool(fm.get("free_sample"))
        if free and fm.get("recipe") not in FREE_SAMPLES:
            e("free_sample is only allowed for recipes marked freeSample (30, 31, 33)")
        if free and "[[free-sample]]" not in body:
            e("free_sample articles need a [[free-sample]] line where the recipe goes")
        if not free:
            if "[[free-sample]]" in body:
                e("[[free-sample]] used without free_sample: true")
            for m in QUANTITY.finditer(body):
                e(f"looks like a recipe quantity (paid content stays out): {m.group(0)!r}")
        if rec and rec.get("freeSample") is not True and any(k in rec for k in ("ingredients", "steps")):
            e("teaser data unexpectedly has full recipe fields")
    return errs


def all_articles():
    return sorted(CONTENT.glob("walter/*.md")) + sorted(CONTENT.glob("sal/*.md"))


if __name__ == "__main__":
    files = [Path(a) for a in sys.argv[1:]] or all_articles()
    problems = [p for f in files for p in lint(f)]
    for f in files:
        try:
            print(f"{f.parent.name}/{f.name}: {len(plain_words(split(f.read_text())[1]))} words")
        except Exception:  # noqa: BLE001
            pass
    print("\n".join(problems) if problems else f"OK: {len(files)} article(s), no problems.")
    sys.exit(1 if problems else 0)
