// Playwright checks for the free tools (SPEC_V2_FREE_TOOLS.md).
// Run through tests/check.js, which serves the site and launches the browser.
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');

const TOOLS = {
  'walter/house-age': {
    slug: 'house-age',
    photo: 'walter/assets/walter.jpg',
    payhip: ['https://payhip.com/b/hiIm1', 'https://payhip.com/b/ABaxT', 'https://payhip.com/b/OZeda'],
    other: ['../', '../guides/buying-an-older-home-checklist/', '../guides/knob-and-tube-wiring/', '../guides/lead-paint-in-older-homes/', '../guides/polybutylene-and-galvanized-pipes/', '../guides/', '../'],
    text: [
      'What to check in a house built in…', 'Why this matters', 'Related guides',
      'The Home Check Manual has a full chapter on what to check by the decade your house was built',
      'Educational content. Not a substitute for a professional inspection of your property.',
    ],
    shotQuery: '?year=1972&found=basement',
    run: walterFlow,
  },
  'sal/restaurant-or-home': {
    slug: 'restaurant-or-home',
    photo: 'sal/assets/sal.jpg',
    payhip: ['https://payhip.com/b/xM6XQ', 'https://payhip.com/b/MQDaN', 'https://payhip.com/b/dnY7F'],
    other: ['../', '../guides/eating-out-vs-cooking-at-home/', '../guides/how-to-eat-out-cheaper/', '../guides/restaurant-drink-markup/', '../guides/sunday-marinara-sauce/', '../guides/', '../'],
    text: [
      'Restaurant or Home?', 'Related guides', 'all 33 recipes on your phone with shopping list & timers',
      'typical casual-dining price, estimate',
      'Prices are rough estimates for illustration. Recipes are inspired by popular restaurant dishes. Not affiliated with or endorsed by any restaurant.',
    ],
    shotQuery: '?d=2,5,9&p=4',
    run: salFlow,
  },
};

// Restaurant (out) and home cost per plate, mirrored from the page so the math is checked independently.
const SAL = { 1: [3, 0.5], 2: [18, 2.5], 4: [6, 1], 5: [20, 3.5], 7: [9, 1.5], 9: [26, 8], 18: [12, 2.5], 19: [10, 1.5], 20: [10, 1.25] };
function salExpect(d, p, t = 18, dr = 3) {
  const out = d.reduce((a, id) => a + SAL[id][0], 0) * p;
  const home = d.reduce((a, id) => a + SAL[id][1], 0) * p + (dr > 0 ? 0.5 * p : 0);
  const o = Math.round((out + dr * p) * (1 + t / 100));
  const h = Math.round(home);
  return { o, h, k: o - h };
}

