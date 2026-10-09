"""Build the free lead magnet: "The Faceless Channel Starter Pack" (PDF + CSV template).

    python3 tools/make_starter_pack.py OUT_DIR

Not published on the site; the files are uploaded to Payhip as a free product.
"""
import csv
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
pdfmetrics.registerFont(TTFont("H", str(FONTS / "SpaceGrotesk-Bold.ttf")))
pdfmetrics.registerFont(TTFont("B", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("BB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

INK = HexColor("#1c1a27")
CORAL = HexColor("#ff6b4a")
CREAM = HexColor("#fdf3dc")
SOFT = HexColor("#ffe6df")
GREY = HexColor("#5b5868")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_config as CFG  # noqa: E402

KIT = CFG.BUY_URL + "?utm_source=starterpack&utm_medium=pdf&utm_campaign=starter"
SITE = "https://plazzers.github.io/links/creator-kit/?utm_source=starterpack&utm_medium=pdf&utm_campaign=starter"
SCORER = "https://plazzers.github.io/links/creator-kit/tools/title-scorer/"
CHECKER = "https://plazzers.github.io/links/creator-kit/tools/pinterest-csv-checker/"

W, H = letter
M = 54

HEADER = ["Title", "Media URL", "Pinterest board", "Thumbnail", "Description",
          "Link", "Publish date", "Keywords"]
EXAMPLE = ["5 Mistakes New Faceless Channels Make",
           "https://yourname.github.io/pins/mistakes-01.png",
           "Faceless YouTube Tips", "",
           "Five fixable mistakes that slow down new faceless YouTube channels, and what to do instead.",
           "https://example.com/your-video-or-product",
           "2026-11-02T09:00:00", "faceless youtube,youtube tips,content planning"]

FORMULAS = [
    ("Number + outcome", "7 Ways to Cut Your Grocery Bill This Month",
     "A real number and a concrete result. Only use the number you actually cover."),
    ("Mistake to avoid", "The Wiring Mistake Most First-Time Buyers Miss",
     "People click to avoid losses. The video must name the mistake early."),
    ("How to + time frame", "How to Plan a Week of Videos in One Hour",
     "Promise a method and a realistic time. Keep the time honest."),
    ("Before you ...", "Watch This Before You Buy a Used Car",
     "Ties the video to a decision the viewer is about to make."),
    ("X vs Y", "Index Funds vs Savings Account: Which Wins in 2026?",
     "Comparison titles work when the video gives a clear answer."),
    ("The real reason", "The Real Reason Your Bread Comes Out Dense",
     "Curiosity with a payoff. Answer it inside the first minute."),
    ("Question the viewer asks", "Is a Home Warranty Worth It?",
     "Use the exact question people type into search."),
    ("Beginner's guide", "A Beginner's Guide to Pinterest for YouTubers",
     "Clear audience, clear level. Good for evergreen search traffic."),
    ("Checklist", "The 10-Point Checklist I'd Use Before Uploading",
     "Implies a usable tool. Show the checklist on screen."),
    ("What happens when", "What Happens When You Skip Annual Maintenance",
     "Consequence-led. Works for explainers and story videos."),
]

CHECKLIST = [
    ("Monday - Plan", ["Pick 1-2 topics from your topic bank",
                       "Write 3 title options for each and score them",
                       "Write the script prompt and generate a first draft"]),
    ("Tuesday - Script", ["Edit the script: hook in the first 10 seconds",
                          "Cut anything that doesn't serve the title's promise",
                          "Add chapter markers"]),
    ("Wednesday - Produce", ["Voice / avatar render", "Edit, captions, b-roll",
                             "Thumbnail: 2-5 words, readable on a phone"]),
    ("Thursday - Package", ["Description: what it is, links, chapters, disclaimer",
                            "Cut 3-6 Shorts from the chapters",
                            "Make 5-10 Pinterest pins that link to the video"]),
    ("Friday - Publish", ["Schedule the video and the Shorts",
                          "Bulk-upload this week's pins with one CSV",
                          "Add next week's ideas to the topic bank"]),
    ("Weekend - Review", ["Note views, CTR and watch time for last week's video",
                          "Write one sentence: what worked, what to change",
                          "Keep one thing the same, change one thing"]),
]


def footer(c, n):
    c.setFont("B", 8)
    c.setFillColor(GREY)
    c.drawString(M, 30, "The Faceless Channel Starter Pack - free. Share it freely.")
    c.drawRightString(W - M, 30, str(n))


def wrap(c, text, font, size, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if c.stringWidth(t, font, size) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def para(c, x, y, text, font="B", size=10.5, width=W - 2 * M, lead=1.45, color=INK):
    c.setFont(font, size)
    c.setFillColor(color)
    for line in wrap(c, text, font, size, width):
        c.drawString(x, y, line)
        y -= size * lead
    return y


def h(c, y, text, size=22):
    c.setFont("H", size)
    c.setFillColor(INK)
    c.drawString(M, y, text)
    c.setFillColor(CORAL)
    c.rect(M, y - 10, 46, 4, stroke=0, fill=1)
    return y - 34


def cover(c):
    c.setFillColor(INK)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(CORAL)
    c.rect(M, H - 150, 60, 6, stroke=0, fill=1)
    c.setFont("B", 11)
    c.setFillColor(SOFT)
    c.drawString(M, H - 120, "FREE  |  FOR FACELESS & AI-AVATAR YOUTUBE CREATORS")
    c.setFont("H", 46)
    c.setFillColor(white)
    for i, line in enumerate(["The Faceless", "Channel", "Starter Pack"]):
        c.drawString(M, H - 220 - i * 54, line)
    y = H - 410
    for item in ["10 title formulas that aren't clickbait",
                 "A one-page weekly production checklist",
                 "The exact Pinterest bulk-upload CSV header (+ template)"]:
        c.setFillColor(CORAL)
        c.circle(M + 5, y + 4, 4, stroke=0, fill=1)
        c.setFillColor(CREAM)
        c.setFont("B", 13)
        c.drawString(M + 20, y, item)
        y -= 28
    c.setFont("B", 9)
    c.setFillColor(SOFT)
    c.drawString(M, 60, "From the makers of the Faceless Creator Kit")
    c.showPage()


def page_titles(c):
    y = h(c, H - 80, "1. Ten title formulas (honest ones)")
    y = para(c, M, y, "A good title makes a specific promise the video keeps. Fill in the formula with "
             "your topic, then check it: under ~60 characters, a strong first word, one keyword "
             "people actually search, no ALL CAPS, no words like \"shocking\" or \"insane\".",
             color=GREY) - 6
    for i, (name, ex, note) in enumerate(FORMULAS, 1):
        c.setFillColor(CORAL)
        c.setFont("H", 12)
        c.drawString(M, y, f"{i:02d}")
        c.setFillColor(INK)
        c.setFont("BB", 10.5)
        c.drawString(M + 28, y, name)
        y -= 15
        c.setFont("B", 10.5)
        c.drawString(M + 28, y, f"“{ex}”")
        y -= 14
        y = para(c, M + 28, y, note, size=9, color=GREY, width=W - 2 * M - 28) - 7
    c.setFillColor(SOFT)
    c.roundRect(M, y - 34, W - 2 * M, 38, 6, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("B", 9.5)
    c.drawString(M + 12, y - 13, "Score up to 3 titles for free (with reasons):")
    c.setFillColor(CORAL)
    c.drawString(M + 12, y - 26, SCORER)
    c.linkURL(SCORER, (M, y - 34, W - M, y + 4))
    footer(c, 2)
    c.showPage()


def page_checklist(c):
    y = h(c, H - 80, "2. The weekly checklist (one video a week)")
    y = para(c, M, y, "One finished video a week beats three half-finished ones. Print this page, "
             "tick the boxes, and adjust the days to your schedule.", color=GREY) - 8
    for day, items in CHECKLIST:
        c.setFont("H", 13)
        c.setFillColor(INK)
        c.drawString(M, y, day)
        y -= 18
        for it in items:
            c.setStrokeColor(INK)
            c.setLineWidth(1)
            c.rect(M + 4, y - 2, 10, 10, stroke=1, fill=0)
            c.setFont("B", 10.5)
            c.drawString(M + 24, y, it)
            y -= 17
        y -= 8
    footer(c, 3)
    c.showPage()


def page_csv(c):
    y = h(c, H - 80, "3. Pinterest bulk upload: the exact CSV")
    y = para(c, M, y, "Pinterest lets you schedule many pins at once from a CSV file "
             "(Settings > Import content > Upload). The first row must be this header, in this order:",
             color=GREY) - 4
    c.setFillColor(INK)
    c.roundRect(M, y - 30, W - 2 * M, 34, 6, stroke=0, fill=1)
    c.setFillColor(CREAM)
    c.setFont("B", 8.6)
    c.drawString(M + 10, y - 17, ",".join(HEADER))
    y -= 52
    rows = [("Title", "Up to 100 characters."),
            ("Media URL", "A PUBLIC link to the image file (.png/.jpg). Not a file on your computer. "
                          "Free option: a GitHub Pages site."),
            ("Pinterest board", "The board name exactly as it appears on your profile."),
            ("Thumbnail", "Only for video pins. Leave empty for image pins."),
            ("Description", "Up to 500 characters. Say what the pin links to."),
            ("Link", "Where a click goes: your video, blog post or product. Add UTM tags to track it."),
            ("Publish date", "Optional. Format like 2026-11-02T09:00:00. Must be in the future."),
            ("Keywords", "Optional, comma-separated. Wrap the whole cell in quotes.")]
    for k, v in rows:
        c.setFont("BB", 10)
        c.setFillColor(INK)
        c.drawString(M, y, k)
        y = para(c, M + 110, y, v, size=10, width=W - 2 * M - 110) - 5
    y -= 4
    y = para(c, M, y, "Common errors: a header typo, a Media URL that isn't public, a board name that "
             "doesn't match, dates in the past, and commas inside text without quotes. The template "
             "file in this download (pinterest-bulk-template.csv) has the header and one correct example row.",
             color=GREY) - 6
    c.setFillColor(SOFT)
    c.roundRect(M, y - 34, W - 2 * M, 38, 6, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("B", 9.5)
    c.drawString(M + 12, y - 13, "Check any bulk CSV for free before uploading:")
    c.setFillColor(CORAL)
    c.drawString(M + 12, y - 26, CHECKER)
    c.linkURL(CHECKER, (M, y - 34, W - M, y + 4))
    footer(c, 4)
    c.showPage()


def page_kit(c):
    y = h(c, H - 80, "Want this done for you?")
    y = para(c, M, y, "The Faceless Creator Kit is a web app with two tools that do the boring parts of "
             "the checklist above:") - 6
    for t, d in [("Channel Planner", "Video board from idea to published, calendar, topic bank, script "
                  "prompt templates, description builder, title & thumbnail lab with transparent scoring, "
                  "Shorts planner and a weekly review."),
                 ("Pin Factory", "8 pin templates at 1000x1500, your brand colors and fonts, batch mode "
                  "for many pins at once, and a Pinterest bulk CSV export with scheduling and UTM links.")]:
        c.setFont("H", 13)
        c.setFillColor(CORAL)
        c.drawString(M, y, t)
        y = para(c, M, y - 17, d) - 8
    y = para(c, M, y, "It runs in your browser, works offline and keeps your data on your device. "
             "One-time price, no subscription.", color=GREY) - 14
    c.setFillColor(CORAL)
    c.roundRect(M, y - 40, 250, 44, 8, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("H", 14)
    c.drawString(M + 18, y - 24, "See the Faceless Creator Kit")
    c.linkURL(KIT, (M, y - 40, M + 250, y + 4))
    y -= 66
    c.setFont("B", 9)
    c.setFillColor(GREY)
    c.drawString(M, y, "More free guides: plazzers.github.io/links/creator-kit/")
    c.linkURL(SITE, (M, y - 3, M + 300, y + 10))
    footer(c, 5)
    c.showPage()


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    pdf = out / "Faceless-Channel-Starter-Pack.pdf"
    c = canvas.Canvas(str(pdf), pagesize=letter)
    c.setTitle("The Faceless Channel Starter Pack")
    c.setAuthor("Faceless Creator Kit")
    cover(c)
    page_titles(c)
    page_checklist(c)
    page_csv(c)
    page_kit(c)
    c.save()
    with open(out / "pinterest-bulk-template.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(HEADER)
        w.writerow(EXAMPLE)
    print(pdf)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "starter-pack-out")
