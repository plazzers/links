// Playwright checks for the Faceless Creator Kit site (creator-kit/).
// Run from the repo root:  node tests/kit.js
// (needs the `playwright` npm package; if installed globally:
//  NODE_PATH="$(npm root -g)" node tests/kit.js)
// Serves the repo under /links/ like GitHub Pages and checks the landing page,
// both free tools (with sample input) and two guides at 390x844 and 1280x800:
// no console errors, nothing loaded from other sites, no sideways scroll,
// images load, tap targets. Screenshots go to docs/screens/kit-*.png.
const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const VIEWPORTS = [{ width: 390, height: 844 }, { width: 1280, height: 800 }];
const PAGES = [
  ['landing', 'creator-kit/'],
  ['title-scorer', 'creator-kit/tools/title-scorer/'],
  ['csv-checker', 'creator-kit/tools/pinterest-csv-checker/'],
  ['guides-index', 'creator-kit/guides/'],
  ['guide-csv', 'creator-kit/guides/pinterest-bulk-upload-csv/'],
  ['guide-titles', 'creator-kit/guides/youtube-title-formulas/'],
];
const TYPES = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.jpg': 'image/jpeg',
  '.png': 'image/png', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.woff2': 'font/woff2', '.csv': 'text/csv',
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

async function titleScorer(page, fail, where) {
  await page.click('#example');
  const cards = await page.$$eval('.result', (els) => els.map((e) => ({ score: +e.dataset.score, best: e.classList.contains('best'), title: e.querySelector('h3').textContent })));
  const want = [45, 85, 50]; // A: 37 chars (10) + strong-start miss; B: the kit's demo title; C: caps + clickbait
  if (JSON.stringify(cards.map((c) => c.score)) !== JSON.stringify(want)) fail(where, `scores ${JSON.stringify(cards.map((c) => c.score))}, want ${JSON.stringify(want)}`);
  if (!cards[1] || !cards[1].best || cards.filter((c) => c.best).length !== 1) fail(where, 'title B should be marked best');
  const reasons = await page.$$eval('.result:nth-child(3) .reasons li', (els) => els.map((e) => e.textContent));
  if (!reasons.some((r) => /ALL CAPS/.test(r)) || !reasons.some((r) => /Clickbait words: you won't believe, shocking/i.test(r))) fail(where, `caps/clickbait reasons missing: ${reasons}`);
  if (await page.isHidden('#copy-best')) fail(where, 'copy button hidden');
  // shared link restores the titles
  await page.waitForTimeout(400);
  const url = page.url();
  if (!/t2=7\+Things/.test(url) || !/kw=telescope/.test(url)) fail(where, `URL not updated: ${url}`);
  await page.goto(url, { waitUntil: 'networkidle' });
  const restored = await page.$$eval('.result', (els) => els.length);
  if (restored !== 3) fail(where, `shared link restored ${restored} results`);
  // copy button (clipboard may be denied headless; the status line must change)
  await page.click('#copy-best');
  await page.waitForTimeout(150);
  const st = await page.textContent('#tool-status');
  if (!/7 Things You Can See Tonight/.test(st)) fail(where, `copy status: ${st}`);
}

async function csvChecker(page, fail, where) {
  await page.click('#sample');
  const summary = await page.textContent('#summary');
  const m = summary.match(/(\d+) pins? · (\d+) errors? · (\d+) warnings?/);
  if (!m || +m[1] !== 3 || +m[2] < 6) fail(where, `summary: ${summary}`);
  const text = await page.textContent('#report');
  for (const s of ['should be named exactly "Title"', 'drive.google.com', 'is in the past', 'Exact duplicate of line 2', 'Title is 108 characters', 'Link is not a valid web address', 'differ only in capitals', 'Night Sky Tips (3)']) {
    if (!text.includes(s)) fail(where, `report is missing "${s}"`);
  }
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('.dl')]);
  const fixed = fs.readFileSync(await dl.path(), 'utf8');
  const lines = fixed.trim().split('\r\n');
  if (lines[0] !== '"Title","Media URL","Pinterest board","Thumbnail","Description","Link","Publish date","Keywords"') fail(where, `fixed header: ${lines[0]}`);
  if (lines.length !== 4) fail(where, `fixed file has ${lines.length - 1} rows, want 3`);
  if (!/T14:00:00/.test(fixed) || /14:00"/.test(fixed.replace(/T14:00:00/g, ''))) fail(where, 'date not normalized');
  if (/Night sky tips|night sky tips/.test(fixed)) fail(where, 'board spelling not merged');
  if (!/003%20moon\.jpg/.test(fixed)) fail(where, 'space in media URL not encoded');
  // the repo's own kit CSV must pass with zero errors (fixed "now" before the schedule starts)
  const own = fs.readFileSync(path.join(ROOT, 'pins/pinterest-bulk-kit.csv'), 'utf8');
  const res = await page.evaluate((t) => { const r = window.checkPinCsv(t, new Date('2026-10-10T00:00:00Z')); return { e: r.errors, w: r.warnings, n: r.pins, b: r.boards.length, issues: r.issues.slice(0, 5) }; }, own);
  if (res.e !== 0 || res.w !== 0 || res.n !== 30 || res.b !== 3) fail(where, `own CSV: ${JSON.stringify(res)}`);
  // semicolon + BOM + 250 rows -> split into 2 files
  const big = await page.evaluate(() => {
    let t = '﻿Title;Media URL;Pinterest board;Thumbnail;Description;Link;Publish date;Keywords\n';
    for (let i = 0; i < 250; i++) t += `Pin ${i};https://x.github.io/p/${i}.jpg;Board;;Desc ${i};https://x.com/;2030-01-01T10:00:00;a\n`;
    const r = window.checkPinCsv(t, new Date('2026-10-10T00:00:00Z'));
    return { files: r.files.length, errors: r.errors, msgs: r.issues.map((x) => x.msg).join(' | ') };
  });
  if (big.files !== 2 || !/semicolons/.test(big.msgs) || !/byte-order mark/.test(big.msgs)) fail(where, `big file: ${JSON.stringify(big).slice(0, 300)}`);
}

async function guidesIndex(page, fail, where) {
  await page.fill('#q', 'csv');
  await page.waitForTimeout(100);
  const n = await page.$$eval('.gcard', (els) => els.filter((e) => !e.hidden).length);
  if (n < 2 || n > 6) fail(where, `search "csv" shows ${n} guides`);
  await page.fill('#q', '');
  await page.click('.fchip[data-cat="youtube"]');
  const y = await page.$$eval('.gcard', (els) => els.filter((e) => !e.hidden).map((e) => e.dataset.cat));
  if (!y.length || y.some((c) => c !== 'youtube')) fail(where, `youtube filter: ${y}`);
  await page.click('.fchip[data-cat=""]');
}

(async () => {
  const server = await serve();
  const base = `http://127.0.0.1:${server.address().port}/links/`;
  const browser = await chromium.launch(fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {});
  const failures = [];
  const fail = (where, msg) => failures.push(`[${where}] ${msg}`);
  fs.mkdirSync(path.join(ROOT, 'docs/screens'), { recursive: true });

  for (const [name, rel] of PAGES) {
    for (const vp of VIEWPORTS) {
      const where = `${name} ${vp.width}x${vp.height}`;
      const context = await browser.newContext({ viewport: vp, deviceScaleFactor: vp.width < 500 ? 2 : 1, acceptDownloads: true, reducedMotion: 'reduce' });
      const page = await context.newPage();
      page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') fail(where, `console ${m.type()}: ${m.text()}`); });
      page.on('pageerror', (e) => fail(where, `page error: ${e.message}`));
      page.on('requestfailed', (r) => { if (!r.url().startsWith('blob:')) fail(where, `request failed: ${r.url()}`); });
      page.on('request', (r) => { const u = r.url(); if (!u.startsWith(base) && !u.startsWith('blob:') && !u.startsWith('data:')) fail(where, `external request: ${u}`); });
      page.on('response', (r) => { if (r.status() >= 400) fail(where, `HTTP ${r.status()}: ${r.url()}`); });
      await page.goto(base + rel, { waitUntil: 'networkidle' });
      // load lazy images
      await page.evaluate(async () => { for (const i of document.images) { i.loading = 'eager'; } window.scrollTo(0, document.body.scrollHeight); });
      await page.waitForFunction(() => [...document.images].every((i) => getComputedStyle(i).display === 'none' || (i.complete && i.naturalWidth > 0)), null, { timeout: 10000 }).catch(() => {});
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 600) { window.scrollTo(0, y); await new Promise((r) => setTimeout(r, 30)); }
        window.scrollTo(0, 0);
      });
      await page.waitForFunction(() => [...document.images].every((i) => getComputedStyle(i).display === 'none' || (i.complete && i.naturalWidth > 0)), null, { timeout: 10000 }).catch(() => {});

      const info = await page.evaluate(() => ({
        scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth,
        imgs: [...document.images].filter((i) => getComputedStyle(i).display !== 'none').map((i) => ({ src: i.currentSrc, ok: i.complete && i.naturalWidth > 0, alt: i.getAttribute('alt') })),
        small: [...document.querySelectorAll('main a.btn, main button, .top nav a, .foot a')]
          .filter((a) => a.offsetParent !== null)
          .map((a) => ({ t: a.textContent.trim().slice(0, 30), h: a.getBoundingClientRect().height })).filter((a) => a.h < 44),
        h1: document.querySelectorAll('h1').length,
      }));
      if (info.scrollW > info.clientW) fail(where, `horizontal scroll ${info.scrollW} > ${info.clientW}`);
      for (const i of info.imgs) { if (!i.ok) fail(where, `image did not load: ${i.src}`); if (i.alt === null) fail(where, `image without alt: ${i.src}`); }
      for (const s of info.small) fail(where, `tap target under 44px: "${s.t}" (${s.h}px)`);
      if (info.h1 !== 1) fail(where, `${info.h1} h1`);

      if (name === 'title-scorer') await titleScorer(page, fail, where);
      if (name === 'csv-checker') await csvChecker(page, fail, where);
      if (name === 'guides-index') await guidesIndex(page, fail, where);
      if (name === 'landing') {
        const buys = await page.$$eval('a[href*="payhip.com"]', (as) => as.map((a) => a.getAttribute('href')));
        if (buys.length < 4 || buys.some((h) => !/utm_source=kitsite&utm_medium=landing&utm_campaign=/.test(h))) fail(where, `buy links: ${buys}`);
      }
      const after = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
      if (after > 0) fail(where, `horizontal scroll after interaction: ${after}px`);

      const shot = path.join(ROOT, 'docs/screens', `kit-${name}-${vp.width < 500 ? 'mobile' : 'desktop'}.png`);
      await page.screenshot({ path: shot, fullPage: true });
      console.log(`${where}: ok -> ${path.relative(ROOT, shot)}`);
      await context.close();
    }
  }
  await browser.close();
  server.close();
  if (failures.length) {
    console.error(`\n${failures.length} problem(s):\n` + failures.join('\n'));
    process.exit(1);
  }
  console.log('\nAll kit browser checks passed.');
})();
