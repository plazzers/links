// Free YouTube Title Scorer — same transparent rules as the Faceless Creator
// Kit's Title & Thumbnail Lab. Runs entirely in the browser; nothing is sent.
(function () {
  'use strict';

  var POWER = ['never', 'stop', 'mistake', 'avoid', 'secret', 'wrong', 'worst', 'hidden', 'problem', 'expensive',
    'warning', 'truth', 'nobody', 'why', "don't", 'ruin', 'regret', 'skip', 'trick', 'damage', 'before',
    'fail', 'danger', 'cost', 'really'];
  var CLICKBAIT = ["you won't believe", 'shocking', 'insane', 'mind-blowing', 'mind blowing', 'gone wrong',
    'unbelievable', 'jaw-dropping', 'must see'];
  var WEAK_STARTS = ['how i', 'in this video', "in today's video", 'this video'];

  var reEscape = function (s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); };
  var norm = function (s) { return String(s == null ? '' : s).toLowerCase().replace(/[’]/g, "'"); };

  function hasPhrase(text, phrase) {
    var p = norm(phrase).trim();
    if (!p) return false;
    var re = new RegExp("(^|[^\\p{L}\\p{N}'])" + reEscape(p).replace(/\s+/g, '\\s+') + "(e?s)?(?=$|[^\\p{L}\\p{N}'])", 'u');
    return re.test(norm(text));
  }
  function capsWords(text) {
    return (String(text).match(/[\p{L}']+/gu) || []).filter(function (w) {
      var l = w.replace(/'/g, '');
      return l.length >= 2 && l === l.toUpperCase() && l !== l.toLowerCase();
    });
  }
  function wordList(input) {
    var seen = {};
    return String(input || '').split(/[\n,]+/).map(function (x) { return x.trim(); })
      .filter(function (x) { var k = x.toLowerCase(); if (!x || seen[k]) return false; seen[k] = 1; return true; });
  }

  function scoreTitle(title, keywords) {
    var t = String(title || '').trim();
    if (!t) return { score: 0, reasons: [] };
    var reasons = [];
    var add = function (points, max, level, text) { reasons.push({ points: points, max: max, level: level, text: text }); };
    var len = t.length;
    if (len >= 40 && len <= 65) add(20, 20, 'good', len + ' characters — in the ideal 40–65 range.');
    else if (len >= 30 && len <= 75) add(10, 20, 'warn', len + ' characters — ' + (len < 40 ? 'a bit short' : 'a bit long') + ' (ideal 40–65).');
    else add(0, 20, 'bad', len + ' characters — ' + (len < 40 ? 'too short' : 'too long') + ' (ideal 40–65).');

    var num = t.match(/\d+/);
    if (num) add(15, 15, 'good', 'Has a number (' + num[0] + ').');
    else add(0, 15, 'warn', 'No number. Numbers ("7 Things") usually help.');

    var pw = POWER.filter(function (w) { return hasPhrase(t, w); });
    if (pw.length) add(15, 15, 'good', 'Curiosity/pain word: ' + pw.join(', ') + '.');
    else add(0, 15, 'warn', 'No curiosity/pain word (like never, mistake, hidden).');

    var low = norm(t);
    var weak = WEAK_STARTS.filter(function (w) { return low.indexOf(w) === 0; })[0];
    if (weak) add(0, 15, 'bad', 'Starts weak ("' + t.slice(0, weak.length) + '…"). Lead with the payoff.');
    else add(15, 15, 'good', 'Starts strong.');

    var caps = capsWords(t);
    if (caps.length > 2) add(0, 10, 'bad', caps.length + ' ALL CAPS words (' + caps.join(', ') + '). Use 2 at most.');
    else add(10, 10, 'good', caps.length ? caps.length + ' ALL CAPS word' + (caps.length === 1 ? '' : 's') + ' — fine.' : 'No shouting in capitals.');

    var cb = CLICKBAIT.filter(function (w) { return hasPhrase(t, w); });
    if (cb.length) add(0, 10, 'bad', 'Clickbait words: ' + cb.join(', ') + '.');
    else add(10, 10, 'good', 'No clickbait words.');

    var kws = wordList(keywords);
    var kw = kws.filter(function (w) { return hasPhrase(t, w); });
    if (kw.length) add(15, 15, 'good', 'Keyword: ' + kw.join(', ') + '.');
    else add(0, 15, 'warn', kws.length ? 'Your keyword is missing (' + kws.join(', ') + ').' : 'No keyword entered — add the phrase people search for.');

    return { score: reasons.reduce(function (s, r) { return s + r.points; }, 0), reasons: reasons };
  }
  window.scoreTitle = scoreTitle; // used by the automated checks

  var ids = ['t1', 't2', 't3'];
  var inputs = ids.map(function (id) { return document.getElementById(id); });
  var kwInput = document.getElementById('kw');
  var out = document.getElementById('results');
  var copyBtn = document.getElementById('copy-best');
  var shareBtn = document.getElementById('share-link');
  var status = document.getElementById('tool-status');
  var best = '';

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function render() {
    var scored = inputs.map(function (inp, i) {
      return { i: i, title: inp.value.trim(), res: scoreTitle(inp.value, kwInput.value) };
    }).filter(function (x) { return x.title; });
    if (!scored.length) {
      out.innerHTML = '<p class="note">Type or paste a title above to see its score.</p>';
      copyBtn.hidden = true; best = '';
      return;
    }
    var top = scored.reduce(function (a, b) { return b.res.score > a.res.score ? b : a; });
    var tie = scored.filter(function (x) { return x.res.score === top.res.score; }).length > 1;
    best = top.title;
    out.innerHTML = scored.map(function (x) {
      var isBest = x === top && scored.length > 1 && !tie;
      return '<div class="result' + (isBest ? ' best' : '') + '" data-score="' + x.res.score + '">' +
        '<p class="small">Title ' + 'ABC'[x.i] + (isBest ? '<span class="badge">Best</span>' : '') + '</p>' +
        '<h3>' + esc(x.title) + '</h3>' +
        '<p class="score">' + x.res.score + '<small>/100</small></p>' +
        '<ul class="reasons">' + x.res.reasons.map(function (r) {
          return '<li><span class="lvl ' + r.level + '" aria-hidden="true"></span><span>' + esc(r.text) +
            '</span><span class="pts">' + r.points + '/' + r.max + '</span></li>';
        }).join('') + '</ul></div>';
    }).join('');
    out.className = 'results' + (scored.length > 1 ? ' three' : '');
    copyBtn.hidden = false;
    copyBtn.textContent = scored.length > 1 ? (tie ? 'Copy the first top-scoring title' : 'Copy the best title') : 'Copy this title';
  }

  function saveUrl() {
    var p = new URLSearchParams();
    inputs.forEach(function (inp, i) { if (inp.value.trim()) p.set(ids[i], inp.value.trim()); });
    if (kwInput.value.trim()) p.set('kw', kwInput.value.trim());
    var qs = p.toString();
    history.replaceState(null, '', location.pathname + (qs ? '?' + qs : ''));
  }

  var timer;
  function onInput() { render(); clearTimeout(timer); timer = setTimeout(saveUrl, 300); status.textContent = ''; }
  inputs.concat(kwInput).forEach(function (el) { el.addEventListener('input', onInput); });

  copyBtn.addEventListener('click', function () {
    if (!best) return;
    var done = function () { status.textContent = 'Copied: ' + best; };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(best).then(done, function () { status.textContent = best; });
    else status.textContent = best;
  });
  shareBtn.addEventListener('click', function () {
    saveUrl();
    var url = location.href;
    if (navigator.share) { navigator.share({ title: document.title, url: url }).catch(function () {}); return; }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(function () { status.textContent = 'Link copied — it opens with these titles.'; }, function () { status.textContent = url; });
    else status.textContent = url;
  });
  document.getElementById('example').addEventListener('click', function () {
    inputs[0].value = 'In this video I talk about telescopes';
    inputs[1].value = '7 Things You Can See Tonight Without a Telescope';
    inputs[2].value = 'SHOCKING Night Sky SECRETS You WON\'T Believe';
    kwInput.value = 'telescope';
    onInput();
  });

  var params = new URLSearchParams(location.search);
  ids.forEach(function (id, i) { if (params.get(id)) inputs[i].value = params.get(id); });
  if (params.get('kw')) kwInput.value = params.get('kw');
  render();
})();