async function pageInfo(page) {
  return page.evaluate(() => {
    const meta = (sel) => document.querySelector(sel)?.getAttribute('content') || document.querySelector(sel)?.getAttribute('href') || null;
    const visible = (el) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden'; };
    return {
      links: [...document.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')),
      text: document.body.textContent.replace(/\s+/g, ' '),
      visibleText: document.body.innerText,
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth,
      imgs: [...document.images].map((i) => ({ src: i.currentSrc, ok: i.complete && i.naturalWidth > 0, alt: i.alt })),
      small: [...document.querySelectorAll('main a, button, .chip span, .dish span, input[type=number], input[type=range], label.check')]
        .filter(visible)
        .map((el) => ({ t: (el.textContent || el.id || el.type).trim().slice(0, 40), h: el.getBoundingClientRect().height }))
        .filter((a) => a.h < 48),
      footerSmall: [...document.querySelectorAll('footer a')].filter(visible)
        .map((a) => ({ t: a.textContent.trim(), h: a.getBoundingClientRect().height })).filter((a) => a.h < 44),
      title: document.title,
      lang: document.documentElement.lang,
      h1: document.querySelectorAll('h1').length,
      meta: {
        description: meta('meta[name=description]'), canonical: meta('link[rel=canonical]'), theme: meta('meta[name=theme-color]'),
        icon: meta('link[rel=icon]'), ogTitle: meta('meta[property="og:title"]'), ogImage: meta('meta[property="og:image"]'),
        ogUrl: meta('meta[property="og:url"]'), twCard: meta('meta[name="twitter:card"]'), twImage: meta('meta[name="twitter:image"]'),
      },
    };
  });
}

// Read location.href from the page: page.url() can lag behind history.replaceState.
async function href(page) { return page.evaluate(() => location.href); }
async function query(page) { return Object.fromEntries(new URL(await href(page)).searchParams); }

async function walterFlow({ page, open, fail, where, clip }) {
  const has = async (t) => (await page.locator('#groups').innerText()).includes(t);
  const titles = async () => page.$$eval('#groups h4', (els) => els.map((e) => e.textContent));

  await open('');
  if (await page.isVisible('#results')) fail(where, 'results visible before a year is picked');

  // Decade button
  await page.click('label.chip:has(input[value="1970s"]) span');
  if ((await query(page)).year !== '1970s') fail(where, `decade click: URL ${await href(page)}`);
  for (const t of ['Aluminum branch wiring', 'Possible lead paint', 'Polybutylene water pipes', 'Electrical panel brand', 'Radon test']) {
    if (!(await has(t))) fail(where, `1970s: missing "${t}"`);
  }
  for (const t of ['Knob-and-tube', 'drywall']) if (await has(t)) fail(where, `1970s: should not show "${t}"`);
  if (await page.isVisible('#err')) fail(where, 'error visible after decade click');

  // Typed year + toggles
  await page.fill('#year', '1972');
  await page.click('button[type=submit]');
  await page.click('label.chip:has(input[name=own][value="1"]) span');
  await page.click('label.chip:has(input[value="basement"]) span');
  let q = await query(page);
  if (q.year !== '1972' || q.own !== '1' || q.found !== 'basement') fail(where, `typed year/toggles: URL ${await href(page)}`);
  if (await page.isChecked('input[value="1970s"]')) fail(where, 'decade still selected after typing a year');
  if (!(await has('Basement: water and walls'))) fail(where, 'basement item missing');
  if (!(await has('Since you own it:'))) fail(where, '"own" tips missing');

  // Copy list
  await page.click('#copy');
  await page.waitForFunction(() => document.getElementById('status').textContent.length > 0);
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  for (const t of ['a house built in 1972', '[ ] Aluminum branch wiring (Have a pro check)', 'Basement: water and walls', 'Educational content.', 'year=1972']) {
    if (!copied.includes(t)) fail(where, `copied list missing "${t}"`);
  }

  // URL round trip
  await open('?year=1972&own=1');
  if ((await page.inputValue('#year')) !== '1972') fail(where, 'round trip: year not restored');
  if (!(await page.isChecked('input[name=own][value="1"]'))) fail(where, 'round trip: own not restored');
  if (!(await page.locator('#res-title').innerText()).includes('1972')) fail(where, 'round trip: title');
  if (!(await has('Aluminum branch wiring'))) fail(where, 'round trip: list');

  // Era boundaries
  const cases = [
    ['1940', ['Knob-and-tube', 'Galvanized steel', 'Possible lead paint'], ['Polybutylene', 'Aluminum', 'drywall', 'Grading']],
    ['2005', ['drywall', 'Grading and drainage', 'Attic ventilation', 'Flashing details', 'Radon test'], ['lead paint', 'asbestos', 'Knob-and-tube']],
    ['2020', ['Grading and drainage', 'Roof age'], ['lead paint', 'drywall', 'Polybutylene']],
    ['pre1950', ['Knob-and-tube'], ['Polybutylene']],
    ['2010s', ['Grading and drainage'], ['drywall']],
  ];
  for (const [y, want, not] of cases) {
    await open(`?year=${y}`);
    const t = (await titles()).join(' | ');
    for (const w of want) if (!t.includes(w)) fail(where, `year=${y}: missing "${w}"`);
    for (const n of not) if (t.includes(n)) fail(where, `year=${y}: should not show "${n}"`);
  }

  // Bad input
  await open('?year=abc');
  if (await page.isVisible('#results')) fail(where, 'year=abc shows results');
  await page.fill('#year', '19');
  await page.click('button[type=submit]');
  if (!(await page.isVisible('#err'))) fail(where, 'no error for a 2-digit year');

  // Share: Web Share API path, then fallback (copy link)
  await open('?year=1972');
  await page.evaluate(() => { navigator.share = (d) => { window.__shared = d; return Promise.resolve(); }; });
  await page.click('#share');
  const shared = await page.evaluate(() => window.__shared);
  if (!shared || !shared.url.includes('year=1972')) fail(where, `Web Share not called with the URL: ${JSON.stringify(shared)}`);
  await page.evaluate(() => { delete navigator.share; Object.defineProperty(navigator, 'share', { value: undefined }); });
  await page.click('#share');
  await page.waitForFunction(() => /Link copied/.test(document.getElementById('status').textContent));
  if (!(await page.evaluate(() => navigator.clipboard.readText())).includes('year=1972')) fail(where, 'share fallback did not copy the link');

  // Print view
  await open('?year=1972&found=basement');
  await page.emulateMedia({ media: 'print' });
  const pr = await page.evaluate(() => {
    const shown = (s) => [...document.querySelectorAll(s)].some((el) => getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().height > 0);
    return { form: shown('form'), actions: shown('.actions'), cta: shown('.cta'), why: shown('.why'), items: document.querySelectorAll('#groups .item').length, itemsShown: shown('#groups .item'),
      disclaimer: document.body.innerText.includes('Not a substitute for a professional inspection'), bg: getComputedStyle(document.body).backgroundColor,
      scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth };
  });
  if (pr.form || pr.actions || pr.cta || pr.why) fail(where, `print view shows controls: ${JSON.stringify(pr)}`);
  if (!pr.itemsShown || !pr.disclaimer) fail(where, 'print view missing list or disclaimer');
  if (pr.bg !== 'rgb(255, 255, 255)') fail(where, `print background is ${pr.bg}`);
  if (pr.scrollW > pr.clientW) fail(where, 'print view scrolls sideways');
  await clip('print');
  await page.emulateMedia({ media: 'screen' });
}

async function salFlow({ page, open, fail, where, clip }) {
  const big = async () => {
    const t = (await page.locator('#big').innerText()).replace(/\s+/g, ' ');
    const m = t.match(/Dinner for (\d+) at a restaurant: ~\$([\d,]+)\. At home: ~\$([\d,]+)\. ?You keep ~\$([\d,]+)\./);
    return m ? { p: +m[1], o: +m[2].replace(/,/g, ''), h: +m[3].replace(/,/g, ''), k: +m[4].replace(/,/g, '') } : t;
  };
  const checked = () => page.$$eval('input[name=d]:checked', (els) => els.map((e) => +e.value));
  const expectBig = async (label, d, p, t, dr) => {
    const want = salExpect(d, p, t, dr);
    const got = await big();
    if (typeof got === 'string' || got.p !== p || got.o !== want.o || got.h !== want.h || got.k !== want.k) {
      fail(where, `${label}: result ${JSON.stringify(got)}, want ${JSON.stringify({ p, ...want })}`);
    }
    return want;
  };

  // Defaults
  await open('');
  if (JSON.stringify(await checked()) !== '[2,4,7]') fail(where, `default dishes ${await checked()}`);
  await expectBig('default', [2, 4, 7], 4);
  if ((await page.$$('input[name=d]')).length !== 29) fail(where, 'expected 29 dishes');
  if (await page.locator('.quote').innerText() === '') fail(where, 'no Sal line');

  // URL state from the spec example
  await open('?d=2,5,9&p=4');
  if (JSON.stringify(await checked()) !== '[2,5,9]') fail(where, `?d=2,5,9 checked ${await checked()}`);
  const w = await expectBig('?d=2,5,9&p=4', [2, 5, 9], 4);
  const year = (w.k * 52).toLocaleString('en-US');
  if (!(await page.locator('#month').innerText()).includes(`~$${year} a year`)) fail(where, `yearly savings, want ~$${year} a year`);
  const line1 = await page.locator('#quote').innerText();

  // Interact: add a dish, one more person, tip 20%, no drinks
  await page.click('label.dish:has(input[value="1"]) span');
  await page.click('#plus');
  await page.focus('#tip');
  await page.keyboard.press('ArrowRight');
  await page.keyboard.press('ArrowRight');
  await page.click('label.check:has(#drinks-on)');
  let q = await query(page);
  if (q.d !== '1,2,5,9' || q.p !== '5' || q.t !== '20' || q.dr !== '0') fail(where, `after edits URL ${await href(page)}`);
  if (!(await href(page)).includes('d=1,2,5,9')) fail(where, 'commas in URL are escaped');
  await expectBig('after edits', [1, 2, 5, 9], 5, 20, 0);
  if ((await page.locator('#quote').innerText()) === line1) fail(where, 'Sal line did not rotate');
  const lines = new Set();
  for (const v of ['18', '19', '20', '4', '7', '9', '18']) {
    await page.click(`label.dish:has(input[value="${v}"]) span`);
    lines.add(await page.locator('#quote').innerText());
  }
  if (lines.size < 6) fail(where, `expected 6 rotating lines, saw ${lines.size}`);

  // Round trip
  await open('?d=1,2,5,9&p=5&t=20&dr=0');
  if (JSON.stringify(await checked()) !== '[1,2,5,9]') fail(where, 'round trip dishes');
  if ((await page.locator('#people').innerText()) !== '5') fail(where, 'round trip people');
  if ((await page.inputValue('#tip')) !== '20') fail(where, 'round trip tip');
  if (await page.isChecked('#drinks-on')) fail(where, 'round trip drinks');
  await expectBig('round trip', [1, 2, 5, 9], 5, 20, 0);

  // Drinks amount + quick pick + clear
  await open('?d=2&p=2');
  await page.fill('#drinks', '5');
  if ((await query(page)).dr !== '5') fail(where, `drinks amount not in URL: ${await href(page)}`);
  await expectBig('drinks $5', [2], 2, 18, 5);
  await page.click('button[data-pick="18,20,19"]');
  if ((await query(page)).d !== '18,19,20') fail(where, `quick pick URL ${await href(page)}`);
  await page.click('button[data-pick=""]');
  const empty = await page.locator('#result').innerText();
  if (!/Pick at least one dish/.test(empty) || /NaN|undefined/.test(empty)) fail(where, `empty state: ${empty}`);
  if (await page.isVisible('#month')) fail(where, 'month block visible with no dishes');

  // Junk URL
  await open('?d=99,abc,3,3&p=0&t=500&dr=-4');
  if (JSON.stringify(await checked()) !== '[3]') fail(where, `junk URL dishes ${await checked()}`);
  if ((await page.locator('#people').innerText()) !== '4' || (await page.inputValue('#tip')) !== '18') fail(where, 'junk URL defaults');

  // Share
  await open('?d=2,5,9&p=4');
  await page.evaluate(() => { navigator.share = (d) => { window.__shared = d; return Promise.resolve(); }; });
  await page.click('#share');
  const shared = await page.evaluate(() => window.__shared);
  if (!shared || !shared.url.includes('d=2,5,9') || !shared.url.includes('p=4')) fail(where, `Web Share data ${JSON.stringify(shared)}`);
  await page.evaluate(() => { Object.defineProperty(navigator, 'share', { value: undefined }); });
  await page.click('#copy');
  await page.waitForFunction(() => /Link copied/.test(document.getElementById('status').textContent));
  if (!(await page.evaluate(() => navigator.clipboard.readText())).includes('d=2,5,9')) fail(where, 'copy link did not copy the URL');

  // Print view: result + the math table, no controls
  await page.evaluate(() => window.dispatchEvent(new Event('beforeprint')));
  await page.emulateMedia({ media: 'print' });
  const pr = await page.evaluate(() => ({ cta: getComputedStyle(document.querySelector('.cta')).display, form: getComputedStyle(document.querySelector('form')).display,
    bg: getComputedStyle(document.body).backgroundColor, table: document.querySelector('#tbl').getBoundingClientRect().height > 0,
    rows: document.querySelector('#tbl').innerText, scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth }));
  if (pr.cta !== 'none' || pr.form !== 'none' || !pr.table || pr.bg !== 'rgb(255, 255, 255)' || pr.scrollW > pr.clientW) fail(where, `print view: ${JSON.stringify(pr)}`);
  for (const t of ['Real Fettuccine Alfredo', 'Chicken Parmigiana', 'Pan-Seared Steak with Garlic Butter']) if (!pr.rows.includes(t)) fail(where, `print table missing ${t}`);
  await clip('print');
  await page.emulateMedia({ media: 'screen' });
  await page.evaluate(() => window.dispatchEvent(new Event('afterprint')));
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

async function checkTools(browser, base, viewports, fail) {
  for (const [dir, spec] of Object.entries(TOOLS)) {
    const name = spec.slug;
    const src = fs.readFileSync(path.join(ROOT, dir, 'index.html'), 'utf8');
    if (/source-assets/.test(src)) fail(name, 'page references source-assets/');
    if (/(src|href)="\/(?!\/)/.test(src)) fail(name, 'page uses a root-absolute path');
    if (/<script[^>]+src=/i.test(src)) fail(name, 'page loads an external script');
    if (/cookie|localStorage|sessionStorage/i.test(src)) fail(name, 'page uses cookies/storage');
    const og = jpegSize(path.join(ROOT, dir, 'og.jpg'));
    if (!og || og.width !== 1200 || og.height !== 630) fail(name, `og.jpg is ${JSON.stringify(og)}, want 1200x630`);

    for (const vp of viewports) {
      const size = vp.width < 500 ? 'mobile' : 'desktop';
      const where = `${name} ${vp.width}x${vp.height}`;
      const url = `${base}${dir}/`;
      const context = await browser.newContext({ viewport: vp, deviceScaleFactor: vp.width < 500 ? 2 : 1 });
      await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: new URL(base).origin });
      const page = await context.newPage();
      let bytes = 0;
      page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') fail(where, `console ${m.type()}: ${m.text()}`); });
      page.on('pageerror', (e) => fail(where, `page error: ${e.message}`));
      // A favicon still loading when the flow navigates on gets aborted; that's not a broken link.
      page.on('requestfailed', (r) => {
        if (r.failure()?.errorText === 'net::ERR_ABORTED' && /favicon|apple-touch/.test(r.url())) return;
        fail(where, `request failed: ${r.url()} ${r.failure()?.errorText}`);
      });
      page.on('response', async (r) => {
        if (!r.url().startsWith(base)) { fail(where, `external request: ${r.url()}`); return; }
        if (r.status() >= 400) fail(where, `HTTP ${r.status()}: ${r.url()}`);
        const body = await r.body().catch(() => Buffer.alloc(0));
        if (!r.url().endsWith(spec.photo)) bytes += body.length;
      });

      // Every state the flow opens is also checked for sideways scroll and broken output.
      const audit = async (label) => {
        const s = await page.evaluate(() => ({ w: document.documentElement.scrollWidth, c: document.documentElement.clientWidth, t: document.body.innerText }));
        if (s.w > s.c) fail(where, `${label}: horizontal scroll ${s.w} > ${s.c}`);
        if (/\bNaN\b|\bundefined\b|\[object/.test(s.t)) fail(where, `${label}: broken text on page`);
      };
      const open = async (qs) => {
        if (page.url().startsWith(url)) await audit(page.url().slice(url.length) || '(start)');
        await page.goto(url + qs, { waitUntil: 'networkidle' });
      };
      const clip = async (label) => { await page.mouse.move(0, 0); return page.screenshot({ path: path.join(ROOT, 'docs/screens', `${name}-${label}.png`), fullPage: true }); };

      await open('');
      const info = await pageInfo(page);
      const firstLoad = bytes; // page weight = the first load only
      const want = [...spec.payhip.map((l) => `${l}?utm_source=links&utm_medium=tool&utm_campaign=${spec.slug}`)];
      const payhip = info.links.filter((l) => l.includes('payhip.com'));
      if (JSON.stringify(payhip) !== JSON.stringify(want)) fail(where, `Payhip links differ:\n    got  ${JSON.stringify(payhip)}\n    want ${JSON.stringify(want)}`);
      const other = info.links.filter((l) => !l.includes('payhip.com'));
      if (JSON.stringify(other) !== JSON.stringify(spec.other)) fail(where, `other links: ${JSON.stringify(other)}`);
      for (const t of spec.text) if (!info.text.toLowerCase().includes(t.toLowerCase())) fail(where, `missing text: ${t}`);
      for (const img of info.imgs) {
        if (!img.ok) fail(where, `image did not load: ${img.src}`);
        if (!img.alt) fail(where, `image missing alt: ${img.src}`);
      }
      if (!info.title || info.lang !== 'en' || info.h1 !== 1) fail(where, 'title/lang/h1');
      for (const [k, v] of Object.entries(info.meta)) if (!v) fail(where, `missing meta: ${k}`);
      const pageUrl = `https://plazzers.github.io/links/${dir}/`;
      if (info.meta.canonical !== pageUrl || info.meta.ogUrl !== pageUrl) fail(where, 'canonical/og:url mismatch');
      if (info.meta.ogImage !== `${pageUrl}og.jpg` || info.meta.twImage !== `${pageUrl}og.jpg`) fail(where, 'og:image/twitter:image mismatch');
      if (firstLoad > 150 * 1024) fail(where, `page weight ${Math.round(firstLoad / 1024)} KB excluding photo (> 150 KB)`);

      await spec.run({ page, open, fail, where, clip: (l) => clip(`${l}-${size}`) });

      // Screenshot in a filled-in state, then check tap targets there (every control is visible).
      await open(spec.shotQuery);
      await audit('screenshot state');
      const filled = await pageInfo(page);
      for (const s of filled.small) fail(where, `tap target under 48px: "${s.t}" (${s.h}px)`);
      for (const s of filled.footerSmall) fail(where, `footer link under 44px: "${s.t}" (${s.h}px)`);
      if (filled.scrollW > filled.clientW) fail(where, `horizontal scroll: ${filled.scrollW} > ${filled.clientW}`);
      await clip(size);
      console.log(`${where}: tool flow done, ${(firstLoad / 1024).toFixed(1)} KB excl. photo -> docs/screens/${name}-${size}.png`);
      await context.close();
    }
  }
}

module.exports = { checkTools };
