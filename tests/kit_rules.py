"""Content rules for the Faceless Creator Kit site (content/kit/*.md and the
built pages under creator-kit/).

Shared by tools/build_kit_site.py (refuses to build broken content) and
tests/check_kit_site.py. Lint just the Markdown:
    python3 tests/kit_rules.py [content/kit/file.md ...]
"""
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guide_rules import plain_words, split  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "kit"

CATEGORIES = {"pinterest": "Pinterest", "youtube": "YouTube", "workflow": "Workflow", "selling": "Selling"}
TOOLS = {"title-scorer", "pinterest-csv-checker"}
FEATURES = {"planner", "pins"}
REQUIRED = ["title", "description", "keyword", "category", "date", "updated", "tool", "feature"]
MIN_WORDS, MAX_WORDS = 900, 1500

# Honesty rules (SPEC_V5): no fake social proof, ratings, user counts, income
# claims, "guaranteed", invented credentials.
BANNED = [
    r"guarantee", r"testimonial", r"michelin", r"licensed inspector",
    r"\b\d(?:\.\d)? ?(?:out of 5|stars?)\b", r"\brated\b", r"\bratings?\b", r"\breviews? from\b",
    r"\b(?:loved|trusted|used) by\b", r"\bjoin (?:over |more than )?\d", r"\b\d[\d,.]*\+? (?:creators|users|customers|buyers|youtubers)\b",
    r"\bthousands of (?:creators|users|customers|buyers)\b", r"\b(?:six|seven)[- ]figures?\b",
    r"\$\s?\d[\d,.]*k?\s*(?:/|per|a|an|every)\s*(?:month|mo|day|week|year)\b", r"\bpassive income\b",
    r"\bmake money fast\b", r"\bget rich\b", r"\bquit your (?:day )?job\b", r"\bovernight\b",
    r"\bgo viral\b", r"\bexplode your\b", r"\bcase study\b", r"\bas seen on\b", r"\bbest[- ]selling\b",
    r"\b#1\b", r"\bnumber one\b", r"\brisk[- ]free\b",
]


def lint_text(text, where):
    errs = []
    for pat in BANNED:
        m = re.search(pat, text, re.I)
        if m:
            errs.append(f"{where}: banned wording {m.group(0)!r}")
    return errs


def lint(path):
    path = Path(path)
    errs = []
    try:
        fm, body = split(path.read_text(encoding="utf-8"))
    except Exception as ex:  # noqa: BLE001
        return [f"kit/{path.name}: {ex}"]
    e = lambda m: errs.append(f"kit/{path.name}: {m}")  # noqa: E731
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", path.stem):
        e("file name must be a lowercase-hyphen slug")
    for k in REQUIRED:
        if not fm.get(k):
            e(f"missing front matter: {k}")
    title, desc = str(fm.get("title", "")), str(fm.get("description", ""))
    seo = str(fm.get("seo_title") or title)
    if len(seo) > 60:
        e(f"<title> text is {len(seo)} chars (> 60); shorten title or add seo_title")
    if len(title) > 80:
        e(f"title is {len(title)} chars (> 80)")
    if not (70 <= len(desc) <= 155):
        e(f"description is {len(desc)} chars (want 70-155)")
    if fm.get("category") not in CATEGORIES:
        e(f"category must be one of {list(CATEGORIES)}")
    if fm.get("tool") not in TOOLS:
        e(f"tool must be one of {sorted(TOOLS)}")
    if fm.get("feature") not in FEATURES:
        e(f"feature must be one of {sorted(FEATURES)}")
    for k in ("date", "updated"):
        if k in fm and not isinstance(fm[k], date):
            e(f"{k} must be a YYYY-MM-DD date")
    words = len(plain_words(body))
    if not (MIN_WORDS <= words <= MAX_WORDS):
        e(f"{words} words (want {MIN_WORDS}-{MAX_WORDS})")
    if re.search(r"^# ", body, re.M):
        e("body must not contain an H1 (# )")
    if len(re.findall(r"^## ", body, re.M)) < 4:
        e("needs at least 4 ## sections")
    if re.search(r"payhip\.com/(?:b/|PLACEHOLDER)", body, re.I):
        e("no Payhip product links in the body; the build adds the product box")
    if re.search(r"\]\(/", body):
        e("use relative links (../slug/), not root-absolute ones")
    for m in re.finditer(r"\]\(\.\./([a-z0-9-]+)/\)", body):
        if not (CONTENT / f"{m.group(1)}.md").exists():
            e(f"links to a guide that doesn't exist: {m.group(1)}")
    errs += lint_text(title + "\n" + desc + "\n" + body, f"kit/{path.name}")
    return errs


def all_articles():
    return sorted(CONTENT.glob("*.md"))


if __name__ == "__main__":
    files = [Path(a) for a in sys.argv[1:]] or all_articles()
    problems = [p for f in files for p in lint(f)]
    for f in files:
        try:
            print(f"{f.name}: {len(plain_words(split(f.read_text())[1]))} words")
        except Exception:  # noqa: BLE001
            pass
    print("\n".join(problems) if problems else f"OK: {len(files)} article(s), no problems.")
    sys.exit(1 if problems else 0)
