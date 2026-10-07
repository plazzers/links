// Playwright checks for the guide sites (SPEC_V4_GUIDE_SITES.md §6).
// Run from the repo root after the build:  node tests/guides.js
// (if playwright is installed globally: NODE_PATH="$(npm root -g)" node tests/guides.js)
// Serves the repo under /links/ like GitHub Pages and, at 390x844 and 1280x800, opens
// each guides index, 3 articles per channel and the about pages: no console errors,
// no outside requests, no sideways scroll, images load, tap targets >= 44px. It tries
// search + category chips, the table-of-contents highlight and the share button
// (copy-link and show-the-link fallbacks), and saves screenshots to docs/screens/guides-*.png.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const VIEWPORTS = [{ width: 390, height: 844 }, { width: 1280, height: 800 }];
const ARTICLES = {
  walter: ['house-red-flags-at-a-showing', 'radon-basics-for-homeowners', 'knob-and-tube-wiring'],
  sal: ['menu-psychology-tricks', 'copycat-fettuccine-alfredo', 'sunday-marinara-sauce'],
};
const SEARCH = { walter: { q: 'radon', hit: 'radon-basics-for-homeowners', cat: 'older-homes' }, sal: { q: 'alfredo', hit: 'copycat-fettuccine-alfredo', cat: 'copycat' } };
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
  '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.xml': 'application/xml',
};

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

