"""Faceless Creator Kit site — the ONLY place the store links live.

Edit the two links below, then rebuild:

    python3 tools/build_kit_site.py

Every Buy / Get-it-free button on creator-kit/ is made from these, with
?utm_source=kitsite&utm_medium=<page>&utm_campaign=<slug> added by the build.
Nothing else in the repo may contain a Payhip link for the kit
(tests/check_kit_site.py checks this).
"""

# The paid product on Payhip (placeholder until the product exists).
BUY_URL = "https://payhip.com/b/KQZna"

# The free lead-magnet product on Payhip (placeholder until it exists).
FREE_URL = "https://payhip.com/PLACEHOLDER-FREE"

# What the free lead magnet is called on the site (change it to match the real product).
FREE_NAME = "The Faceless Channel Starter Pack"
FREE_DESC = ("A free PDF: 10 title formulas, a one-page weekly planning checklist and a "
             "Pinterest bulk-upload CSV template with the exact header.")

# Price shown in the price box and in the Product JSON-LD (USD, numbers only).
PRICE = "29"

# The app itself (access-code gated) — linked from the FAQ only.
APP_URL = "https://plazzers.github.io/channel-studio/kit/"
