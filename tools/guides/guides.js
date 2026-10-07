// Guide pages: table-of-contents highlight, share button, index search + filter.
(function () {
  'use strict';

  // Table of contents: highlight the section being read.
  var tocLinks = [].slice.call(document.querySelectorAll('.toc a[href^="#"]'));
  if (tocLinks.length) {
    var byId = {};
    tocLinks.forEach(function (a) { (byId[a.getAttribute('href').slice(1)] = byId[a.getAttribute('href').slice(1)] || []).push(a); });
    var heads = Object.keys(byId).map(function (id) { return document.getElementById(id); }).filter(Boolean);
    var ticking = false;
    var update = function () {
      ticking = false;
      var current = null;
      heads.forEach(function (h) { if (h.getBoundingClientRect().top <= window.innerHeight * 0.3) current = h; });
      tocLinks.forEach(function (a) { a.classList.toggle('active', !!current && byId[current.id].indexOf(a) !== -1); });
    };
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }, { passive: true });
    update();
    // On small screens the contents box closes after a jump so the text is visible.
    var toc = document.querySelector('.toc-m');
    tocLinks.forEach(function (a) {
      a.addEventListener('click', function () { if (toc) toc.open = false; });
    });
  }

  // Share: native share sheet, else copy the link, else show it to copy by hand.
  var share = document.querySelector('.share');
  var status = document.querySelector('.share-status');
  if (share && status) {
    var url = share.getAttribute('data-url');
    var title = share.getAttribute('data-title');
    var showLink = function () {
      status.textContent = 'Copy this link: ';
      var input = document.createElement('input');
      input.type = 'text'; input.readOnly = true; input.value = url; input.setAttribute('aria-label', 'Link to this guide');
      status.appendChild(input);
      input.focus(); input.select();
    };
    share.addEventListener('click', function () {
      if (navigator.share) {
        navigator.share({ title: title, url: url }).catch(function () {});
        return;
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url).then(function () {
          status.textContent = 'Link copied — paste it anywhere.';
        }, showLink);
        return;
      }
      showLink();
    });
  }

  // Guides index: search over search.json + category chips. URL keeps ?q= and ?c=.
  var list = document.getElementById('list');
  var input = document.getElementById('q');
  if (list && input) {
    var cards = [].slice.call(list.querySelectorAll('.gcard'));
    var chips = [].slice.call(document.querySelectorAll('.fchip'));
    var count = document.getElementById('count');
    var empty = document.getElementById('empty');
    var index = {};
    var params = new URLSearchParams(location.search);
    var state = { q: params.get('q') || '', c: params.get('c') || '' };
    if (!chips.some(function (b) { return b.getAttribute('data-cat') === state.c; })) state.c = '';
    input.value = state.q;

    var norm = function (s) { return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); };
    var apply = function () {
      var words = norm(state.q).split(/\s+/).filter(Boolean);
      var shown = 0;
      cards.forEach(function (card) {
        var slug = card.getAttribute('data-slug');
        var hay = index[slug] || norm(card.textContent);
        var ok = (!state.c || card.getAttribute('data-cat') === state.c) &&
          words.every(function (w) { return hay.indexOf(w) !== -1; });
        card.hidden = !ok;
        if (ok) shown++;
      });
      chips.forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-cat') === state.c)); });
      count.textContent = shown + (shown === 1 ? ' guide' : ' guides') + (state.q ? ' for “' + state.q + '”' : '');
      empty.hidden = shown !== 0;
      var p = new URLSearchParams();
      if (state.q) p.set('q', state.q);
      if (state.c) p.set('c', state.c);
      var qs = p.toString();
      history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
    };
    input.addEventListener('input', function () { state.q = input.value.trim(); apply(); });
    chips.forEach(function (b) {
      b.addEventListener('click', function () { state.c = b.getAttribute('data-cat'); apply(); });
    });
    fetch('search.json').then(function (r) { return r.json(); }).then(function (data) {
      data.forEach(function (d) {
        index[d.slug] = norm([d.title, d.description, d.keyword, d.category, d.headings.join(' ')].join(' '));
      });
      apply();
    }).catch(function () { apply(); });
    if (state.q || state.c) apply();
  }
})();
