// Playwright checks for the link pages.
// Run from the repo root:  node tests/check.js
// (needs the `playwright` npm package; if it is installed globally, run
//  NODE_PATH="$(npm root -g)" node tests/check.js)
// Serves the repo under /links/ like GitHub Pages, checks every page and both
// free tools (tests/tools.js) at phone and desktop size, and saves screenshots
// to docs/screens/.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { checkTools } = require('./tools');

const ROOT = path.resolve(__dirname, '..');
const UTM = 'utm_source=links&utm_medium=bio';
const VIEWPORTS = [
  { width: 390, height: 844 },
  { width: 1280, height: 800 },
];

// Exactly what BUILD_SPEC.md (+ the FREE TOOL cards from SPEC_V2_FREE_TOOLS.md and the
// "Read the guides" button from SPEC_V4_GUIDE_SITES.md) asks for, in page order.
const PAGES = {
  walter: {
    photo: 'walter/assets/walter.jpg',
    links: [
      'https://payhip.com/b/hiIm1',
      'https://payhip.com/b/Yml6C',
      'house-age/',
      'guides/',
      'https://payhip.com/b/OZeda',
      'https://payhip.com/b/ABaxT',
      'https://payhip.com/b/HAfRF',
      'https://www.youtube.com/@WaltersHomeCheck',
      'mailto:waltershomecheck@outlook.com',
    ],
    text: [
      "WALTER'S HOME CHECK", 'WHAT HOMEOWNERS MISS',
      'I look at houses the way an inspector does — and show you the warning signs most people walk right past.',
      'FREE: The Weekend Home Check — 25 things to check in 30 minutes',
      'FREE: Before the First Freeze — Winter checklist',
      'FREE TOOL: What to Check in a House Built in… — Pick the year, get your era checklist',
      'Read the guides',
      'Guides & tools',
      "Walter's Home Check App", 'The whole room-by-room checklist on your phone. Photos, notes, PDF report.', '$29', 'NEW',
      'The Home Check Manual', 'Room-by-room guide, seasonal calendar and home record page.', '$17',
      "The House Buyer's Red Flag Checklist", '50 things to check before you buy.', '$12',
      'Watch on YouTube',
      'Educational content. Not a substitute for a professional inspection of your property.',
      "© 2026 Walter's Home Check",
    ],
  },
  sal: {
    photo: 'sal/assets/sal.jpg',
    links: [
      'https://payhip.com/b/dnY7F',
      'restaurant-or-home/',
      'guides/',
      'https://payhip.com/b/B9g7J',
      'https://payhip.com/b/xM6XQ',
      'https://payhip.com/b/MQDaN',
      'https://payhip.com/b/Lv425',
      'https://payhip.com/SalRomano',
      'https://www.youtube.com/@ChefSalRomano',
      'mailto:salromanochef@outlook.com',
    ],
    text: [
      'CHEF SAL ROMANO', "What the restaurants won't tell you.",
      "I know how restaurant kitchens work. Now I'm telling you the tricks — and showing you how to cook it better at home.",
      'Read the guides',
      "FREE: Sal's 25 Rules for Eating Out",
      'FREE TOOL: Restaurant or Home? — See what you keep by cooking it yourself',
      'Cook it at home',
      "Sal's Kitchen App", 'All 33 restaurant favorites on your phone, with shopping list & cooking timers.', '$19', 'NEW',
      "Sal's Restaurant Copycat Cookbook", '33 restaurant dishes at home for a fraction of the price.', '$17',
      "Sal's Italian Kitchen", '60 real Italian recipes, from antipasti to dolci.', '$39.99',
      "All of Sal's books", 'Watch on YouTube',
      'Recipes are inspired by popular restaurant dishes. Not affiliated with or endorsed by any restaurant.',
      '© 2026 Chef Sal Romano. Mangia bene.',
    ],
  },
  index: { links: ['walter/', 'sal/', 'creator-kit/'], text: ["Walter's Home Check", 'Chef Sal Romano', 'Tools for creators'] },
};

