// Creator Kit site: table-of-contents highlight, share button, guide search + filter.
(function () {
  'use strict';
  var $$ = function (s) { return [].slice.call(document.querySelectorAll(s)); };

  // Table of contents: highlight the section being read.
  var tocLinks = $$('.toc a[href^="#"]');
  if (tocLinks.length) {
    var heads = tocLinks.map(function (a) { return document.getElementById(a.getAttribute('href').slice(1)); });
    var update = function () {
      var cur = null;
      heads.forEach(function (h) { if (h && h.getBoundingClientRect().top <= window.innerHeight * 0.3) cur = h; });
      tocLinks.forEach(function (a, i) { a.classList.toggle('active', !!cur && heads[i] && heads[i].id === cur.id); });
    };
    var ticking = false;
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; requestAnimationFrame(function () { ticking = false; update(); }); }
    }, { passive: true });
    update();
    var tocM = document.querySelector('.toc-m');
    tocLinks.forEach(function (a) { a.addEventListener('click', function () { if (tocM) tocM.open = false; }); });
  }

  // Share: native share sheet, else copy the link, else show it.
  $$('.share').forEach(function (btn) {
    var status = btn.parentNode.parentNode.querySelector('.share-status') || document.querySelector('.share-status');
    btn.addEventListener('click', function () {
      var url = btn.getAttribute('data-url') || location.href;
      var title = btn.getAttribute('data-title') || document.title;
      var show = function () {
        if (!status) return;
        status.textContent = 'Copy this link: ';
        var i = document.createElement('input');
        i.type = 'text'; i.readOnly = true; i.value = url; i.setAttribute('aria-label', 'Link to this page');
        status.appendChild(i); i.select();
      };
      if (navigator.share) { navigator.share({ title: title, url: url }).catch(function () {}); return; }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () { if (status) status.textContent = 'Link copied.'; }, show);
      } else { show(); }
    });
  });

  // Guide index: search box + category chips (works on the page's own cards).
  var q = document.getElementById('q');
  var cards = $$('.gcard');
  if (q && cards.length) {
    var chips = $$('.fchip');
    var count = document.getElementById('count');
    var empty = document.getElementById('empty');
    var cat = '';
    var norm = function (s) { return s.toLowerCase().replace(/[^a-z0-9 ]+/g, ' '); };
    var apply = function () {
      var words = norm(q.value).split(/\s+/).filter(Boolean);
      var n = 0;
      cards.forEach(function (c) {
        var text = norm(c.getAttribute('data-text') || c.textContent);
        var ok = (!cat || c.getAttribute('data-cat') === cat) && words.every(function (w) { return text.indexOf(w) !== -1; });
        c.hidden = !ok;
        if (ok) n++;
      });
      if (count) count.textContent = n + (n === 1 ? ' guide' : ' guides');
      if (empty) empty.hidden = n !== 0;
    };
    chips.forEach(function (b) {
      b.addEventListener('click', function () {
        cat = b.getAttribute('data-cat');
        chips.forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        apply();
      });
    });
    q.addEventListener('input', apply);
    var p = new URLSearchParams(location.search);
    if (p.get('q')) q.value = p.get('q');
    if (p.get('c')) chips.forEach(function (b) { if (b.getAttribute('data-cat') === p.get('c')) b.click(); });
    apply();
  }
})();
