# SPEC v2 — Free interactive tools on the link pages

Read README.md and the existing pages first. Add two free, fast, shareable tools that bring in new viewers and point them to the free PDFs and paid products. Same rules as BUILD_SPEC.md: plain HTML/CSS/vanilla JS, no build, no CDN, no tracking, no cookies, relative paths, each page self-contained, brand look of its channel, og:image per page (generate with Python/PIL like the existing ones), utm params on every Payhip link (`?utm_source=links&utm_medium=tool&utm_campaign=<tool-slug>`).

Add a prominent card linking to each tool on the existing walter/ and sal/ pages (under the free PDF button): "FREE TOOL: …".

## 1. Walter — "What to Check in a House Built in…" (`walter/house-age/`)
- Input: year built (number or decade buttons: before 1950, 1950s, 1960s, 1970s, 1980s, 1990s, 2000s, 2010s+). Optional toggles: basement / crawlspace / slab; buying vs already own.
- Output: a tailored checklist of the era-specific things worth a closer look, each with a short plain-English why and "Look yourself" vs "Have a pro check" tag. Content (write it carefully, accurate and conservative, educational — no scare tactics, no prices):
  - Pre-1978: possible lead paint (don't sand/scrape before testing).
  - Pre-1980s: materials that may contain asbestos (some old floor tiles, pipe wrap, popcorn ceilings, vermiculite insulation) — don't disturb, test first.
  - Knob-and-tube or cloth wiring (roughly pre-1950s), ungrounded two-prong outlets, older fuse boxes; certain older panel brands with known concerns (Federal Pacific Stab-Lok, Zinsco) — have an electrician look.
  - Aluminum branch wiring (roughly mid-1960s to mid-1970s).
  - Galvanized steel supply pipes (common pre-1960s), cast-iron drains, clay sewer laterals → sewer camera inspection idea.
  - Polybutylene pipes (roughly late 1970s to mid-1990s).
  - Original windows, single-pane, insulation levels in older homes.
  - Chinese drywall concern (roughly 2001–2008 builds/renovations, mostly southeastern US) — sulfur smell, blackened copper.
  - Newer homes (2000s+): still check grading, attic ventilation, builder-grade water heaters reaching age, flashing details.
  - Always: radon test, roof age, water heater & HVAC age, foundation and water signs.
  Use cautious wording ("roughly", "common in", "worth asking about"). Add a short "why this matters" intro in Walter's voice.
- Actions: Print / Save as PDF (print stylesheet), Copy list, Share (Web Share API, fallback copy link).
- CTA block after results: FREE Weekend Home Check (https://payhip.com/b/hiIm1), "The Home Check Manual has a full chapter on what to check by the decade your house was built" (https://payhip.com/b/ABaxT), and the app (https://payhip.com/b/OZeda).
- Footer disclaimer: "Educational content. Not a substitute for a professional inspection of your property."
- URL state: `?year=1972&own=1` so results are shareable.

## 2. Sal — "Restaurant or Home?" calculator (`sal/restaurant-or-home/`)
- Pick dishes from the 33 Copycat Cookbook recipes (titles only — get them from the cookbook list below; no recipe text, no restaurant names) and how many people.
- Shows: typical restaurant price per plate (your conservative estimate, round numbers, labeled "typical casual-dining price, estimate") × people + tip slider (default 18%) + optional drinks per person ($3 default), versus "made at home" cost per plate (estimates; use the cookbook's "cost at home" where given — list below).
- Big result: "Dinner for 4 at a restaurant: ~$96. At home: ~$14. You keep ~$82." plus a Sal one-liner (punchy, warm, no brand names; rotate 6 lines).
- "Make it a month": if you cook this once a week instead of eating out → yearly savings.
- CTA: Sal's Kitchen App (https://payhip.com/b/xM6XQ) "all 33 recipes on your phone with shopping list & timers", Copycat Cookbook (https://payhip.com/b/MQDaN), FREE 25 Rules (https://payhip.com/b/dnY7F).
- Footer: "Prices are rough estimates for illustration. Recipes are inspired by popular restaurant dishes. Not affiliated with or endorsed by any restaurant."
- URL state for sharing (`?d=2,5,9&p=4`).

Dish list with home cost (from the cookbook; per serving unless noted — convert sensibly):
1 Garlic Butter Breadsticks ($0.25 each) · 2 Real Fettuccine Alfredo ($2.50/plate) · 3 Sausage, Potato & Kale Soup ($2/bowl) · 4 House Salad with Italian Dressing ($1/serving) · 5 Chicken Parmigiana · 6 Shrimp Scampi · 7 Angela's Tiramisu · 8 Cheddar Garlic Biscuits · 9 Pan-Seared Steak with Garlic Butter · 10 Loaded Baked Potato Soup · 11 Hot Spinach Artichoke Dip · 12 Honey Butter Dinner Rolls · 13 Restaurant-Style Blender Salsa · 14 Cilantro Lime Rice · 15 Sizzling Chicken Fajitas · 16 White Queso Dip ($1/serving) · 17 Burrito Bowl at Home · 18 Orange Chicken · 19 Better Chow Mein ($1.50) · 20 Takeout Fried Rice · 21 Chicken Lettuce Wraps · 22 Smash Burgers with Special Sauce · 23 Crispy Chicken Sandwich · 24 Classic Diner Chili · 25 Creamy Coleslaw · 26 Fluffy Diner Pancakes · 27 Baked Mac and Cheese · 28 Oven-Baked Buffalo Wings ($2.50/serving) · 29 Chocolate Lava Cakes · (30–33 are sauces — exclude from the calculator).
Where no cost is given, estimate conservatively and mark all numbers as estimates.

## 3. Testing & delivery
- Playwright (Chromium preinstalled; don't run `playwright install`) at 390x844 and 1280x800: both tools work, URL state round-trips, print view looks clean, every Payhip link has the correct utm params and exact product URL, no console errors, no horizontal scroll. Screenshots to docs/screens/.
- Update README. Commit to main.