async function run(browser, base, fail) {
  fs.mkdirSync(path.join(ROOT, 'docs/screens'), { recursive: true });
  const shot = (page, name, full = true) => page.screenshot({ path: path.join(ROOT, 'docs/screens', `guides-${name}.png`), fullPage: full });

  for (const vp of VIEWPORTS) {
    const size = vp.width < 500 ? 'mobile' : 'desktop';
    for (const ch of ['walter', 'sal']) {
      const where0 = `${ch} ${vp.width}x${vp.height}`;
      const context = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
      const page = await context.newPage();
      let where = where0;
      page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') fail(where, `console ${m.type()}: ${m.text()}`); });
      page.on('pageerror', (e) => fail(where, `page error: ${e.message}`));
      page.on('requestfailed', (r) => fail(where, `request failed: ${r.url()} ${r.failure()?.errorText}`));
      page.on('response', (r) => {
        if (!r.url().startsWith(base)) fail(where, `external request: ${r.url()}`);
        else if (r.status() >= 400) fail(where, `HTTP ${r.status()}: ${r.url()}`);
      });
      const audit = async (label) => {
        // load lazy images before checking them
        await page.evaluate(async () => {
          for (const img of document.images) { img.loading = 'eager'; if (!img.complete) await new Promise((r) => { img.onload = img.onerror = r; }); }
        });
        const s = await page.evaluate(() => ({
          w: document.documentElement.scrollWidth, c: document.documentElement.clientWidth,
          imgs: [...document.images].map((i) => ({ src: i.currentSrc, ok: i.complete && i.naturalWidth > 0, alt: i.alt })),
          small: [...document.querySelectorAll('main a, main button, header a, main input, main summary')]
            .filter((a) => a.offsetParent !== null && !a.closest('.prose p, .prose li, .prose td, .crumbs, .author p, .sources, .small, .empty, .toc'))
            .map((a) => ({ t: (a.textContent || a.getAttribute('aria-label') || '').trim().slice(0, 40), h: a.getBoundingClientRect().height }))
            .filter((a) => a.h < 44),
          h1: document.querySelectorAll('h1').length,
          text: document.body.innerText,
        }));
        if (s.w > s.c) fail(where, `${label}: horizontal scroll ${s.w} > ${s.c}`);
        for (const i of s.imgs) { if (!i.ok) fail(where, `${label}: image did not load ${i.src}`); if (!i.alt) fail(where, `${label}: image without alt`); }
        for (const t of s.small) fail(where, `${label}: tap target under 44px: "${t.t}" (${t.h}px)`);
        if (s.h1 !== 1) fail(where, `${label}: ${s.h1} h1`);
        if (/\bNaN\b|\bundefined\b|\[object/.test(s.text)) fail(where, `${label}: broken text`);
      };

      // ---- index, search, chips
      where = `${where0} index`;
      await page.goto(`${base}${ch}/guides/`, { waitUntil: 'networkidle' });
      await audit('index');
      const total = await page.locator('#list .gcard').count();
      if (total !== 30) fail(where, `index lists ${total} guides`);
      if ((await page.locator('.start .gcard').count()) !== 3) fail(where, 'Start here should have 3 picks');
      await shot(page, `${ch}-index-${size}`);
      const { q, hit, cat } = SEARCH[ch];
      await page.fill('#q', q);
      const visible = await page.$$eval('#list .gcard:not([hidden])', (els) => els.map((e) => e.dataset.slug));
      if (!visible.includes(hit)) fail(where, `search "${q}" does not find ${hit} (got ${visible.join(', ')})`);
      if (visible.length >= total) fail(where, `search "${q}" did not filter`);
      if (!new URL(page.url()).search.includes(`q=${q}`)) fail(where, 'search not kept in URL');
      if (!(await page.textContent('#count')).includes(q)) fail(where, 'result count does not mention the search');
      await shot(page, `${ch}-search-${size}`, false);
      await page.fill('#q', 'zzqqxx');
      if (await page.locator('#empty').isHidden()) fail(where, 'no "nothing matches" message');
      await page.fill('#q', '');
      await page.click(`.fchip[data-cat="${cat}"]`);
      const cats = await page.$$eval('#list .gcard:not([hidden])', (els) => els.map((e) => e.dataset.cat));
      if (!cats.length || cats.some((c) => c !== cat)) fail(where, `chip ${cat} shows ${[...new Set(cats)]}`);
      if ((await page.getAttribute(`.fchip[data-cat="${cat}"]`, 'aria-pressed')) !== 'true') fail(where, 'chip not pressed');
      await page.goto(`${base}${ch}/guides/?q=${q}&c=${cat}`, { waitUntil: 'networkidle' });
      if ((await page.inputValue('#q')) !== q) fail(where, 'shared search link does not restore the query');

      // ---- articles
      for (const [i, slug] of ARTICLES[ch].entries()) {
        where = `${where0} ${slug}`;
        await page.goto(`${base}${ch}/guides/${slug}/`, { waitUntil: 'networkidle' });
        await audit(slug);
        const info = await page.evaluate(() => ({
          toc: document.querySelectorAll('.toc-d li').length,
          related: document.querySelectorAll('.rcard').length,
          payhip: [...document.querySelectorAll('a[href*="payhip.com"]')].map((a) => a.href),
          ld: [...document.querySelectorAll('script[type="application/ld+json"]')].map((s) => s.textContent),
        }));
        if (info.toc < 3) fail(where, 'table of contents too short');
        if (info.related !== 3) fail(where, `${info.related} related articles`);
        for (const l of info.payhip) {
          const u = new URL(l);
          if (u.searchParams.get('utm_source') !== 'guides' || u.searchParams.get('utm_medium') !== 'article' || u.searchParams.get('utm_campaign') !== slug) fail(where, `utm: ${l}`);
        }
        for (const raw of info.ld) { try { JSON.parse(raw); } catch (e) { fail(where, 'JSON-LD does not parse'); } }
        if (i === 0) await shot(page, `${ch}-article-${size}`);
        else await shot(page, `${ch}-article-${i + 1}-${size}`, false);

        // TOC highlight: jump to the third section and expect its link to light up
        const target = await page.$$eval('.toc-d a', (as) => as[2] && as[2].getAttribute('href'));
        if (target) {
          await page.evaluate((id) => document.getElementById(id).scrollIntoView({ behavior: 'instant' }), target.slice(1));
          await page.waitForTimeout(400);
          const active = await page.$$eval('.toc a.active', (as) => as.map((a) => a.getAttribute('href')));
          if (!active.includes(target)) fail(where, `TOC highlight: want ${target}, got ${active}`);
          await page.evaluate(() => window.scrollTo(0, 0));
        }
      }

      // ---- share: copy-link path, then the show-the-link fallback
      where = `${where0} share`;
      const slug = ARTICLES[ch][0];
      const url = `https://plazzers.github.io/links/${ch}/guides/${slug}/`;
      await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: new URL(base).origin });
      await page.addInitScript(() => { try { delete Navigator.prototype.share; } catch (e) {} Object.defineProperty(navigator, 'share', { value: undefined, configurable: true }); });
      await page.goto(`${base}${ch}/guides/${slug}/`, { waitUntil: 'networkidle' });
      await page.click('.share');
      await page.waitForFunction(() => document.querySelector('.share-status').textContent.length > 0);
      const copied = await page.textContent('.share-status');
      if (!/copied/i.test(copied)) fail(where, `copy path: status "${copied}"`);
      const clip = await page.evaluate(() => navigator.clipboard.readText());
      if (clip !== url) fail(where, `clipboard has "${clip}", want ${url}`);
      await page.addInitScript(() => { Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true }); });
      await page.goto(`${base}${ch}/guides/${slug}/`, { waitUntil: 'networkidle' });
      await page.click('.share');
      const shown = await page.inputValue('.share-status input').catch(() => null);
      if (shown !== url) fail(where, `fallback shows "${shown}", want ${url}`);
      await audit('share fallback');
      await page.locator('.art-head').screenshot({ path: path.join(ROOT, 'docs/screens', `guides-${ch}-share-${size}.png`) });

      // ---- about
      where = `${where0} about`;
      await page.goto(`${base}${ch}/about/`, { waitUntil: 'networkidle' });
      await audit('about');
      await shot(page, `${ch}-about-${size}`, false);

      // ---- link page button + tool strip
      where = `${where0} link page`;
      await page.goto(`${base}${ch}/`, { waitUntil: 'networkidle' });
      await page.click('a[href="guides/"]');
      await page.waitForURL(`${base}${ch}/guides/`);
      console.log(`${where0}: guides index, ${ARTICLES[ch].length} articles, search, share, about checked`);
      await context.close();
    }
  }
}

module.exports = { checkGuides: run };

if (require.main === module) {
  (async () => {
    const server = await serve();
    const base = `http://127.0.0.1:${server.address().port}/links/`;
    const browser = await chromium.launch(fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {});
    const failures = [];
    await run(browser, base, (where, msg) => failures.push(`[${where}] ${msg}`));
    await browser.close();
    server.close();
    if (failures.length) {
      console.error(`\n${failures.length} problem(s):\n` + failures.join('\n'));
      process.exit(1);
    }
    console.log('\nAll guide page checks passed. Screenshots in docs/screens/guides-*.png');
  })();
}
