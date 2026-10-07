# SPEC v3 — Pinterest pin factory (Walter + Sal)

Goal: a big batch of high-quality Pinterest pins + a ready-to-upload Pinterest bulk CSV, hosted in this repo (GitHub Pages) so Pinterest can fetch the images by URL. Pinterest is a strong traffic source for home-maintenance and recipe content; every pin links to our free tools / link pages, which lead to free PDFs (email list) and paid products.

## 1. Output
- `pins/walter/NNN-slug.jpg` and `pins/sal/NNN-slug.jpg` — 1000x1500 JPG (2:3), < 350 KB each, sRGB.
- `pins/pinterest-bulk-walter.csv` and `pins/pinterest-bulk-sal.csv` in Pinterest's bulk-create format with header exactly:
  `Title,Media URL,Pinterest board,Thumbnail,Description,Link,Publish date,Keywords`
  - Media URL: `https://plazzers.github.io/links/pins/<channel>/<file>.jpg`
  - Thumbnail: empty (images, not video)
  - Title ≤ 100 chars, Description ≤ 500 chars (helpful, keyword-rich, natural, ends with a soft CTA), Keywords: 5–8 comma-separated inside quotes.
  - Publish date: ISO 8601 with time, spread 3 pins/day per channel starting 2026-10-10, times 13:00, 17:00, 21:00 UTC; alternate topics so similar pins aren't back to back.
  - Pinterest board names (create a sensible set, e.g. Walter: "Home Maintenance Checklists", "Buying a House Tips", "Winter Home Prep", "Older Home Problems"; Sal: "Copycat Restaurant Recipes", "Easy Italian Dinners", "Restaurant Secrets", "Budget Family Dinners").
  - Link: one of our pages with utm: `?utm_source=pinterest&utm_medium=pin&utm_campaign=<slug>` → Walter: `https://plazzers.github.io/links/walter/house-age/` (for age/older-home pins), otherwise `https://plazzers.github.io/links/walter/`; Sal: `https://plazzers.github.io/links/sal/restaurant-or-home/` (money/restaurant pins) or `https://plazzers.github.io/links/sal/`.
- `pins/index.html` — a simple private-ish gallery (noindex) showing all pins with title, board, date, link, to review them visually.
- `tools/make_pins.py` — the generator (Python + Pillow, fonts vendored in `tools/fonts/` under OFL: Oswald Bold, Source Sans 3 / Inter for Walter; Playfair Display / Inter for Sal). Re-runnable; content lives in `tools/pins_walter.yaml` / `tools/pins_sal.yaml` (or JSON) so the owner can add pins later.
- README section: how to upload the CSV in Pinterest (Business account → Create → Create Pins in bulk → upload CSV), how to add more pins.

## 2. Walter pins (60)
Match the existing style exactly: see `source-assets/walter-pin-style-reference.jpg` — deep navy #1C2B3A background with faint blueprint grid, "WALTER'S HOME CHECK" top-left (off-white #F2EDE4) and "WHAT HOMEOWNERS MISS" top-right (orange #E07A1F), small orange kicker line, huge condensed headline in off-white with the key words in orange, yellow tape-measure divider, 1–2 lines of body text, orange tag button bottom-left (e.g. WINTER TIP / BUYER RED FLAG / 5-MINUTE CHECK / OLDER HOMES), footer "YOUTUBE · WALTER'S HOME CHECK", Walter's photo bottom-right in a circle with orange ring (use `source-assets/walter.jpg`, crop face/shoulders; soft edge so it sits nicely).
Content mix (write it — accurate, calm, practical, educational; never claims credentials; no prices; no scare tactics):
- 20 "One thing to do today" quick checks (from home maintenance basics: GFCI test, dryer vent, HVAC filter, sump pump test, smoke/CO alarms, water heater relief valve, garage door reverse test, caulk, downspouts, grading, attic after storm…)
- 15 "Buyer red flag" pins (foundation cracks direction, fresh paint in one spot, musty basement, DIY electrical, ceiling stains, bad grading, too-perfect flip, etc.)
- 12 "Older homes" pins by era (lead paint pre-1978, asbestos materials, knob-and-tube, aluminum wiring 1965–1975, polybutylene, galvanized pipes, old panels) → link to house-age tool
- 8 seasonal (winter/fall/spring) pins
- 5 list pins ("7 things to check before winter", "5 signs your roof is near the end", …) with a numbered list layout variant
At most 10 pins mention a product (free checklist mostly; Manual / App rarely) and only softly.

## 3. Sal pins (60)
Sal style: espresso #2A1E18 background, thin Italian tri-stripe top (olive #586E34 / cream #FAF4E8 / tomato red #BE3A24), elegant serif headline (cream, key words red), Inter body, Sal's photo (`source-assets/sal.jpg`) in a circle with red ring, footer "YOUTUBE · CHEF SAL ROMANO". No food photos (we have none) — make the typography and layout appetizing: big dish name, a "Sal says" quote box, a small ingredient-count / time / cost-at-home row with simple line icons drawn in Pillow.
Content (no real restaurant brand names anywhere — use "the Italian chain", "the steakhouse chains", etc.; recipes are "inspired by"):
- 33 recipe pins, one per Copycat Cookbook dish (titles below), each with time & "cost at home" and a punchy Sal line (don't reproduce recipe steps). Titles: Garlic Butter Breadsticks; Real Fettuccine Alfredo; Sausage, Potato & Kale Soup; House Salad with Italian Dressing; Chicken Parmigiana; Shrimp Scampi; Angela's Tiramisu; Cheddar Garlic Biscuits; Pan-Seared Steak with Garlic Butter; Loaded Baked Potato Soup; Hot Spinach Artichoke Dip; Honey Butter Dinner Rolls; Restaurant-Style Blender Salsa; Cilantro Lime Rice; Sizzling Chicken Fajitas; White Queso Dip; Burrito Bowl at Home; Orange Chicken; Better Chow Mein; Takeout Fried Rice; Chicken Lettuce Wraps; Smash Burgers with Special Sauce; Crispy Chicken Sandwich; Classic Diner Chili; Creamy Coleslaw; Fluffy Diner Pancakes; Baked Mac and Cheese; Oven-Baked Buffalo Wings; Chocolate Lava Cakes; Sunday Marinara; Garlic Butter Sauce; Steak Sauce; Buttermilk Ranch.
- 16 "Restaurant trick" pins (menu golden corner, no dollar signs, price endings, decoy dish, drinks markup, the little yeses upsell, specials, market price, salty bread basket, music & lighting, portion game, dessert from a box, birthday dessert, "can I start you off", fancy menu words, what Sal orders).
- 11 money pins ("Dinner for 4: restaurant vs home", "Make takeout night cheaper", "Copycat recipes that save the most"…) → link to the Restaurant or Home calculator.
Each recipe pin's description should read naturally for search ("copycat garlic butter breadsticks recipe like the Italian chain, easy homemade…").

## 4. Quality bar & checks
- Render every pin and visually review a contact sheet (`pins/contact-walter.jpg`, `pins/contact-sal.jpg`) — fix text overflow, widows, tiny text, faces cut badly. Headlines must be readable at phone size (min ~70 px cap height).
- Validate CSVs: UTF-8, quoted properly, all Media URLs point to files that exist in the repo, all links contain the utm params, title/description length limits, dates ascending and unique per channel time slot.
- No real restaurant names, no logos, no medical/health claims, no prices for repairs.
- Commit everything to main (GitHub Pages will host the images). Then fetch 3 random Media URLs from the live site to confirm they load (they appear a minute after the push).
