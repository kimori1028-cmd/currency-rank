/* 世界の通貨安ランキング: data/latest.json（順位）と data/series/<コード>.json（国別）を読むだけの静的サイト。 */
(function () {
  'use strict';
  const $ = id => document.getElementById(id);
  const PLABEL = { d1: '1日', d7: '7日', d30: '30日', ytd: '年初来' };
  const TOP = 20;
  const WARN = { step: true, spike: true, check: true };

  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmtPct = v => v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toFixed(2) + '%';
  const fmtRate = v => v >= 1000 ? Math.round(v).toLocaleString('en-US') : v >= 10 ? v.toFixed(2) : v.toFixed(4);
  const fmtZ = z => z == null ? '—' : z >= 20 ? '20倍超' : z.toFixed(1) + '倍';
  const md = d => Number(d.slice(5, 7)) + '/' + Number(d.slice(8, 10));

  function load(key, fallback) { try { return localStorage.getItem(key) || fallback; } catch (e) { return fallback; } }
  function save(key, v) { try { localStorage.setItem(key, v); } catch (e) { /* 保存できなくても動く */ } }

  let DATA = null;
  const state = { period: load('cr.period', 'd1'), sort: load('cr.sort', 'chg'), all: false, q: '', range: 365 };
  if (!PLABEL[state.period]) state.period = 'd1';

  /* ---------- 共通のツールチップ ---------- */
  const tip = $('tip');
  function showTip(html, x, y) {
    tip.innerHTML = html; tip.hidden = false;
    const r = tip.getBoundingClientRect(), vw = document.documentElement.clientWidth;
    tip.style.left = Math.max(8, Math.min(x + 12, vw - r.width - 8)) + 'px';
    tip.style.top = Math.max(8, y - r.height - 12) + 'px';
  }
  function hideTip() { tip.hidden = true; }

  /* ---------- ランキング ---------- */
  function spark(w) {
    const v = w.filter(x => x).map(x => -Math.log(x));
    if (v.length < 2) return '';
    const W = 120, H = 26, p = 4, lo = Math.min.apply(null, v), hi = Math.max.apply(null, v), sp = (hi - lo) || 1;
    const pts = v.map((y, i) => [p + i * (W - 2 * p) / (v.length - 1), p + (hi - y) * (H - 2 * p) / sp]);
    const d = pts.map((q, i) => (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1)).join('');
    const e = pts[pts.length - 1];
    return '<svg class="spark" width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" aria-hidden="true"><path d="' + d + '"/><circle cx="' + e[0].toFixed(1) + '" cy="' + e[1].toFixed(1) + '" r="3.5"/></svg>';
  }

  function chips(r) {
    let s = '';
    if (r.alert) s += '<span class="chip warn"><i></i>異変</span>';
    if (r.m) s += '<span class="chip mkt"><i></i>' + esc(r.m) + '</span>';
    r.f.forEach(f => { s += '<span class="chip' + (WARN[f.k] ? ' warn' : '') + '"><i></i>' + esc(f.t) + '</span>'; });
    return s;
  }

  function renderRank() {
    const p = state.sort === 'z' ? 'd7' : state.period;
    let list = DATA.rows.filter(r => r[p] != null);
    if (state.sort === 'z') list = list.filter(r => r.d7 < 0 && r.z != null).sort((a, b) => b.z - a.z || a.d7 - b.d7);
    else list.sort((a, b) => a[p] - b[p]);
    list.forEach((r, i) => { r._rank = i + 1; });
    const total = list.length;
    const q = state.q.trim().toLowerCase();
    if (q) list = list.filter(r => r.c.toLowerCase().indexOf(q) >= 0 || r.n.toLowerCase().indexOf(q) >= 0);
    else if (!state.all) list = list.slice(0, TOP);
    const mx = Math.max.apply(null, list.map(r => Math.abs(r[p])).concat([0.01]));
    $('rank-body').innerHTML = list.length ? list.map(r => {
      const w = Math.max(2, Math.abs(r[p]) / mx * 108);
      return '<tr data-c="' + r.c + '"><td class="rk">' + r._rank + '</td>' +
        '<td><a class="cur-link" href="#' + r.c + '"><span class="code">' + r.c + '</span><span class="cname">' + esc(r.n) + '</span></a></td>' +
        '<td class="r num">' + fmtRate(r.rate) + '</td>' +
        '<td><div class="chg"><span class="bar-track"><span class="bar' + (r[p] > 0 ? ' up' : '') + '" style="width:' + w.toFixed(0) + 'px"></span></span><span class="chg-val">' + fmtPct(r[p]) + '</span></div></td>' +
        '<td class="r num">' + fmtZ(r.z) + '</td><td>' + spark(r.w) + '</td><td><div class="chips">' + chips(r) + '</div></td></tr>';
    }).join('') : '<tr><td colspan="7" class="empty">当てはまる通貨がありません。</td></tr>';
    $('th-chg').textContent = '通貨の価値の変化（' + PLABEL[p] + '）';
    $('rank-sub').textContent = DATA.ref[p] + ' と ' + DATA.end + ' の比較・' + (q ? list.length + ' 件' : state.all ? total + ' 通貨すべて' : total + ' 通貨のうち上位 ' + Math.min(TOP, total));
    document.querySelectorAll('#seg-period button').forEach(b => { b.setAttribute('aria-pressed', String(b.dataset.p === p)); b.disabled = state.sort === 'z' && b.dataset.p !== 'd7'; });
    document.querySelectorAll('#seg-sort button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.s === state.sort)));
    const more = $('more');
    more.hidden = !!q || total <= TOP;
    more.textContent = state.all ? '上位 ' + TOP + ' だけにする' : total + ' 通貨すべてを表示';
  }

  function renderAlerts() {
    const a = DATA.alerts || [];
    $('alerts').hidden = !a.length;
    $('alert-list').innerHTML = a.map(x => '<a class="alert" href="#' + x.c + '"><b><span class="code">' + x.c + '</span>　' + esc(x.n) + '</b><span>' + esc(x.why) + '（7日 <span class="num">' + fmtPct(x.d7) + '</span>）</span></a>').join('');
  }

  $('seg-period').addEventListener('click', e => { const b = e.target.closest('button'); if (b && !b.disabled) { state.period = b.dataset.p; save('cr.period', state.period); renderRank(); } });
  $('seg-sort').addEventListener('click', e => { const b = e.target.closest('button'); if (b) { state.sort = b.dataset.s; save('cr.sort', state.sort); renderRank(); } });
  $('q').addEventListener('input', e => { state.q = e.target.value; renderRank(); });
  $('more').addEventListener('click', () => { state.all = !state.all; renderRank(); });
  $('rank-body').addEventListener('click', e => { const tr = e.target.closest('tr[data-c]'); if (tr && !e.target.closest('a')) location.hash = tr.dataset.c; });

  /* ---------- 国別 ---------- */
  let SERIES = null;

  function cleaned(dates, vals, spikes) {
    const sp = {}; spikes.forEach(d => { sp[d] = 1; });
    const out = vals.slice();
    for (let i = 1; i < out.length; i++) if (sp[dates[i]]) out[i] = out[i - 1];
    return out;
  }

  function niceTicks(lo, hi, n) {
    if (hi <= lo) { hi = lo * 1.01 + 1e-9; lo = lo * 0.99; }
    const raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), f = raw / mag;
    const step = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * mag;
    const t0 = Math.floor(lo / step) * step, out = [];
    for (let v = t0; v < hi + step * 0.999; v += step) out.push(v);
    return { ticks: out, step: step };
  }

  function fmtTick(v, step) {
    if (Math.abs(v) >= 10000) { const m = v / 10000; return (step >= 10000 ? Math.round(m).toLocaleString('en-US') : m.toFixed(step >= 1000 ? 1 : 2)) + '万'; }
    const dec = step >= 1 ? 0 : Math.min(6, Math.ceil(-Math.log10(step)));
    return v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  function renderChart() {
    const S = SERIES, svg = $('c-chart');
    // 図の大きさを入れ物の幅に合わせる（文字の大きさを変えずに、スマホでも端の値が見えるように）
    const W = Math.max(340, Math.round(svg.parentNode.clientWidth) || 760), H = Math.round(Math.max(250, Math.min(360, W * 0.5)));
    const L = 62, R = W < 560 ? 92 : 124, T = 22, B = 34;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
    const cutoff = state.range ? new Date(Date.parse(S.end) - state.range * 864e5).toISOString().slice(0, 10) : '0000';
    const lines = [{ key: 'main', name: S.market ? S.market.label : null, dates: S.dates, vals: cleaned(S.dates, S.vals, S.spikes), raw: S.vals, spikes: S.spikes, steps: S.steps, cls: 'series', dot: 'dot' }];
    if (S.official) lines.push({ key: 'off', name: '配信レート', dates: S.official.dates, vals: cleaned(S.official.dates, S.official.vals, S.official.spikes), raw: S.official.vals, spikes: S.official.spikes, steps: S.official.steps, cls: 'series2', dot: 'dot2' });
    lines.forEach(l => { l.i0 = Math.max(0, l.dates.findIndex(d => d >= cutoff)); });
    const t0 = Date.parse(lines[0].dates[lines[0].i0]), t1 = Date.parse(S.end);
    let lo = Infinity, hi = -Infinity;
    lines.forEach(l => { for (let i = l.i0; i < l.vals.length; i++) { if (l.vals[i] < lo) lo = l.vals[i]; if (l.vals[i] > hi) hi = l.vals[i]; } });
    const nt = niceTicks(lo, hi, 4), y0 = nt.ticks[0], y1 = nt.ticks[nt.ticks.length - 1];
    const X = d => L + (Date.parse(d) - t0) / ((t1 - t0) || 1) * (W - L - R);
    const Y = v => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
    let s = '';
    nt.ticks.forEach((v, i) => {
      s += '<line class="' + (i ? 'grid' : 'base') + '" x1="' + L + '" x2="' + (W - R) + '" y1="' + Y(v).toFixed(1) + '" y2="' + Y(v).toFixed(1) + '"/>';
      s += '<text class="tick" x="' + (L - 8) + '" y="' + (Y(v) + 4).toFixed(1) + '" text-anchor="end">' + fmtTick(v, nt.step) + '</text>';
    });
    // 月の目盛り
    const months = (t1 - t0) / 864e5 / 30.4, every = months <= 4 ? 1 : months <= 14 ? 3 : 6;
    const dt = new Date(t0); dt.setUTCDate(1); dt.setUTCMonth(dt.getUTCMonth() + 1);
    let lastX = -99;
    while (dt.getTime() <= t1) {
      if (dt.getUTCMonth() % every === 0) {
        const x = L + (dt.getTime() - t0) / ((t1 - t0) || 1) * (W - L - R);
        if (x - lastX > 60 && x < W - R + 1) { s += '<text class="tick" x="' + x.toFixed(1) + '" y="' + (H - 12) + '" text-anchor="middle">' + dt.getUTCFullYear() + '/' + String(dt.getUTCMonth() + 1).padStart(2, '0') + '</text>'; lastX = x; }
      }
      dt.setUTCMonth(dt.getUTCMonth() + 1);
    }
    const ends = [];
    lines.forEach((l, li) => {
      const pts = [];
      for (let i = l.i0; i < l.vals.length; i++) pts.push([X(l.dates[i]), Y(l.vals[i]), i]);
      l.pts = pts;
      const path = pts.map((q, i) => (i ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1)).join('');
      if (li === 0 && lines.length === 1) s += '<path class="wash" d="' + path + 'L' + pts[pts.length - 1][0].toFixed(1) + ' ' + Y(y0) + 'L' + pts[0][0].toFixed(1) + ' ' + Y(y0) + 'Z"/>';
      s += '<path class="' + l.cls + '" d="' + path + '"/>';
      // 値の飛びの日（線は直前の値で埋めてある）
      l.spikes.filter(d => d >= l.dates[l.i0]).forEach(d => { s += '<circle class="mark" cx="' + X(d).toFixed(1) + '" cy="' + (Y(y0) - 5) + '" r="3.5"/>'; });
      // 段差は大きいもの 2 つまで名札を付ける
      l.steps.filter(st => st[0] >= l.dates[l.i0]).sort((a, b) => Math.abs(Math.log(1 + b[1] / 100)) - Math.abs(Math.log(1 + a[1] / 100))).slice(0, 2).forEach(st => {
        const i = l.dates.indexOf(st[0]), x = X(st[0]), y = Y(l.vals[i]), left = x > L + 130;
        const pct = st[1] > 999 ? '+999%超' : fmtPct(st[1]);
        s += '<text class="note" x="' + (left ? x - 10 : x + 10).toFixed(1) + '" y="' + Math.max(T + 12, y + (st[1] < 0 ? 18 : -8)).toFixed(1) + '" text-anchor="' + (left ? 'end' : 'start') + '">' + md(st[0]) + ' 段差 ' + pct + '</text>';
      });
      const e = pts[pts.length - 1];
      ends.push({ l: l, x: e[0], y: e[1], ly: e[1] });
    });
    if (ends.length === 2 && Math.abs(ends[0].ly - ends[1].ly) < 34) {
      const up = ends[0].y <= ends[1].y ? ends[0] : ends[1], dn = up === ends[0] ? ends[1] : ends[0], mid = (up.y + dn.y) / 2;
      up.ly = mid - 17; dn.ly = mid + 17;
    }
    ends.forEach(e => {
      s += '<circle class="' + e.l.dot + '" cx="' + e.x.toFixed(1) + '" cy="' + e.y.toFixed(1) + '" r="4.5"/>';
      const yy = Math.max(T + 10, Math.min(H - B - 16, e.ly));
      if (e.l.name) s += '<text class="note2" x="' + (e.x + 10).toFixed(1) + '" y="' + (yy - 3).toFixed(1) + '">' + esc(e.l.name) + '</text>';
      s += '<text class="note" x="' + (e.x + 10).toFixed(1) + '" y="' + (yy + (e.l.name ? 13 : 4)).toFixed(1) + '">' + fmtRate(e.l.raw[e.l.raw.length - 1]) + '</text>';
    });
    s += '<line class="cross" id="cross" x1="0" x2="0" y1="' + T + '" y2="' + (H - B) + '" visibility="hidden"/>';
    lines.forEach((l, li) => { s += '<circle class="' + l.dot + '" id="cdot' + li + '" r="4.5" visibility="hidden"/>'; });
    svg.innerHTML = s;
    svg.setAttribute('aria-label', S.n + '（' + S.c + '）の対ドル相場の折れ線。上に行くほど通貨安。');
    const m = lines[0];
    svg.onpointermove = ev => {
      const b = svg.getBoundingClientRect(), x = (ev.clientX - b.left) / b.width * W;
      let k = 0, best = 1e9;
      m.pts.forEach((q, i) => { const dd = Math.abs(q[0] - x); if (dd < best) { best = dd; k = i; } });
      const q = m.pts[k], d = m.dates[q[2]];
      const cross = svg.querySelector('#cross');
      cross.setAttribute('x1', q[0]); cross.setAttribute('x2', q[0]); cross.setAttribute('visibility', 'visible');
      let html = d;
      lines.forEach((l, li) => {
        let j = -1;
        for (let i = l.pts.length - 1; i >= 0; i--) if (l.dates[l.pts[i][2]] <= d) { j = i; break; }
        const dot = svg.querySelector('#cdot' + li);
        if (j < 0) { dot.setAttribute('visibility', 'hidden'); return; }
        const pt = l.pts[j], idx = pt[2], spike = l.spikes.indexOf(l.dates[idx]) >= 0;
        dot.setAttribute('cx', pt[0]); dot.setAttribute('cy', pt[1]); dot.setAttribute('visibility', 'visible');
        html += '<br>' + (l.name ? esc(l.name) + ' ' : '1ドル＝') + '<span class="num">' + fmtRate(l.raw[idx]) + '</span>' + (spike ? '（値の飛び）' : '');
      });
      showTip(html, ev.clientX, ev.clientY);
    };
    svg.onpointerleave = () => {
      svg.querySelector('#cross').setAttribute('visibility', 'hidden');
      lines.forEach((l, li) => svg.querySelector('#cdot' + li).setAttribute('visibility', 'hidden'));
      hideTip();
    };
    const lg = $('c-legend');
    lg.hidden = lines.length < 2;
    lg.innerHTML = lines.map(l => '<span><i style="background:var(--' + (l.key === 'main' ? 's1' : 's2') + ')"></i>' + esc(l.name || '') + '</span>').join('') +
      (lines.some(l => l.spikes.length) ? '<span>○ 値の飛びがあった日</span>' : '');
    document.querySelectorAll('#seg-range button').forEach(b => b.setAttribute('aria-pressed', String(Number(b.dataset.r) === state.range)));
  }

  function renderCountry() {
    const S = SERIES;
    $('c-title').innerHTML = '<span class="code">' + S.c + '</span>　' + esc(S.n);
    $('c-sub').textContent = '1 ドルあたりの値（上に行くほど通貨安）・' + S.end + ' 時点';
    document.title = S.n + '（' + S.c + '）｜世界の通貨安ランキング';
    const facts = [['1ドル＝' + (S.market ? '（' + S.market.label + '）' : ''), fmtRate(S.rate), '']];
    ['d1', 'd7', 'd30', 'ytd'].forEach(p => facts.push([PLABEL[p], fmtPct(S[p]), S.ref[p] ? S.ref[p].slice(5).replace('-', '/') + ' 比' : '']));
    facts.push(['普段の何倍（7日）', fmtZ(S.z), '']);
    if (S.official) { facts.push(['配信レート', fmtRate(S.official.rate), '']); facts.push(['配信レートとの開き', (S.gap > 0 ? '+' : '') + S.gap.toFixed(1) + '%', '']); }
    $('c-facts').innerHTML = facts.map(a => '<div class="fact"><span>' + esc(a[0]) + '</span><span><span class="num">' + a[1] + '</span>' + (a[2] ? '<small>' + a[2] + '</small>' : '') + '</span></div>').join('');
    let fl = '';
    if (S.alert) fl += '<div class="callout"><b>異変</b>' + esc(S.alert) + '</div>';
    if (S.market) fl += '<div class="callout info"><b>' + esc(S.market.label) + 'で表示</b>' + esc(S.market.src) + '（' + S.market.asof + ' 時点）。順位もこの値で付けています。配信レートより ' + S.gap.toFixed(1) + '% ドル高です。</div>';
    S.flags.forEach(f => { fl += '<div class="callout' + (WARN[f.k] ? '' : ' plain') + '"><b>' + esc(f.t) + '</b>' + esc(f.why) + '</div>'; });
    if (S.official) S.official.flags.forEach(f => { fl += '<div class="callout plain"><b>配信レート: ' + esc(f.t) + '</b>' + esc(f.why) + '</div>'; });
    $('c-flags').innerHTML = fl;
    const n = S.dates.length, rows = [];
    for (let i = n - 1; i >= Math.max(1, n - 30); i--) rows.push('<tr><td>' + S.dates[i] + '</td><td>' + fmtRate(S.vals[i]) + '</td><td>' + fmtPct((S.vals[i - 1] / S.vals[i] - 1) * 100) + '</td></tr>');
    $('c-table').innerHTML = '<table><tr><th>日付</th><th>1ドル＝</th><th>前日比（価値）</th></tr>' + rows.join('') + '</table>';
    renderChart();
  }

  $('seg-range').addEventListener('click', e => { const b = e.target.closest('button'); if (b) { state.range = Number(b.dataset.r); renderChart(); } });
  let resizeTimer = 0;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (SERIES && !$('view-country').hidden) renderChart(); }, 150); });

  /* ---------- 画面の切り替え ---------- */
  function route() {
    hideTip();
    const code = decodeURIComponent(location.hash.replace('#', '')).toUpperCase();
    const row = code && DATA.rows.find(r => r.c === code);
    if (!row) {
      $('view-country').hidden = true; $('view-rank').hidden = false;
      document.title = '世界の通貨安ランキング';
      return;
    }
    fetch('data/series/' + code + '.json', { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(j => {
      SERIES = j;
      $('view-rank').hidden = true; $('view-country').hidden = false;
      renderCountry();
      window.scrollTo(0, 0);
    }).catch(() => { location.hash = ''; });
  }
  window.addEventListener('hashchange', route);

  fetch('data/latest.json', { cache: 'no-cache' }).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(j => {
    DATA = j;
    $('asof').textContent = j.end + ' の値（' + j.generated + ' 更新）';
    $('foot').innerHTML = 'データの出どころ: 無料の公開レート配信（currency-api）。イランの市中レートは bonbast.com の両替相場の公開アーカイブ。値は配信されたものに点検の旗を付けただけで、正しさは保証しません。売買の判断に使うものではありません。';
    renderAlerts(); renderRank(); route();
  }).catch(() => {
    $('rank-body').innerHTML = '<tr><td colspan="7" class="empty">データを読み込めませんでした。少し待ってから開き直してください。</td></tr>';
  });
})();
