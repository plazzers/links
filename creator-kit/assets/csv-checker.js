// Free Pinterest bulk-upload CSV checker. Runs entirely in the browser:
// the file is read on your device and never uploaded anywhere.
(function () {
  'use strict';

  var HEADER = ['Title', 'Media URL', 'Pinterest board', 'Thumbnail', 'Description', 'Link', 'Publish date', 'Keywords'];
  var ALIASES = {
    'title': 0, 'pin title': 0,
    'media url': 1, 'mediaurl': 1, 'image url': 1, 'image': 1, 'media': 1,
    'pinterest board': 2, 'board': 2, 'board name': 2,
    'thumbnail': 3,
    'description': 4, 'pin description': 4,
    'link': 5, 'destination link': 5, 'url': 5, 'destination url': 5,
    'publish date': 6, 'publishdate': 6, 'date': 6, 'publish_date': 6, 'schedule': 6,
    'keywords': 7, 'keyword': 7, 'tags': 7
  };
  var TITLE_MAX = 100, DESC_MAX = 500, MAX_ROWS = 200;
  var MEDIA_EXT = /\.(jpe?g|png|webp|gif|mp4|mov|m4v)$/i;
  var VIDEO_EXT = /\.(mp4|mov|m4v)$/i;
  var SHARE_HOSTS = /(^|\.)((drive|docs|photos)\.google\.com|dropbox\.com|1drv\.ms|onedrive\.live\.com|icloud\.com|photos\.app\.goo\.gl)$/i;

  function parseCsv(text) {
    var delim = ',';
    var first = text.split(/\r?\n/, 1)[0] || '';
    var count = function (ch) { return first.split(ch).length - 1; };
    if (count(',') === 0 && count(';') > 0) delim = ';';
    else if (count(',') === 0 && count('\t') > 0) delim = '\t';
    var rows = [], row = [], field = '', i = 0, q = false, quotedAny = false;
    while (i < text.length) {
      var c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { field += '"'; i += 2; continue; } q = false; i++; continue; }
        field += c; i++; continue;
      }
      if (c === '"' && field === '') { q = true; quotedAny = true; i++; continue; }
      if (c === delim) { row.push(field); field = ''; i++; continue; }
      if (c === '\r') { i++; continue; }
      if (c === '\n') { row.push(field); rows.push(row); row = []; field = ''; i++; continue; }
      field += c; i++;
    }
    if (field !== '' || row.length) { row.push(field); rows.push(row); }
    return { rows: rows, delim: delim, unclosed: q, quoted: quotedAny };
  }

  function trimTo(s, max) {
    if (s.length <= max) return s;
    var cut = s.slice(0, max);
    var sentence = cut.match(/^[\s\S]*[.!?](?=\s|$)/);
    if (sentence && sentence[0].length > max * 0.6) return sentence[0].trim();
    var sp = cut.lastIndexOf(' ');
    return (sp > max * 0.6 ? cut.slice(0, sp) : cut).replace(/[\s,;:–-]+$/, '');
  }

  function validDate(y, mo, d, h, mi, s) {
    var dt = new Date(Date.UTC(+y, +mo - 1, +d, +h, +mi, +s));
    return dt.getUTCFullYear() === +y && dt.getUTCMonth() === +mo - 1 && dt.getUTCDate() === +d && +h < 24 && +mi < 60 && +s < 60 ? dt : null;
  }

  // Returns {value, date, fixed, error}
  function fixDate(raw) {
    var s = raw.trim();
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})$/);
    if (m) {
      var dt = validDate(m[1], m[2], m[3], m[4], m[5], m[6]);
      return dt ? { value: s, date: dt } : { error: 'is not a real date/time' };
    }
    m = s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T]+(\d{1,2}):(\d{2})(?::(\d{2}))?)?\s*(?:Z|UTC)?$/i);
    if (m) {
      var p = function (x) { return String(x).padStart(2, '0'); };
      var hasTime = m[4] != null;
      var v = m[1] + '-' + p(m[2]) + '-' + p(m[3]) + 'T' + (hasTime ? p(m[4]) + ':' + m[5] + ':' + (m[6] || '00') : '12:00:00');
      var dt2 = validDate(m[1], m[2], m[3], hasTime ? m[4] : 12, hasTime ? m[5] : 0, m[6] || 0);
      if (!dt2) return { error: 'is not a real date/time' };
      return { value: v, date: dt2, fixed: true, noTime: !hasTime };
    }
    return { error: 'is not in the format YYYY-MM-DDTHH:MM:SS (for example 2026-10-12T14:00:00)' };
  }

  function check(text, now) {
    now = now || new Date();
    var issues = [], fixes = [];
    var add = function (level, row, msg) { issues.push({ level: level, row: row, msg: msg }); };
    if (text.charCodeAt(0) === 0xfeff) { text = text.slice(1); fixes.push('Removed the invisible byte-order mark at the start of the file.'); add('warning', null, 'The file starts with a byte-order mark (BOM). Some tools choke on it.'); }
    if (!text.trim()) return { issues: [{ level: 'error', row: null, msg: 'The file is empty.' }], fixes: [], rows: [], boards: [], fixedCsv: null, errors: 1, warnings: 0, pins: 0 };
    var parsed = parseCsv(text);
    if (parsed.unclosed) add('error', null, 'A quote (") is opened but never closed, so part of the file reads as one field. Check descriptions that contain quotes: write them as "" inside a quoted field.');
    if (parsed.delim !== ',') { add('warning', null, 'The file uses ' + (parsed.delim === ';' ? 'semicolons' : 'tabs') + ' instead of commas between columns.'); fixes.push('Switched the separator to commas.'); }
    var rows = parsed.rows;
    var head = rows.shift().map(function (h) { return h.trim(); });

    // Header
    var map = [], seen = {};
    head.forEach(function (h, i) {
      var k = h.toLowerCase().replace(/[_\s]+/g, ' ').trim();
      var idx = ALIASES.hasOwnProperty(k) ? ALIASES[k] : -1;
      if (idx === -1 && h) add('warning', 1, 'Unknown column "' + h + '" — Pinterest ignores or rejects it. It is left out of the corrected file.');
      else if (idx !== -1 && seen[idx] != null) { add('error', 1, 'Column "' + HEADER[idx] + '" appears twice.'); idx = -1; }
      else if (idx !== -1 && h !== HEADER[idx]) { add('error', 1, 'Column "' + h + '" should be named exactly "' + HEADER[idx] + '".'); fixes.push('Renamed column "' + h + '" to "' + HEADER[idx] + '".'); }
      if (idx !== -1) seen[idx] = i;
      map[i] = idx;
    });
    var exact = head.length === HEADER.length && head.every(function (h, i) { return h === HEADER[i]; });
    HEADER.forEach(function (h, idx) {
      if (seen[idx] == null) {
        var required = idx === 1 || idx === 2;
        add(required ? 'error' : 'warning', 1, 'Missing column "' + h + '"' + (required ? ' (required).' : '.'));
        fixes.push('Added the missing column "' + h + '"' + (required ? ' (you still need to fill it in)' : '') + '.');
      }
    });
    if (!exact && Object.keys(seen).length === HEADER.length && !issues.some(function (x) { return x.row === 1 && x.level === 'error'; })) {
      add('warning', 1, 'The columns are not in Pinterest\'s template order.');
      fixes.push('Put the columns in the template order: ' + HEADER.join(', ') + '.');
    }

    // Rows
    var out = [], boards = {}, mediaSeen = {}, titleSeen = {}, rowSeen = {}, lastDate = null, outOfOrder = 0;
    rows.forEach(function (r, n) {
      var line = n + 2;
      if (r.every(function (f) { return !f.trim(); })) { if (n < rows.length - 1 || r.length > 1) fixes.push('Removed the empty row on line ' + line + '.'); return; }
      if (r.length !== head.length) add(r.length > head.length ? 'error' : 'warning', line, 'Has ' + r.length + ' fields but the header has ' + head.length + '. A comma inside an unquoted field is the usual cause.');
      var v = HEADER.map(function (_, idx) { var i = seen[idx]; return i == null ? '' : String(r[i] == null ? '' : r[i]); });
      var orig = v.slice();
      v = v.map(function (x) { return x.replace(/\s+/g, ' ').trim(); });
      if (v[4] !== orig[4] && orig[4].trim().replace(/\s+/g, ' ') === v[4] && /\n/.test(orig[4])) fixes.push('Line ' + line + ': joined the line breaks in the description.');

      var key = v.join('\u0001');
      if (rowSeen[key]) { add('error', line, 'Exact duplicate of line ' + rowSeen[key] + '.'); fixes.push('Removed line ' + line + ' (exact duplicate of line ' + rowSeen[key] + ').'); return; }
      rowSeen[key] = line;

      // Title
      if (!v[0]) add('warning', line, 'No title. Pinterest allows it, but a title helps people and search.');
      else if (v[0].length > TITLE_MAX) { add('error', line, 'Title is ' + v[0].length + ' characters (max ' + TITLE_MAX + ').'); v[0] = trimTo(v[0], TITLE_MAX); fixes.push('Line ' + line + ': shortened the title to ' + v[0].length + ' characters.'); }
      if (v[0]) { var tk = v[0].toLowerCase(); if (titleSeen[tk]) add('warning', line, 'Same title as line ' + titleSeen[tk] + '. Vary titles so pins don\'t look like duplicates.'); else titleSeen[tk] = line; }

      // Media URL
      var media = v[1];
      if (!media) add('error', line, 'No Media URL. Every pin needs a public link to its image or video.');
      else {
        if (/\s/.test(media)) { media = media.replace(/ /g, '%20'); v[1] = media; fixes.push('Line ' + line + ': replaced spaces in the Media URL with %20.'); add('error', line, 'The Media URL contains spaces.'); }
        var u = null;
        try { u = new URL(media); } catch (e) { u = null; }
        if (!u || !/^https?:$/.test(u.protocol)) add('error', line, 'Media URL is not a web address (it must start with https://): ' + media.slice(0, 80));
        else {
          if (u.protocol === 'http:') add('warning', line, 'Media URL uses http:// — use https:// if your host supports it.');
          if (SHARE_HOSTS.test(u.hostname)) add('error', line, 'Media URL points to a sharing page (' + u.hostname + '), not the image file itself. Pinterest needs a direct, public link to the file.');
          else if (!MEDIA_EXT.test(u.pathname)) add('warning', line, 'Media URL doesn\'t end in .jpg, .png or another image/video extension. Make sure it opens the file itself, not a web page.');
          if (/^(localhost|127\.|192\.168\.|10\.)/.test(u.hostname)) add('error', line, 'Media URL points to your own computer or network; Pinterest can\'t reach it.');
        }
        if (mediaSeen[media]) add('warning', line, 'Same Media URL as line ' + mediaSeen[media] + '. The same image twice looks like a duplicate pin.');
        else mediaSeen[media] = line;
      }

      // Board
      if (!v[2]) add('error', line, 'No Pinterest board. Create the board first and type its name exactly.');
      else boards[v[2]] = (boards[v[2]] || []).concat(line);

      // Thumbnail
      if (v[3] && !VIDEO_EXT.test(media)) { add('warning', line, 'Thumbnail is only used for video pins; this pin is an image.'); v[3] = ''; fixes.push('Line ' + line + ': cleared the Thumbnail (image pin).'); }

      // Description
      if (v[4].length > DESC_MAX) { add('error', line, 'Description is ' + v[4].length + ' characters (max ' + DESC_MAX + ').'); v[4] = trimTo(v[4], DESC_MAX); fixes.push('Line ' + line + ': shortened the description to ' + v[4].length + ' characters.'); }
      else if (!v[4]) add('info', line, 'No description. A sentence or two with your keywords helps pins get found.');

      // Link
      if (v[5]) {
        var lu = null;
        try { lu = new URL(v[5]); } catch (e) { lu = null; }
        if (/\s/.test(v[5]) || !lu || !/^https?:$/.test(lu.protocol)) add('error', line, 'Link is not a valid web address: ' + v[5].slice(0, 80));
      } else add('info', line, 'No Link — the pin won\'t send anyone to your video or page.');

      // Publish date
      if (v[6]) {
        var d = fixDate(v[6]);
        if (d.error) add('error', line, 'Publish date "' + v[6] + '" ' + d.error + '.');
        else {
          if (d.fixed) { add('error', line, 'Publish date "' + v[6] + '" is not in the format YYYY-MM-DDTHH:MM:SS.'); fixes.push('Line ' + line + ': changed the date to ' + d.value + (d.noTime ? ' (no time was given, so 12:00 was used — change it if you like)' : '') + '.'); v[6] = d.value; }
          if (d.date < now) add('error', line, 'Publish date ' + d.value + ' is in the past. Pinterest only schedules pins for future dates.');
          if (lastDate && d.date < lastDate) outOfOrder++;
          lastDate = d.date;
        }
      }
      out.push({ line: line, values: v });
    });

    if (outOfOrder) add('warning', null, outOfOrder + ' row' + (outOfOrder === 1 ? ' is' : 's are') + ' earlier than the row above. Pinterest doesn\'t need date order, but a sorted file is easier to review.');
    if (outOfOrder) fixes.push('Sorted rows by publish date (rows without a date stay first).');
    if (out.length > MAX_ROWS) add('error', null, out.length + ' pins in one file. Pinterest takes up to ' + MAX_ROWS + ' per CSV — the corrected download is split into ' + Math.ceil(out.length / MAX_ROWS) + ' files.');
    if (!out.length) add('error', null, 'No pins found below the header.');

    // Board names: same name except for case/spaces is almost always a typo.
    var names = Object.keys(boards), groups = {};
    names.forEach(function (b) { var k = b.toLowerCase().replace(/\s+/g, ' '); (groups[k] = groups[k] || []).push(b); });
    Object.keys(groups).forEach(function (k) {
      var g = groups[k];
      if (g.length > 1) {
        var main = g.slice().sort(function (a, b) { return boards[b].length - boards[a].length; })[0];
        add('warning', null, 'Board names that differ only in capitals or spaces: ' + g.map(function (x) { return '"' + x + '"'; }).join(', ') + '. Pinterest treats them as different boards.');
        fixes.push('Used one spelling for that board: "' + main + '".');
        out.forEach(function (o) { if (g.indexOf(o.values[2]) !== -1) o.values[2] = main; });
      }
    });

    if (outOfOrder) {
      out.sort(function (a, b) {
        var x = a.values[6], y = b.values[6];
        if (!x || !y) return (x ? 1 : 0) - (y ? 1 : 0) || a.line - b.line;
        return x < y ? -1 : x > y ? 1 : a.line - b.line;
      });
    }
    var finalBoards = {};
    out.forEach(function (o) { if (o.values[2]) finalBoards[o.values[2]] = (finalBoards[o.values[2]] || 0) + 1; });

    var quote = function (f) { return '"' + String(f).replace(/"/g, '""') + '"'; };
    var files = [];
    for (var i = 0; i < Math.max(1, Math.ceil(out.length / MAX_ROWS)); i++) {
      files.push([HEADER].concat(out.slice(i * MAX_ROWS, (i + 1) * MAX_ROWS).map(function (o) { return o.values; }))
        .map(function (r) { return r.map(quote).join(','); }).join('\r\n') + '\r\n');
    }
    var count = function (l) { return issues.filter(function (x) { return x.level === l; }).length; };
    return {
      issues: issues, fixes: fixes, rows: out, boards: Object.keys(finalBoards).map(function (b) { return { name: b, pins: finalBoards[b] }; }),
      files: files, errors: count('error'), warnings: count('warning'), pins: out.length
    };
  }
  window.checkPinCsv = check; // used by the automated checks

  // ---------------------------------------------------------------- UI
  var ta = document.getElementById('csv');
  if (!ta) return;
  var fileIn = document.getElementById('file');
  var out = document.getElementById('report');
  var status = document.getElementById('tool-status');
  var fileName = 'pins';

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  function show() {
    var text = ta.value;
    if (!text.trim()) { out.innerHTML = ''; return; }
    var r = check(text, new Date());
    var shown = r.issues.slice(0, 300);
    var html = '<p class="summary-line" id="summary">' + r.pins + ' pin' + (r.pins === 1 ? '' : 's') + ' · ' +
      r.errors + ' error' + (r.errors === 1 ? '' : 's') + ' · ' + r.warnings + ' warning' + (r.warnings === 1 ? '' : 's') + '</p>';
    if (!r.errors && !r.warnings) html += '<p class="status">Looks good. This file matches Pinterest\'s bulk-upload template.</p>';
    if (shown.length) {
      html += '<h3>What we found</h3><ul class="issues">' + shown.map(function (x) {
        return '<li class="' + x.level + '"><b>' + (x.level === 'error' ? 'Error' : x.level === 'warning' ? 'Warning' : 'Tip') +
          (x.row ? ' · line ' + x.row : '') + '</b>' + esc(x.msg) + '</li>';
      }).join('') + '</ul>';
      if (r.issues.length > shown.length) html += '<p class="note">…and ' + (r.issues.length - shown.length) + ' more.</p>';
    }
    if (r.boards.length) {
      html += '<h3>Boards in this file</h3><p class="note">Create these boards in Pinterest first, with exactly these names:</p><ul class="boards">' +
        r.boards.map(function (b) { return '<li>' + esc(b.name) + ' (' + b.pins + ')</li>'; }).join('') + '</ul>';
    }
    if (r.fixes.length && r.pins) {
      html += '<h3>Fixed in the corrected file</h3><ul class="issues">' + r.fixes.slice(0, 100).map(function (f) { return '<li class="info">' + esc(f) + '</li>'; }).join('') + '</ul>';
      html += '<p class="note">Problems not listed here (past dates, sharing-page links, missing boards) need you — fix them in your sheet.</p>';
      html += '<div class="btns">' + r.files.map(function (_, i) {
        return '<button type="button" class="btn btn-primary dl" data-i="' + i + '">Download corrected CSV' + (r.files.length > 1 ? ' (part ' + (i + 1) + ')' : '') + '</button>';
      }).join('') + '</div>';
    }
    out.innerHTML = html;
    [].slice.call(out.querySelectorAll('.dl')).forEach(function (b) {
      b.addEventListener('click', function () {
        var i = +b.getAttribute('data-i');
        var blob = new Blob([r.files[i]], { type: 'text/csv;charset=utf-8' });
        var a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = fileName.replace(/\.csv$/i, '') + '-fixed' + (r.files.length > 1 ? '-' + (i + 1) : '') + '.csv';
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
        status.textContent = 'Downloaded ' + a.download + '.';
      });
    });
  }

  var timer;
  ta.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(show, 250); });
  document.getElementById('run').addEventListener('click', show);
  fileIn.addEventListener('change', function () {
    var f = fileIn.files && fileIn.files[0];
    if (!f) return;
    fileName = f.name;
    var rd = new FileReader();
    rd.onload = function () { ta.value = String(rd.result); show(); status.textContent = 'Loaded ' + f.name + ' (checked on your device, not uploaded).'; };
    rd.readAsText(f);
  });
  document.getElementById('sample').addEventListener('click', function () {
    var y = new Date().getUTCFullYear() + 1;
    ta.value = [
      'title,Media URL,Pinterest Board,Thumbnail,Description,Link,Publish date,Keywords',
      '"7 Things You Can See Tonight Without a Telescope",https://example.github.io/pins/001-sky.jpg,Night Sky Tips,,"No telescope needed: seven sights for tonight.",https://example.com/sky?utm_source=pinterest,' + y + '-03-02 14:00,"stargazing, night sky"',
      '"Binoculars or a Telescope First?",https://drive.google.com/file/d/abc123/view,night sky tips,,"Which to buy first.",https://example.com/gear,' + y + '-03-01T20:00:00,"binoculars, telescope"',
      '"' + 'A very long title that keeps going and going because it tries to fit every single keyword into one pin title' + '",https://example.github.io/pins/003 moon.jpg,Night Sky Tips,,"Moon phases explained.",example.com/moon,2020-01-05T10:00:00,moon',
      '"7 Things You Can See Tonight Without a Telescope",https://example.github.io/pins/001-sky.jpg,Night Sky Tips,,"No telescope needed: seven sights for tonight.",https://example.com/sky?utm_source=pinterest,' + y + '-03-02 14:00,"stargazing, night sky"'
    ].join('\n');
    fileName = 'sample-pins.csv';
    show();
  });
})();
