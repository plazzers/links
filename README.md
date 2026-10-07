# Link pages for Walter and Sal

Two small "link in bio" pages, hosted free on GitHub Pages:

| Page | Address |
|---|---|
| Walter's Home Check | https://plazzers.github.io/links/walter/ |
| Chef Sal Romano | https://plazzers.github.io/links/sal/ |
| Small index (two buttons) | https://plazzers.github.io/links/ |

Each page is a single file you can edit in any text editor, or right on github.com
(open the file → pencil icon → edit → **Commit changes**). The live site updates
about a minute after you commit.

![Walter on a phone](docs/screens/walter-mobile.png) ![Sal on a phone](docs/screens/sal-mobile.png)

## What's where

```
index.html              the small index page
walter/index.html       Walter's page (all text, links and styling)
walter/og.jpg           picture shown when the link is shared (1200x630)
walter/assets/          Walter's photo, favicon, phone home-screen icon
sal/...                 the same for Sal
source-assets/          original photos (not used by the pages directly)
tools/make_og.py        rebuilds the share pictures and the page photos
tests/check.js          automatic checks + screenshots (docs/screens/)
```

## Change a link

Find the old link in `walter/index.html` or `sal/index.html` and replace it. Keep the
tracking bit at the end of every Payhip link so Payhip can show that buyers came from
this page:

```html
href="https://payhip.com/b/NEWCODE?utm_source=links&amp;utm_medium=bio"
```

(In HTML the `&` is written as `&amp;` — keep it that way.)

## Change a price

Each product is a "card". The price is in the line with `class="price"`:

```html
<span class="price">$17</span>
```

Change the number, commit, done.

## Add a product card

Copy a whole card — everything from `<li>` to `</li>` — and paste it right below.
Then change the link, the title, the one-line description and the price:

```html
<li>
  <a class="card" href="https://payhip.com/b/NEWCODE?utm_source=links&amp;utm_medium=bio">
    <span class="card-title">Product name</span>
    <span class="card-desc">One short sentence about what it is.</span>
    <span class="price">$15</span>
  </a>
</li>
```

To show a **NEW** label, put `<span class="badge">NEW</span>` at the start of the title:

```html
<span class="card-title"><span class="badge">NEW</span>Product name</span>
```

To remove a card, delete its `<li> … </li>` block. To remove a NEW label, delete the
`<span class="badge">NEW</span>` part.

If you add or change Payhip links, also update the list of expected links near the top
of `tests/check.js`, otherwise the check will (correctly) report a difference.

## Change the photo or the share picture

1. Replace `source-assets/walter.jpg` or `source-assets/sal.jpg` (square, face in the middle).
2. Run `python3 tools/make_og.py` (needs Python with Pillow: `pip install pillow`).
   This rebuilds the page photo (kept under 80 KB) and `og.jpg` for both pages.
3. Commit the changed files.

Facebook, X and others cache share pictures. After a change, paste the page address
into the Facebook Sharing Debugger and click "Scrape again" to refresh it.

## Turn on GitHub Pages (one time)

1. On github.com open the repo **plazzers/links** → **Settings** → **Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Choose branch **main** and folder **/ (root)**, then **Save**.
4. Wait 1–2 minutes and open https://plazzers.github.io/links/walter/.

The empty `.nojekyll` file tells GitHub to serve the files as they are.

## Run the checks (optional)

The checks open every page in a headless Chrome at phone size (390×844) and desktop size
(1280×800) and confirm: every link matches the spec exactly, every Payhip link carries the
tracking params, no sideways scrolling, images load, no console errors, buttons are at
least 48px tall, meta/share tags are present, and each page stays under 150 KB (photo
excluded). Screenshots are saved to `docs/screens/`.

```sh
npm install playwright        # once
npx playwright install chromium   # once, if you don't already have a Chromium for Playwright
node tests/check.js
```

## Notes

- No cookies, no trackers, no scripts, no outside fonts — the pages load instantly.
- Each page has one fixed brand look, so it looks the same in light and dark mode.
- Sal's page never names real restaurant brands; keep it that way when adding products.