const TYPES = { '.html': 'text/html; charset=utf-8', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml' };

function serve() {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      let p = decodeURIComponent(new URL(req.url, 'http://x').pathname);
      if (!p.startsWith('/links/')) { res.writeHead(404); return res.end(); }
      p = path.join(ROOT, p.slice('/links/'.length));
      if (!p.startsWith(ROOT)) { res.writeHead(403); return res.end(); }
      if (fs.existsSync(p) && fs.statSync(p).isDirectory()) p = path.join(p, 'index.html');
      if (!fs.existsSync(p)) { res.writeHead(404); return res.end(); }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
      fs.createReadStream(p).pipe(res);
    });
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

function jpegSize(file) {
  const b = fs.readFileSync(file);
  for (let i = 2; i < b.length;) {
    const marker = b[i + 1];
    const len = b.readUInt16BE(i + 2);
    if (marker >= 0xc0 && marker <= 0xc2) return { height: b.readUInt16BE(i + 5), width: b.readUInt16BE(i + 7) };
    i += 2 + len;
  }
  return null;
}

(async () => {
  const server = await serve();
  const base = `http://127.0.0.1:${server.address().port}/links/`;
  const browser = await chromium.launch(fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {});
  const failures = [];
  const fail = (where, msg) => failures.push(`[${where}] ${msg}`);
  fs.mkdirSync(path.join(ROOT, 'docs/screens'), { recursive: true });

  for (const [name, spec] of Object.entries(PAGES)) {
    const url = base + (name === 'index' ? '' : `${name}/`);
    const src = fs.readFileSync(path.join(ROOT, name === 'index' ? 'index.html' : `${name}/index.html`), 'utf8');
    if (/source-assets/.test(src)) fail(name, 'page references source-assets/');
    if (/<script/i.test(src)) fail(name, 'page contains a script');
    if (/(src|href)="\/(?!\/)/.test(src)) fail(name, 'page uses a root-absolute path');

    if (name !== 'index') {
      const og = jpegSize(path.join(ROOT, name, 'og.jpg'));
      if (!og || og.width !== 1200 || og.height !== 630) fail(name, `og.jpg is ${JSON.stringify(og)}, want 1200x630`);
      const photoKB = fs.statSync(path.join(ROOT, spec.photo)).size / 1024;
      if (photoKB > 80) fail(name, `photo is ${photoKB.toFixed(1)} KB (> 80 KB)`);
    }

    for (const vp of VIEWPORTS) {
      const where = `${name} ${vp.width}x${vp.height}`;
      const context = await browser.newContext({ viewport: vp, deviceScaleFactor: vp.width < 500 ? 2 : 1 });
      const page = await context.newPage();
      let bytes = 0;
      page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') fail(where, `console ${m.type()}: ${m.text()}`); });
      page.on('pageerror', (e) => fail(where, `page error: ${e.message}`));
      page.on('requestfailed', (r) => fail(where, `request failed: ${r.url()}`));
      page.on('response', async (r) => {
        if (!r.url().startsWith(base)) { fail(where, `external request: ${r.url()}`); return; }
        if (r.status() >= 400) fail(where, `HTTP ${r.status()}: ${r.url()}`);
        const body = await r.body().catch(() => Buffer.alloc(0));
        if (!(spec.photo && r.url().endsWith(spec.photo))) bytes += body.length;
      });

      await page.goto(url, { waitUntil: 'networkidle' });

      const info = await page.evaluate(() => {
        const meta = (sel) => document.querySelector(sel)?.getAttribute('content') || document.querySelector(sel)?.getAttribute('href') || null;
        return {
          links: [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')),
          // textContent so screen-reader-only punctuation ("FREE:") counts too
          text: document.body.textContent.replace(/\s+/g, ' '),
          scrollW: document.documentElement.scrollWidth,
          clientW: document.documentElement.clientWidth,
          imgs: [...document.images].map((i) => ({ src: i.currentSrc, ok: i.complete && i.naturalWidth > 0, alt: i.alt })),
          small: [...document.querySelectorAll('a.btn, a.card, main a, body > main > a')]
            .map((a) => ({ t: a.textContent.trim().slice(0, 40), h: a.getBoundingClientRect().height }))
            .filter((a) => a.h < 48),
          footerSmall: [...document.querySelectorAll('footer a')]
            .map((a) => ({ t: a.textContent.trim(), h: a.getBoundingClientRect().height }))
            .filter((a) => a.h < 44),
          title: document.title,
          lang: document.documentElement.lang,
          h1: document.querySelectorAll('h1').length,
          meta: {
            description: meta('meta[name=description]'),
            canonical: meta('link[rel=canonical]'),
            theme: meta('meta[name=theme-color]'),
            icon: meta('link[rel=icon]'),
            ogTitle: meta('meta[property="og:title"]'),
            ogImage: meta('meta[property="og:image"]'),
            ogUrl: meta('meta[property="og:url"]'),
            twCard: meta('meta[name="twitter:card"]'),
            twImage: meta('meta[name="twitter:image"]'),
          },
        };
      });

      // Links: exact URLs from the spec, in order, Payhip ones with UTM params.
      const want = spec.links.map((l) => (l.startsWith('https://payhip.com/') ? `${l}?${UTM}` : l));
      if (JSON.stringify(info.links) !== JSON.stringify(want)) {
        fail(where, `links differ from spec:\n    got  ${JSON.stringify(info.links)}\n    want ${JSON.stringify(want)}`);
      }
      for (const l of info.links) {
        if (l.includes('payhip.com')) {
          const u = new URL(l);
          if (u.searchParams.get('utm_source') !== 'links' || u.searchParams.get('utm_medium') !== 'bio') fail(where, `missing UTM: ${l}`);
        }
      }
      for (const t of spec.text) if (!info.text.toLowerCase().includes(t.toLowerCase())) fail(where, `missing text: ${t}`);
      if (info.scrollW > info.clientW) fail(where, `horizontal scroll: ${info.scrollW} > ${info.clientW}`);
      for (const img of info.imgs) {
        if (!img.ok) fail(where, `image did not load: ${img.src}`);
        if (!img.alt) fail(where, `image missing alt: ${img.src}`);
      }
      for (const s of info.small) fail(where, `tap target under 48px: "${s.t}" (${s.h}px)`);
      for (const s of info.footerSmall) fail(where, `footer link under 44px: "${s.t}" (${s.h}px)`);
      if (!info.title) fail(where, 'missing <title>');
      if (info.lang !== 'en') fail(where, 'missing lang');
      if (info.h1 !== 1) fail(where, `expected one h1, got ${info.h1}`);
      const required = name === 'index' ? ['description', 'canonical', 'theme', 'icon'] : Object.keys(info.meta);
      for (const k of required) if (!info.meta[k]) fail(where, `missing meta: ${k}`);
      if (name !== 'index') {
        const pageUrl = `https://plazzers.github.io/links/${name}/`;
        if (info.meta.canonical !== pageUrl || info.meta.ogUrl !== pageUrl) fail(where, 'canonical/og:url mismatch');
        if (info.meta.ogImage !== `${pageUrl}og.jpg` || info.meta.twImage !== `${pageUrl}og.jpg`) fail(where, 'og:image/twitter:image mismatch');
      }
      if (bytes > 150 * 1024) fail(where, `page weight ${Math.round(bytes / 1024)} KB excluding photo (> 150 KB)`);

      const shot = path.join(ROOT, 'docs/screens', `${name}-${vp.width < 500 ? 'mobile' : 'desktop'}.png`);
      await page.screenshot({ path: shot, fullPage: true });
      console.log(`${where}: ${info.links.length} links, ${(bytes / 1024).toFixed(1)} KB excl. photo, scrollW ${info.scrollW}/${info.clientW} -> ${path.relative(ROOT, shot)}`);
      await context.close();
    }
  }

  await checkTools(browser, base, VIEWPORTS, fail);

  await browser.close();
  server.close();
  if (failures.length) {
    console.error(`\n${failures.length} problem(s):\n` + failures.join('\n'));
    process.exit(1);
  }
  console.log('\nAll checks passed.');
})();
