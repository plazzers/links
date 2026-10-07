# BUILD SPEC — Channel link pages ("link in bio" mini-sites) for Walter and Sal

## 1. What this is

Two small, fast, beautiful one-page websites in ONE repo, hosted on GitHub Pages:

- `https://plazzers.github.io/links/walter/` — Walter's Home Check
- `https://plazzers.github.io/links/sal/` — Chef Sal Romano
- `https://plazzers.github.io/links/` — tiny neutral index that redirects to nothing important (just two buttons). Keep it minimal.

These links go in the YouTube channel "About" section, channel banner links, Shorts comments and video descriptions. Purpose: turn viewers into **email subscribers** (via the free PDFs) and **buyers** (paid products), and look more trustworthy than a raw Payhip link.

## 2. Tech requirements

- Plain HTML + CSS (+ tiny vanilla JS only if needed). No build step, no frameworks, no CDN, no cookies, no tracking scripts. Relative paths only.
- Each page must load fast on a phone (target < 150 KB total excluding the host photo; photo compressed to WebP/JPEG ≤ 80 KB).
- Proper meta tags: title, description, Open Graph + Twitter card with an og:image (1200x630) per page, favicon, theme-color, canonical URL.
- Accessible: semantic HTML, alt text, contrast AA, buttons ≥ 48px tall.
- Light/dark handled by the brand palette (each page has one fixed brand look; it must look good in both OS modes — simplest: fixed brand palette, not auto dark).
- Simple click counting is NOT needed. Do add `?utm_source=links&utm_medium=bio` to every Payhip link so Payhip analytics can show where buyers came from (Payhip ignores unknown params safely).

## 3. Walter page

Brand: Deep Navy #1C2B3A background, Denim Blue #3E5F8A, Warm Off-White #F2EDE4 text, Warning Orange #E07A1F single accent, Warm Wood Brown #6B4A2F. Headline font feel: bold condensed (use a system stack like "Oswald-like": `"Arial Narrow", "Roboto Condensed", system-ui` with uppercase + letter spacing); body: system sans.

Photo: `walter/assets/walter.jpg` (provided in the repo under `source-assets/walter.jpg`; crop to a circle-friendly square, face centered).

Content top to bottom:
1. Round photo, "WALTER'S HOME CHECK", tagline "WHAT HOMEOWNERS MISS".
2. One short line: "I look at houses the way an inspector does — and show you the warning signs most people walk right past."
3. **Big primary button (orange):** "FREE: The Weekend Home Check — 25 things to check in 30 minutes" → https://payhip.com/b/hiIm1
4. Secondary free button: "FREE: Before the First Freeze — winter checklist" → https://payhip.com/b/Yml6C
5. Section "Guides & tools":
   - Card: Walter's Home Check App — "The whole room-by-room checklist on your phone. Photos, notes, PDF report." — $29 → https://payhip.com/b/OZeda (badge: NEW)
   - Card: The Home Check Manual — "Room-by-room guide, seasonal calendar and home record page." — $17 → https://payhip.com/b/ABaxT
   - Card: The House Buyer's Red Flag Checklist — "50 things to check before you buy." — $12 → https://payhip.com/b/HAfRF
6. Button: "Watch on YouTube" → https://www.youtube.com/@WaltersHomeCheck
7. Small footer: "Questions? waltershomecheck@outlook.com" · "Educational content. Not a substitute for a professional inspection of your property." · © 2026 Walter's Home Check.

## 4. Sal page

Brand: Espresso #2A1E18 background, Cream #FAF4E8 text, Tomato red #BE3A24 accent, Olive #586E34, a thin Italian tri-stripe (olive / cream / red) at the top. Headings: elegant serif (`Georgia, "Times New Roman", serif`); body: system sans.

Photo: `sal/assets/sal.jpg` (from `source-assets/sal.jpg`).

Content top to bottom:
1. Round photo, "CHEF SAL ROMANO", tagline "What the restaurants won't tell you."
2. One short line: "Forty years in restaurant kitchens. Now I'm telling you the tricks — and showing you how to cook it better at home."
3. **Big primary button (red):** "FREE: Sal's 25 Rules for Eating Out" → https://payhip.com/b/dnY7F
4. Section "Cook it at home":
   - Card: Sal's Kitchen App — "All 33 restaurant favorites on your phone, with shopping list & cooking timers." — $19 → https://payhip.com/b/xM6XQ (badge: NEW)
   - Card: Sal's Restaurant Copycat Cookbook — "33 restaurant dishes at home for a fraction of the price." — $17 → https://payhip.com/b/MQDaN
   - Card: Sal's Italian Kitchen — "60 real Italian recipes from 40 years in the kitchen." — $39.99 → https://payhip.com/b/Lv425
5. Button: "All of Sal's books" → https://payhip.com/SalRomano
6. Button: "Watch on YouTube" → https://www.youtube.com/@ChefSalRomano
7. Footer: "Questions? salromanochef@outlook.com" · "Recipes are inspired by popular restaurant dishes. Not affiliated with or endorsed by any restaurant." · © 2026 Chef Sal Romano. Mangia bene.

Never use real restaurant brand names or logos.

## 5. og:image

Generate `walter/og.jpg` and `sal/og.jpg` (1200x630) with Python/PIL from the photos + brand colors + name + tagline. Keep text large and readable.

## 6. Deliverables & testing

- Files: `index.html`, `walter/index.html`, `sal/index.html`, shared nothing (each page self-contained CSS inline is fine), assets, `.nojekyll`, README (plain language: how to change a link, price or add a product card).
- Remove `source-assets/` from what pages reference (keep the folder, pages use the optimized copies).
- Test with Playwright (Chromium preinstalled; do not run `playwright install`) at 390x844 and 1280x800: every link has the utm params, every Payhip URL matches the spec exactly, no horizontal scroll, images load, Lighthouse-style sanity (no console errors). Save screenshots to `docs/screens/`.
