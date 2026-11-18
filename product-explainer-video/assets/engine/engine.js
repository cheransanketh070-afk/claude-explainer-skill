/* Product Explainer engine.
 * Deterministic: every frame is a pure function of time t. window.__seek(t) renders time t.
 * Animations are Web Animations (paused, scrubbed via currentTime) + "tickers" for text/counters/packets.
 */
(function () {
'use strict';
const SB = window.__STORYBOARD__;
const M = Object.assign({ theme: 'dark-tech', fps: 30, aspect: '16:9', captions: true, product: 'Product', tagline: '', url: '', accent: null, accent2: null, brand: true }, SB.meta || {});
const params = new URLSearchParams(location.search);
const RENDER = params.has('render');
const EMBED = params.has('embed');
const DIMS = ({ '16:9': [1920, 1080], '9:16': [1080, 1920] })[M.aspect] || [1920, 1080];
const PORTRAIT = DIMS[1] > DIMS[0];
const NS = 'http://www.w3.org/2000/svg';

document.body.className = 'theme-' + M.theme + (PORTRAIT ? ' portrait' : '') + (RENDER ? ' render' : '') + (EMBED ? ' embed' : '');
const wrap = document.getElementById('wrap');
const stage = document.getElementById('stage');
stage.style.width = DIMS[0] + 'px';
stage.style.height = DIMS[1] + 'px';

/* ---------- helpers ---------- */
const $ = (tag, cls, html, parent) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; if (parent) parent.appendChild(e); return e; };
const esc = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const rich = s => esc(s).replace(/\*([^*]+)\*/g, '<em>$1</em>').replace(/`([^`]+)`/g, '<code>$1</code>');
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const easeOut = x => 1 - Math.pow(1 - clamp(x, 0, 1), 3);
const easeInOut = x => { x = clamp(x, 0, 1); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const EASE = 'cubic-bezier(.2,.8,.2,1)';
const hex2rgb = h => { h = (h || '#6c8cff').trim().replace('#', ''); if (h.length === 3) h = h.split('').map(c => c + c).join(''); const n = parseInt(h, 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
const rgba = (h, a) => { const [r, g, b] = hex2rgb(h); return `rgba(${r},${g},${b},${a})`; };
function shiftHue(hex, deg) { let [r, g, b] = hex2rgb(hex).map(v => v / 255); const mx = Math.max(r, g, b), mn = Math.min(r, g, b); let h, s, l = (mx + mn) / 2; if (mx === mn) { h = s = 0; } else { const d = mx - mn; s = l > .5 ? d / (2 - mx - mn) : d / (mx + mn); h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; h /= 6; } h = (h + deg / 360 + 1) % 1; const f = (p, q, t) => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < .5 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; }; const q = l < .5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q; const o = [f(p, q, h + 1 / 3), f(p, q, h), f(p, q, h - 1 / 3)].map(v => Math.round(v * 255).toString(16).padStart(2, '0')); return '#' + o.join(''); }
if (M.accent) { stage.style.setProperty('--accent', M.accent); stage.style.setProperty('--accent2', M.accent2 || shiftHue(M.accent, 45)); }
else if (M.accent2) stage.style.setProperty('--accent2', M.accent2);
const cssVar = n => getComputedStyle(stage).getPropertyValue(n).trim();
if (M.font_stack) stage.style.setProperty('--font', M.font_stack), stage.style.fontFamily = M.font_stack;
if (M.css) { const gs = document.createElement('style'); gs.textContent = String(M.css); document.head.appendChild(gs); }
if (M.vars) Object.keys(M.vars).forEach(k => stage.style.setProperty(k.startsWith('--') ? k : '--' + k, M.vars[k]));

/* ---------- icons (24x24, stroke) ---------- */
const IC = {
  globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>',
  database: '<ellipse cx="12" cy="5.5" rx="8" ry="3"/><path d="M4 5.5v13c0 1.7 3.6 3 8 3s8-1.3 8-3v-13M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  code: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M14 4l-4 16"/>',
  terminal: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 10l3 2-3 2M13 15h4"/>',
  bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
  file: '<path d="M6 3h8l5 5v13H6z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  download: '<path d="M12 4v11M7 11l5 5 5-5M4 20h16"/>',
  upload: '<path d="M12 16V5M7 9l5-5 5 5M4 20h16"/>',
  cloud: '<path d="M7 18a4 4 0 010-8 5.5 5.5 0 0110.6-1A4.5 4.5 0 0117 18z"/>',
  cpu: '<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9.5" y="9.5" width="5" height="5"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
  bell: '<path d="M6 16V11a6 6 0 0112 0v5l2 2H4z"/><path d="M10 21h4"/>',
  chart: '<path d="M4 20V4M4 20h16M8 16v-4M12 16V8M16 16v-7"/>',
  filter: '<path d="M3 5h18l-7 8v6l-4 2v-8z"/>',
  link: '<path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M9 13v1M15 13v1M9 17h6"/><circle cx="12" cy="3.5" r="1"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 12.5l9 5 9-5M3 17l9 5 9-5"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
  play: '<path d="M7 4l13 8-13 8z"/>',
  folder: '<path d="M3 6h6l2 2h10v11H3z"/>',
  git: '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="9" r="2"/><path d="M6 7v10M18 11c0 4-6 3-12 6"/>',
  star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 018 0v3"/>',
  refresh: '<path d="M20 11a8 8 0 00-14-4L4 9M4 4v5h5M4 13a8 8 0 0014 4l2-2M20 20v-5h-5"/>',
  box: '<path d="M12 3l9 5v8l-9 5-9-5V8z"/><path d="M3 8l9 5 9-5M12 13v8"/>',
  table: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M10 4v16"/>',
  image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M4 18l5-5 4 4 3-3 4 4"/>',
  calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
  bug: '<rect x="8" y="8" width="8" height="12" rx="4"/><path d="M12 8V5M9 5l1.5 1.5M15 5l-1.5 1.5M4 13h4M16 13h4M5 19l3-2M19 19l-3-2M5 8l3 2M19 8l-3 2"/>',
  rocket: '<path d="M14 4c4 0 6 2 6 6-2 4-5 7-8 8l-4-4c1-3 4-6 6-10z"/><circle cx="14.5" cy="9.5" r="1.5"/><path d="M8 14c-2 .5-3.5 2-4 5 3-.5 4.5-2 5-4"/>',
  sparkles: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z"/>',
  server: '<rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/>',
  key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3M14 9l2 2"/>',
  eye: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
  send: '<path d="M21 3L10 14M21 3l-7 18-4-7-7-4z"/>',
  plug: '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 01-12 0zM12 17v4"/>',
  wand: '<path d="M5 19L17 7M15 5l4 4M18 3v3M20 4.5h-3M6 5v2M7 6H5"/>',
  arrow: '<path d="M4 12h15M13 6l6 6-6 6"/>'
};
const ALIAS = { github: 'git', repo: 'git', scraper: 'search', crawl: 'search', crawler: 'search', api: 'plug', web: 'globe', website: 'globe', site: 'globe', browser: 'globe', db: 'database', sql: 'database', storage: 'database', ai: 'sparkles', llm: 'sparkles', magic: 'wand', schedule: 'clock', cron: 'clock', timer: 'clock', email: 'mail', notify: 'bell', alert: 'bell', data: 'table', csv: 'table', sheet: 'table', json: 'code', python: 'code', js: 'code', cli: 'terminal', shell: 'terminal', docker: 'box', package: 'box', deploy: 'rocket', launch: 'rocket', security: 'shield', auth: 'key', login: 'key', cache: 'bolt', fast: 'bolt', speed: 'bolt', queue: 'list', parse: 'filter', clean: 'filter', extract: 'download', export: 'upload', output: 'upload', report: 'chart', analytics: 'chart', dashboard: 'chart', monitor: 'eye', watch: 'eye', telegram: 'send', discord: 'send', slack: 'send', message: 'send', webhook: 'link', url: 'link', server2: 'server', backend: 'server', cloud2: 'cloud', settings: 'gear', config: 'gear', ok: 'check', done: 'check', no: 'x', pdf: 'file', doc: 'file', image2: 'image', photo: 'image', loop: 'refresh', sync: 'refresh', retry: 'refresh', agent: 'bot', robot: 'bot', automation: 'bot', stack: 'layers', people: 'user', users: 'user' };
const icon = (name, cls) => { const k = IC[name] ? name : (ALIAS[String(name || '').toLowerCase()] || 'box'); return `<span class="ico ${cls || ''}" style="display:block"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${IC[k]}</svg></span>`; };

/* ---------- timeline registry ---------- */
const ANIMS = [], TICKS = [], LAYOUTS = [];
const IMG_WAIT = [];

/* ---------- scene context ---------- */
function makeCtx(scene, S, D, root, idx) {
  const c = { S, D, root, scene, idx, data: scene.data || {} };
  c.a = (el, kf, t = 0, d = .55, ease = EASE) => { const an = el.animate(kf, { delay: Math.round((S + t) * 1000), duration: Math.max(1, Math.round(d * 1000)), easing: ease, fill: 'both' }); an.pause(); ANIMS.push(an); return an; };
  c.tick = fn => TICKS.push(t => fn(t - S, t));
  c.layout = fn => LAYOUTS.push(fn);
  c.pop = (el, t = 0, d = .55) => c.a(el, [{ opacity: 0, transform: 'translateY(30px) scale(.96)' }, { opacity: 1, transform: 'translateY(0) scale(1)' }], t, d);
  c.fade = (el, t = 0, d = .5) => c.a(el, [{ opacity: 0 }, { opacity: 1 }], t, d, 'ease-out');
  c.times = (n, from = .6, to = D - 1.4, maxStep = .8) => { if (n <= 1) return [from]; const step = Math.min(maxStep, Math.max(.12, (to - from) / (n - 1))); return Array.from({ length: n }, (_, i) => from + i * step); };
  c.heading = (txt, t = .1) => { if (!txt) return null; const h = $('h2', 'h', rich(txt), root); c.a(h, [{ opacity: 0, transform: 'translateY(22px)' }, { opacity: 1, transform: 'none' }], t, .6); return h; };
  return c;
}

/* ---------- scenes ---------- */
const SCENES = {};

SCENES.title = c => {
  const d = c.data, name = String(d.product || M.product || 'Product');
  const w = $('div', 't-wrap', null, c.root);
  const mark = $('div', 't-mark', d.icon ? icon(d.icon) : esc(d.mark || name.trim().charAt(0).toUpperCase()), w);
  if (d.icon) { const i = mark.firstChild; i.style.width = '56%'; i.style.height = '56%'; }
  const ring = $('i', 'ring', null, mark);
  c.a(mark, [{ opacity: 0, transform: 'scale(.35) rotate(-14deg)' }, { opacity: 1, transform: 'scale(1) rotate(0deg)' }], .1, .9, 'cubic-bezier(.3,1.45,.5,1)');
  c.tick(l => { const p = ((l - .9) % 2.4) / 2.4; if (l < .9) { ring.style.opacity = 0; return; } ring.style.opacity = (1 - p) * .65; ring.style.transform = `scale(${1 + p * .8})`; });
  const nm = $('div', 't-name', null, w);
  const chars = [...name];
  chars.forEach((ch, i) => { const s = $('span', '', ch === ' ' ? '&nbsp;' : esc(ch), nm); c.a(s, [{ opacity: 0, transform: 'translateY(46px)', filter: 'blur(12px)' }, { opacity: 1, transform: 'translateY(0)', filter: 'none' }], .45 + i * .04, .6); });
  const tEnd = .45 + chars.length * .04 + .3;
  if (d.tagline || M.tagline) { const tg = $('div', 't-tag', rich(d.tagline || M.tagline), w); c.a(tg, [{ opacity: 0, transform: 'translateY(20px)' }, { opacity: 1, transform: 'none' }], tEnd, .7); }
  const ln = $('div', 't-line', '<i></i>', w); c.a(ln.firstChild, [{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], tEnd + .2, .9, 'ease-in-out');
  if (d.chips && d.chips.length) { const cw = $('div', 'chips', null, w); d.chips.slice(0, 5).forEach((x, i) => { const p = $('span', 'pill', esc(x), cw); c.pop(p, tEnd + .5 + i * .12, .5); }); }
};

SCENES.chapter = c => {
  const d = c.data;
  const k = $('div', 'ch-k', esc(d.kicker || 'Part'), c.root); c.fade(k, .1);
  const n = $('div', 'ch-num', esc(String(d.number != null ? d.number : c.idx).padStart(2, '0')), c.root);
  c.a(n, [{ opacity: 0, transform: 'scale(.8)' }, { opacity: 1, transform: 'scale(1)' }], .15, .8);
  const b = $('div', 'ch-bar', '', c.root); c.a(b, [{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }], .5, .7, 'ease-in-out');
  const t = $('div', 'ch-t', rich(d.title || ''), c.root); c.a(t, [{ opacity: 0, transform: 'translateY(26px)' }, { opacity: 1, transform: 'none' }], .55, .7);
  if (d.subtitle) { const s = $('div', 'ch-s', rich(d.subtitle), c.root); c.a(s, [{ opacity: 0, transform: 'translateY(20px)' }, { opacity: 1, transform: 'none' }], .8, .7); }
};

SCENES.problem = c => {
  const d = c.data; c.heading(d.heading);
  const rows = $('div', 'rows', null, c.root);
  const pts = (d.points || []).slice(0, 5);
  const ts = c.times(pts.length, .8, c.D - (d.pivot ? 2.6 : 1.6), .85);
  pts.forEach((p, i) => {
    const r = $('div', 'row card', `<div class="ic">${icon('x')}</div><div>${rich(p)}</div>`, rows);
    c.a(r, [{ opacity: 0, transform: 'translateX(-60px)' }, { opacity: 1, transform: 'translateX(0)' }], ts[i], .6);
    c.a(r.firstChild, [{ transform: 'scale(1)' }, { transform: 'scale(1.18)', offset: .3 }, { transform: 'scale(1)' }], ts[i] + .35, .5);
  });
  if (d.pivot) { const pv = $('div', 'pivot', rich(d.pivot), c.root); c.a(pv, [{ opacity: 0, transform: 'translateY(24px) scale(.97)' }, { opacity: 1, transform: 'none' }], c.D - 2.0, .7); }
};

SCENES.flow = c => {
  const d = c.data; c.heading(d.heading);
  const nodes = (d.nodes || []).slice(0, 6), n = nodes.length;
  const box = $('div', 'flow' + (d.loop ? ' hasloop' : ''), null, c.root);
  const svg = document.createElementNS(NS, 'svg'); svg.setAttribute('class', 'edges'); box.appendChild(svg);
  const els = nodes.map(nd => $('div', 'node card', `<div class="ni">${icon(nd.icon || 'box')}</div><div class="nt"><div class="nl">${rich(nd.label)}</div>${nd.sub ? `<div class="ns">${rich(nd.sub)}</div>` : ''}</div>`, box));
  const tsN = c.times(n, .5, Math.max(1.0, c.D * .34), .5);
  els.forEach((e, i) => c.pop(e, tsN[i], .55));
  const tFlow = tsN[n - 1] + 1.0;
  const hop = clamp((c.D - tFlow - .8) / Math.max(1, n - 1) / 1.6, .45, .85);
  const L = (n - 1) * hop + .7;
  const pk = [];
  c.layout(() => {
    const pos = e => ({ x: e.offsetLeft, y: e.offsetTop, w: e.offsetWidth, h: e.offsetHeight });
    box.querySelectorAll('.elabel,.looplabel').forEach(x => x.remove()); svg.innerHTML = ''; pk.length = 0;
    const P = els.map(pos);
    for (let i = 0; i < n - 1; i++) {
      const a = P[i], b = P[i + 1]; let x0, y0, x1, y1;
      if (PORTRAIT) { x0 = a.x + a.w / 2; y0 = a.y + a.h + 8; x1 = b.x + b.w / 2; y1 = b.y - 8; } else { x0 = a.x + a.w + 8; y0 = a.y + a.h / 2; x1 = b.x - 8; y1 = b.y + b.h / 2; }
      const len = Math.hypot(x1 - x0, y1 - y0), ang = Math.atan2(y1 - y0, x1 - x0) * 180 / Math.PI;
      const path = document.createElementNS(NS, 'path'); path.setAttribute('d', `M${x0},${y0} L${x1 - 10 * Math.cos(ang * Math.PI / 180)},${y1 - 10 * Math.sin(ang * Math.PI / 180)}`); path.setAttribute('stroke', 'var(--accent)'); path.setAttribute('stroke-width', '4'); path.setAttribute('stroke-linecap', 'round'); path.setAttribute('fill', 'none'); path.setAttribute('opacity', '.55'); path.style.strokeDasharray = len; svg.appendChild(path);
      c.a(path, [{ strokeDashoffset: len }, { strokeDashoffset: 0 }], tsN[i + 1] - .1, .5, 'ease-out');
      const head = document.createElementNS(NS, 'path'); head.setAttribute('d', 'M-4,-9 L12,0 L-4,9 z'); head.setAttribute('transform', `translate(${x1 - 6},${y1}) rotate(${ang})`); head.setAttribute('fill', 'var(--accent)'); svg.appendChild(head);
      c.fade(head, tsN[i + 1] + .3, .3);
      const lab = nodes[i].edge || nodes[i].edge_label;
      if (lab) { const l = $('div', 'elabel', esc(lab), box); l.style.left = ((x0 + x1) / 2) + 'px'; l.style.top = ((y0 + y1) / 2) + 'px'; c.fade(l, tsN[i + 1] + .2, .4); }
      const mk = () => { const g = document.createElementNS(NS, 'g'); const o = document.createElementNS(NS, 'circle'); o.setAttribute('r', 20); o.setAttribute('fill', 'var(--accent2)'); o.setAttribute('opacity', '.25'); const k = document.createElementNS(NS, 'circle'); k.setAttribute('r', 9); k.setAttribute('fill', 'var(--accent2)'); g.appendChild(o); g.appendChild(k); g.setAttribute('opacity', 0); svg.appendChild(g); return g; };
      pk.push({ i, x0, y0, x1, y1, g: [mk(), mk()] });
    }
    if (d.loop && n > 1) {
      const f = P[0], l = P[n - 1]; let dpath, mx, my;
      if (PORTRAIT) { const rx = Math.max(f.x + f.w, l.x + l.w) + 70; const yy0 = f.y + f.h / 2, yy1 = l.y + l.h / 2; dpath = `M${l.x + l.w + 6},${yy1} C${rx},${yy1} ${rx},${yy0} ${f.x + f.w + 14},${yy0}`; mx = rx - 8; my = (yy0 + yy1) / 2; }
      else { const by = f.y + f.h + 10, fx = f.x + f.w / 2, lx = l.x + l.w / 2; dpath = `M${lx},${by} C${lx},${by + 100} ${fx},${by + 100} ${fx},${by + 14}`; mx = (fx + lx) / 2; my = by + 76; }
      const lp = document.createElementNS(NS, 'path'); lp.setAttribute('d', dpath); lp.setAttribute('stroke', 'var(--muted)'); lp.setAttribute('stroke-width', '3'); lp.setAttribute('stroke-dasharray', '10 12'); lp.setAttribute('fill', 'none'); lp.setAttribute('stroke-linecap', 'round'); svg.appendChild(lp);
      const lh = document.createElementNS(NS, 'path'); lh.setAttribute('d', 'M-4,-8 L11,0 L-4,8 z'); lh.setAttribute('fill', 'var(--muted)');
      if (PORTRAIT) { const yy0 = f.y + f.h / 2; lh.setAttribute('transform', `translate(${f.x + f.w + 10},${yy0}) rotate(180)`); } else { const by = f.y + f.h + 10; lh.setAttribute('transform', `translate(${f.x + f.w / 2},${by + 12}) rotate(-90)`); }
      svg.appendChild(lh); c.fade(lh, tFlow + .2, .5);
      c.fade(lp, tFlow - .2, .6); pk.loop = lp;
      if (typeof d.loop === 'string') { const ll = $('div', 'looplabel', esc(d.loop), box); ll.style.left = mx + 'px'; ll.style.top = my + 'px'; c.fade(ll, tFlow, .5); }
    }
  });
  c.tick(l => {
    if (pk.loop) pk.loop.style.strokeDashoffset = -l * 30;
    const glow = new Array(n).fill(0);
    pk.forEach(e => e.g.forEach(g => g.setAttribute('opacity', 0)));
    if (l >= tFlow) {
      for (let p = 0; p < 2; p++) {
        const u = (((l - tFlow - p * L / 2) % L) + L) % L;
        pk.forEach(e => { const lo = e.i * hop; if (u >= lo && u < lo + hop) { const q = easeInOut((u - lo) / hop); e.g[p].setAttribute('transform', `translate(${e.x0 + (e.x1 - e.x0) * q},${e.y0 + (e.y1 - e.y0) * q})`); e.g[p].setAttribute('opacity', 1); } });
        for (let j = 0; j < n; j++) { const du = (((u - j * hop) % L) + L) % L; if (du < .7 && (p === 0 || (l - tFlow) > L / 2)) glow[j] = Math.max(glow[j], 1 - du / .7); }
      }
    }
    els.forEach((e, j) => e.style.setProperty('--g', glow[j].toFixed(3)));
  });
};

SCENES.architecture = c => {
  const d = c.data; c.heading(d.heading);
  const arch = $('div', 'arch', null, c.root);
  const layers = (d.layers || []).slice(0, 4);
  const ts = c.times(layers.length, .6, Math.max(1.2, c.D * .45), .8);
  const dots = [];
  layers.forEach((ly, i) => {
    const L = $('div', 'layer card', `<div class="layer-name">${esc(ly.name)}</div><div class="items"></div>`, arch);
    const items = L.querySelector('.items');
    (ly.items || []).slice(0, 5).forEach((it, k) => { const ch = $('div', 'chip', `${icon(it.icon || 'box')}<span>${rich(it.label || it)}</span>`, items); c.pop(ch, ts[i] + .15 + k * .1, .5); });
    c.a(L, [{ opacity: 0, transform: 'translateY(30px)' }, { opacity: 1, transform: 'none' }], ts[i], .6);
    if (i < layers.length - 1) { const v = $('div', 'vconn', '<i></i>', arch); c.fade(v, ts[i] + .5, .4); dots.push({ el: v.firstChild, h: 26, t0: ts[i] + .8 }); }
  });
  c.tick(l => dots.forEach((x, k) => { const u = ((l - x.t0 - k * .35) % 1.1 + 1.1) % 1.1 / 1.1; x.el.style.opacity = l < x.t0 ? 0 : Math.sin(u * Math.PI); x.el.style.transform = `translateY(${u * x.h}px)`; }));
};

function hlCmd(s) {
  const e = esc(s);
  return e.replace(/^(\S+)/, '<span class="t-cmd">$1</span>').replace(/(\s)(--?[A-Za-z][\w-]*)/g, '$1<span class="t-flag">$2</span>').replace(/(&quot;[^&]*&quot;|'[^']*')/g, '<span class="t-str">$1</span>');
}
function windowBar(parent, title) { return $('div', 'win-bar', `<i class="dot r"></i><i class="dot y"></i><i class="dot g"></i><div class="win-title">${esc(title || '')}</div>`, parent); }

SCENES.terminal = c => {
  const d = c.data; c.heading(d.heading);
  const win = $('div', 'win', null, c.root); windowBar(win, d.title || 'terminal'); c.pop(win, .15);
  const body = $('div', 'term-body', null, win), inner = $('div', 'term-in', null, body); body.setAttribute('data-noaudit', '1');
  const lines = (d.lines || []).slice(0, 20).map(l => typeof l === 'string' ? (l.startsWith('$ ') ? { type: 'cmd', text: l.slice(2) } : { type: 'out', text: l }) : l);
  const start = .8, avail = Math.max(1.5, c.D - start - 1.1), CPS = 36;
  let nat = 0; lines.forEach(l => { nat += l.type === 'cmd' ? l.text.length / CPS + .45 : .17; });
  const k = Math.min(1, avail / Math.max(.1, nat));
  let t = start;
  const items = lines.map(l => {
    const it = { l, t0: t, dur: 0 };
    const e = it.e = $('div', 'ln ' + (l.type || 'out'), null, inner);
    if (l.type === 'cmd') { it.dur = (l.text.length / CPS) * k; t += it.dur + .45 * k; e.innerHTML = '<span class="p">$ </span><span class="tx"></span><span class="cursor"></span>'; it.tx = e.querySelector('.tx'); it.cur = e.querySelector('.cursor'); }
    else { t += .17 * k; const pre = (l.type === 'success' && !/^[✓✔]/.test(l.text)) ? '✓ ' : (l.type === 'err' && !/^[✗✘×]/.test(l.text)) ? '✗ ' : ''; e.textContent = pre + l.text; }
    return it;
  });
  let offs = [];
  c.layout(() => { const bh = body.clientHeight; offs = items.map(it => Math.max(0, it.e.offsetTop + it.e.offsetHeight + 30 - bh)); });
  c.tick(l => {
    let last = -1;
    items.forEach((it, i) => {
      const vis = l >= it.t0; it.e.style.opacity = vis ? 1 : 0; if (vis) last = i;
      if (it.tx) { const n = Math.floor(clamp((l - it.t0) / Math.max(.05, it.dur), 0, 1) * it.l.text.length); it.tx.innerHTML = hlCmd(it.l.text.slice(0, n)); }
    });
    items.forEach((it, i) => { if (it.cur) { const typing = l >= it.t0 && l < it.t0 + it.dur; const isLast = i === last; it.cur.style.opacity = (l >= it.t0 && (typing || (isLast && Math.floor(l * 2.2) % 2 === 0))) ? 1 : 0; } });
    if (last >= 0 && offs.length) { const cur = offs[last], prev = last > 0 ? offs[last - 1] : 0, f = easeOut((l - items[last].t0) / .25); inner.style.transform = `translateY(${-(prev + (cur - prev) * f)}px)`; }
  });
};

function hlCode(line, lang) {
  const hashLangs = ['python', 'py', 'bash', 'sh', 'shell', 'yaml', 'yml', 'ruby', 'rb', 'toml', 'dockerfile', 'r'];
  const hash = hashLangs.includes(String(lang || '').toLowerCase());
  const KW = new Set('def class return if elif else for while in not and or is import from as with try except finally raise lambda yield pass break continue async await const let var function new this typeof export default extends static public private void int string bool true false null none True False None fn pub use mod struct impl match mut self func package go defer chan interface type range select case switch throw throws catch echo then fi do done'.split(' '));
  const re = new RegExp((hash ? '(#.*)' : '(\\/\\/.*|#!.*)') + '|("(?:[^"\\\\]|\\\\.)*"|\'(?:[^\'\\\\]|\\\\.)*\'|`(?:[^`\\\\]|\\\\.)*`)|\\b(\\d+(?:\\.\\d+)?)\\b|\\b([A-Za-z_$][\\w$]*)(?=\\()|\\b([A-Za-z_$][\\w$]*)\\b', 'g');
  let out = '', last = 0, m;
  while ((m = re.exec(line))) {
    out += esc(line.slice(last, m.index)); last = re.lastIndex;
    if (m[1]) out += `<span class="tc">${esc(m[1])}</span>`; else if (m[2]) out += `<span class="ts">${esc(m[2])}</span>`; else if (m[3]) out += `<span class="tn">${esc(m[3])}</span>`;
    else if (m[4]) out += KW.has(m[4]) ? `<span class="tk">${esc(m[4])}</span>` : `<span class="tf">${esc(m[4])}</span>`;
    else out += KW.has(m[5]) ? `<span class="tk">${esc(m[5])}</span>` : esc(m[5]);
  }
  return out + esc(line.slice(last));
}

SCENES.code = c => {
  const d = c.data; c.heading(d.heading);
  const win = $('div', 'win', null, c.root); windowBar(win, d.filename || 'main.py'); c.pop(win, .15);
  const body = $('div', 'code-body', null, win);
  const src = String(d.code || '').replace(/\n+$/, '').split('\n').slice(0, 14);
  const hl = new Set(d.highlight || []); const annos = {}; (d.annotations || []).forEach(a => annos[a.line] = a.text);
  const hasHL = hl.size > 0;
  const ts = c.times(src.length, .7, Math.max(1.5, c.D * .45), .22);
  const tHL = ts[src.length - 1] + .7;
  src.forEach((ln, i) => {
    const row = $('div', 'cl', `<i class="hlbg"></i><span class="cc"><span class="no">${i + 1}</span><span class="ct">${hlCode(ln, d.language) || ' '}</span></span>${annos[i + 1] ? `<span class="tag">${esc(annos[i + 1])}</span>` : ''}`, body);
    c.a(row, [{ opacity: 0, transform: 'translateX(-26px)' }, { opacity: 1, transform: 'none' }], ts[i], .4);
    if (hasHL) {
      c.a(row.querySelector('.cc'), [{ opacity: 1 }, { opacity: hl.has(i + 1) ? 1 : .32 }], tHL, .5, 'ease-out');
      if (hl.has(i + 1)) c.a(row.querySelector('.hlbg'), [{ opacity: 0 }, { opacity: 1 }], tHL, .5, 'ease-out');
    }
    const tg = row.querySelector('.tag'); if (tg) c.fade(tg, (hasHL ? tHL : ts[i]) + .3, .4);
  });
  if (d.caption) { const cp = $('div', 'capline card', `${icon('sparkles')}<span>${rich(d.caption)}</span>`, c.root); c.pop(cp, hasHL ? tHL + .3 : ts[src.length - 1] + .6, .6); }
};

SCENES.browser = c => {
  const d = c.data; c.heading(d.heading);
  const win = $('div', 'win', null, c.root); const bar = windowBar(win, ''); bar.querySelector('.win-title').remove();
  $('div', 'urlbar', `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${IC.lock}</svg><span>${esc(d.url || 'https://example.com')}</span>`, bar);
  c.pop(win, .15);
  const vp = $('div', 'viewport', null, win); vp.setAttribute('data-noaudit', '1');
  const img = d.image_data || d.image;
  if (img) {
    const im = $('img', 'shot', null, vp); im.src = img; IMG_WAIT.push(im);
    c.tick(l => { const over = Math.max(0, im.offsetHeight - vp.clientHeight); const u = easeInOut((l - 1.0) / Math.max(1, c.D - 2.6)); im.style.transform = `translateY(${-over * u}px)`; });
  } else {
    const site = $('div', 'site', null, vp);
    const nav = $('div', 'm-nav', `<span class="m-logo"></span><span>${esc(d.site || d.title || '')}</span><span class="m-link"></span><span class="m-link"></span><span class="m-link"></span><span class="m-btn"></span>`, site); c.fade(nav, .5);
    const blocks = (d.blocks && d.blocks.length) ? d.blocks : [{ type: 'hero', title: d.title || '', text: d.text || '', button: d.button || 'Get started' }, { type: 'cards', items: [{ icon: 'bolt', title: 'Fast', text: '' }, { icon: 'shield', title: 'Reliable', text: '' }, { icon: 'chart', title: 'Insightful', text: '' }] }];
    const ts = c.times(blocks.length, .9, Math.max(1.6, c.D * .5), .7);
    blocks.slice(0, 4).forEach((b, i) => {
      let e;
      if (b.type === 'hero') e = $('div', 'm-hero', `<h4>${rich(b.title)}</h4>${b.text ? `<p>${rich(b.text)}</p>` : ''}${b.button ? `<span class="m-cta">${esc(b.button)}</span>` : ''}`, site);
      else if (b.type === 'cards') e = $('div', 'm-cards', (b.items || []).slice(0, 3).map(x => `<div class="m-card">${icon(x.icon || 'box')}<b>${esc(x.title)}</b>${x.text ? `<span>${esc(x.text)}</span>` : ''}</div>`).join(''), site);
      else if (b.type === 'list') e = $('div', 'm-list', (b.rows || []).slice(0, 4).map(r => `<div class="m-row"><i></i><span>${esc(r[0])}</span><b>${esc(r[1] == null ? '' : r[1])}</b></div>`).join(''), site);
      else if (b.type === 'chart') { e = $('div', 'm-chart', `<h5>${esc(b.title || '')}</h5><div class="m-bars">${(b.values || [30, 55, 40, 75, 60, 90]).map(v => `<i style="height:${clamp(v, 5, 100)}%"></i>`).join('')}</div>`, site); e.querySelectorAll('.m-bars i').forEach((bar2, k) => c.a(bar2, [{ transform: 'scaleY(0)' }, { transform: 'scaleY(1)' }], ts[i] + .2 + k * .08, .6)); }
      else return;
      c.pop(e, ts[i], .6);
    });
    c.tick(l => { const over = Math.max(0, site.offsetHeight - vp.clientHeight); const u = easeInOut((l - (c.D * .5)) / Math.max(1, c.D * .35)); site.style.transform = `translateY(${-over * u}px)`; });
  }
  (d.callouts || []).slice(0, 4).forEach((co, i) => {
    const el = $('div', 'callout' + (co.x > 58 ? ' flip' : ''), `<div class="cr"></div><div class="cb">${esc(co.text)}</div>`, vp);
    el.style.left = co.x + '%'; el.style.top = co.y + '%';
    const t0 = Math.max(2.0, c.D * .45) + i * .9;
    c.a(el, [{ opacity: 0, transform: 'scale(.4)' }, { opacity: 1, transform: 'scale(1)' }], t0, .5, 'cubic-bezier(.3,1.5,.5,1)');
    c.tick(l => { const p = ((l - t0) % 1.6) / 1.6; const r = el.querySelector('.cr'); r.style.transform = `scale(${1 + .18 * Math.sin(p * Math.PI * 2)})`; });
  });
};

SCENES.table = c => {
  const d = c.data; c.heading(d.heading);
  const cols = (d.columns || []).slice(0, 5), rows = (d.rows || []).slice(0, 8);
  const mr = $('div', 'meta-row', null, c.root);
  const left = $('span', 'pill', d.source ? `source <b>${esc(d.source)}</b>` : '', mr);
  const cn = d.counter || null; const right = $('span', 'pill', '', mr); if (!cn) right.style.visibility = 'hidden';
  c.fade(mr, .2);
  const win = $('div', 'win tbl-win', null, c.root); windowBar(win, d.title || 'output.csv'); c.pop(win, .25);
  const tb = $('div', 'tb', null, win);
  const tbl = $('table', 'tbl', `<thead><tr>${cols.map(x => `<th>${esc(x)}</th>`).join('')}</tr></thead>`, tb);
  const tbody = $('tbody', '', null, tbl);
  const ts = c.times(rows.length, 1.0, Math.max(2, c.D - 1.8), .55);
  const acc = cssVar('--accent');
  rows.forEach((r, i) => {
    const tr = $('tr', '', r.slice(0, cols.length).map(x => `<td>${esc(x)}</td>`).join(''), tbody);
    c.a(tr, [{ opacity: 0, backgroundColor: rgba(acc, .35) }, { opacity: 1, backgroundColor: rgba(acc, .22), offset: .3 }, { opacity: 1, backgroundColor: rgba(acc, 0) }], ts[i], .9, 'ease-out');
  });
  if (cn) c.tick(l => { const u = easeOut((l - 1.0) / Math.max(1, c.D - 2.4)); right.innerHTML = `<b>${Math.round((cn.to || 0) * u).toLocaleString('en-US')}</b> ${esc(cn.label || 'records')}`; });
};

SCENES.stats = c => {
  const d = c.data; c.heading(d.heading);
  const box = $('div', 'stats', null, c.root);
  const items = (d.items || []).slice(0, 4), ts = c.times(items.length, .6, Math.max(1.2, c.D * .4), .5);
  items.forEach((it, i) => {
    const e = $('div', 'stat card', `<div class="sv"></div><div class="sl">${rich(it.label || '')}</div>`, box); c.pop(e, ts[i], .6);
    const sv = e.querySelector('.sv'), num = typeof it.value === 'number' ? it.value : (/^-?[\d,.]+$/.test(String(it.value)) ? parseFloat(String(it.value).replace(/,/g, '')) : null);
    const dec = it.decimals != null ? it.decimals : (num != null && !Number.isInteger(num) ? 1 : 0);
    c.tick(l => { if (num == null) { sv.textContent = (it.prefix || '') + it.value + (it.suffix || ''); return; } const u = easeOut((l - ts[i] - .2) / 1.5); const v = num * u; sv.textContent = (it.prefix || '') + v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + (it.suffix || ''); });
  });
};

SCENES.features = c => {
  const d = c.data; c.heading(d.heading);
  const g = $('div', 'grid', null, c.root);
  const items = (d.items || []).slice(0, 6), ts = c.times(items.length, .6, Math.max(1.4, c.D - 1.8), .45);
  items.forEach((it, i) => { const e = $('div', 'fc card', `<div class="fi">${icon(it.icon || 'sparkles')}</div><h3>${rich(it.title)}</h3>${it.text ? `<p>${rich(it.text)}</p>` : ''}`, g); c.pop(e, ts[i], .55); });
};

SCENES.steps = c => {
  const d = c.data; c.heading(d.heading);
  const box = $('div', 'steps', null, c.root);
  const items = (d.items || []).slice(0, 4), n = items.length, ts = c.times(n, .7, Math.max(1.6, c.D - 2.0), 1.0);
  const tr = $('div', 'track', '<i></i>', box);
  if (PORTRAIT) { tr.style.left = '47px'; } else { tr.style.left = (50 / n) + '%'; tr.style.right = (50 / n) + '%'; }
  const els = items.map((it, i) => { const e = $('div', 'step', `<div class="sn">${i + 1}</div><div class="tx"><h3>${rich(it.title)}</h3>${it.text ? `<p>${rich(it.text)}</p>` : ''}</div>`, box); c.a(e.querySelector('.tx'), [{ opacity: 0, transform: 'translateY(22px)' }, { opacity: 1, transform: 'none' }], ts[i], .6); c.a(e.querySelector('.sn'), [{ transform: 'scale(.6)', opacity: 0 }, { transform: 'scale(1)', opacity: 1 }], ts[i], .5, 'cubic-bezier(.3,1.5,.5,1)'); return e; });
  c.tick(l => {
    let px = 0; for (let i = 0; i < n; i++) { if (l >= ts[i]) { const nx = i < n - 1 ? ts[i + 1] : ts[i] + 1; px = (i + clamp((l - ts[i]) / Math.max(.2, nx - ts[i]), 0, 1)) / Math.max(1, n - 1); } }
    tr.style.setProperty('--px', clamp(px, 0, 1)); els.forEach((e, i) => { const sn = e.querySelector('.sn'); sn.style.setProperty('--on', l >= ts[i] ? 1 : 0); sn.style.color = l >= ts[i] ? 'var(--fg)' : 'var(--muted)'; });
  });
};

SCENES.compare = c => {
  const d = c.data; c.heading(d.heading);
  const box = $('div', 'cmp', null, c.root);
  const L = d.left || d.before || {}, R = d.right || d.after || {};
  const mk = (cls, side, mark) => { const e = $('div', 'side card ' + cls, `<h3>${rich(side.title || '')}</h3><ul>${(side.items || []).slice(0, 5).map(x => `<li><span class="m">${icon(mark)}</span><span>${rich(x)}</span></li>`).join('')}</ul>`, box); return e; };
  const l = mk('before', L, 'x'); const ar = $('div', 'arrow', icon('arrow'), box); const r = mk('after', R, 'check');
  c.a(l, [{ opacity: 0, transform: 'translateX(-60px)' }, { opacity: 1, transform: 'none' }], .4, .7);
  const t2 = Math.max(1.8, c.D * .42);
  c.a(ar, [{ opacity: 0, transform: 'scale(.4)' }, { opacity: 1, transform: 'scale(1)' }], t2 - .3, .5, 'cubic-bezier(.3,1.5,.5,1)');
  c.a(r, [{ opacity: 0, transform: 'translateX(60px)' }, { opacity: 1, transform: 'none' }], t2, .7);
  const stag = (el, base) => el.querySelectorAll('li').forEach((li, i) => c.a(li, [{ opacity: 0, transform: 'translateX(-20px)' }, { opacity: 1, transform: 'none' }], base + i * .28, .5));
  stag(l, .9); stag(r, t2 + .5);
};

SCENES.cta = c => {
  const d = c.data;
  const mark = $('div', 't-mark', d.icon ? icon(d.icon) : esc((M.product || 'P').trim().charAt(0).toUpperCase()), c.root); mark.style.marginBottom = '34px'; mark.style.width = mark.style.height = '104px'; mark.style.fontSize = '58px';
  if (d.icon) { mark.firstChild.style.width = '56%'; mark.firstChild.style.height = '56%'; }
  c.a(mark, [{ opacity: 0, transform: 'scale(.4)' }, { opacity: 1, transform: 'scale(1)' }], .1, .7, 'cubic-bezier(.3,1.45,.5,1)');
  const h = $('div', 'cta-h', rich(d.headline || 'Try it today'), c.root); c.a(h, [{ opacity: 0, transform: 'translateY(30px)' }, { opacity: 1, transform: 'none' }], .35, .7);
  let t = 1.1;
  if (d.command) {
    const box = $('div', 'cmd-box', '<span class="p">$</span><span class="tx"></span><span class="cursor"></span>', c.root); const tx = box.querySelector('.tx'), cur = box.querySelector('.cursor'); c.pop(box, t, .5);
    const t0 = t + .5, dur = Math.min(1.8, d.command.length / 30);
    c.tick(l => { const n = Math.floor(clamp((l - t0) / dur, 0, 1) * d.command.length); tx.innerHTML = hlCmd(d.command.slice(0, n)); cur.style.opacity = (l > t0 - .2 && (l < t0 + dur || Math.floor(l * 2.2) % 2 === 0)) ? 1 : 0; });
    t += 1.2 + dur * .5;
  }
  if (d.url) { const u = $('div', 'url', `${icon('link')}<span>${esc(d.url)}</span>`, c.root); c.pop(u, t, .6); t += .5; }
  if (d.links && d.links.length) { const lw = $('div', 'links', null, c.root); d.links.slice(0, 4).forEach((x, i) => { const p = $('span', 'pill', esc(x), lw); c.pop(p, t + i * .15, .5); }); }
  if (d.sub) { const s = $('div', 'ch-s', rich(d.sub), c.root); s.style.marginTop = '30px'; c.pop(s, t + .3, .6); }
};

/* ---------- custom (bespoke) scene: Claude authors project-specific markup + CSS + animation ---------- */
const H = {
  clamp, easeOut, easeInOut, rich, esc, rgba, cssVar, icon, $,
  /* stagger an animation over many elements: H.stagger(els, [kf0,kf1], t0, step, dur) */
  stagger(c, els, kf, t0 = .5, step = .15, d = .55) { return [...els].map((e, i) => c.a(e, kf, t0 + i * step, d)); },
  /* typewriter into an element: H.type(c, el, text, t0, cps, {cursor:true, html:fn}) */
  type(c, el, text, t0 = .5, cps = 32, o = {}) {
    const cur = o.cursor === false ? null : $('i', 'cursor', null, null); const tx = document.createTextNode(''); el.textContent = ''; el.appendChild(tx); if (cur) el.appendChild(cur);
    const dur = text.length / cps;
    c.tick(l => { const n = Math.floor(clamp((l - t0) / dur, 0, 1) * text.length); tx.textContent = text.slice(0, n); if (cur) cur.style.opacity = (l >= t0 && (l < t0 + dur || Math.floor(l * 2.2) % 2 === 0)) ? 1 : 0; });
    return t0 + dur;
  },
  /* count a number up: H.count(c, el, 1248, t0, dur, {prefix:'$', suffix:'k', dec:0}) */
  count(c, el, to, t0 = .5, dur = 1.4, o = {}) { const dec = o.dec || 0; c.tick(l => { const u = easeOut((l - t0) / dur); el.textContent = (o.prefix || '') + (to * u).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }) + (o.suffix || ''); }); },
  /* draw an SVG path (stroke) over time */
  draw(c, path, t0 = .5, d = .9) { const len = path.getTotalLength(); path.style.strokeDasharray = len; return c.a(path, [{ strokeDashoffset: len }, { strokeDashoffset: 0 }], t0, d, 'ease-in-out'); },
  /* move an element (HTML via transform, SVG via transform attr) along an SVG path; loop optional */
  along(c, el, path, t0 = .5, d = 1.2, o = {}) { const len = path.getTotalLength(); c.tick(l => { let u = (l - t0) / d; if (o.loop) u = u < 0 ? -1 : ((u % 1) + 1) % 1; if (u < 0 || (!o.loop && u > 1)) { el.style.opacity = o.hide === false ? 1 : 0; return; } el.style.opacity = 1; const p = path.getPointAtLength(clamp(easeInOut(u), 0, 1) * len); if (el instanceof SVGElement) el.setAttribute('transform', `translate(${p.x},${p.y})`); else el.style.transform = `translate(${p.x}px,${p.y}px)`; }); },
  /* continuous looping value 0..1 : H.loop(c, period, t0, fn(u)) */
  loop(c, period, t0, fn) { c.tick(l => { if (l >= t0) fn((((l - t0) % period) + period) % period / period, l - t0); }); },
  /* run fn(l) every frame with scene-local time */
  tick(c, fn) { c.tick(fn); }
};
SCENES.custom = c => {
  const d = c.data; c.heading(d.heading);
  const box = $('div', 'custom cs-' + c.idx, null, c.root);
  if (d.css) { const st = $('style', '', String(d.css).replace(/&/g, '.cs-' + c.idx), c.root); }
  if (d.html) box.innerHTML = d.html;
  if (d.js) { const fn = new Function('c', 'box', 'H', '$', 'icon', 'dims', d.js); fn(c, box, H, $, icon, { W: DIMS[0], H: DIMS[1], portrait: PORTRAIT, D: c.D }); }
};

/* ---------- build ---------- */
const scenes = SB.scenes || [];
const INFO = []; let cursor = 0;
const bg = $('div', '', null, stage); bg.id = 'bg';
bg.className = 'bg-' + (M.bg || 'grid');
const gridbg = $('div', 'gridbg', null, bg), b1 = $('div', 'blob b1', null, bg), b2 = $('div', 'blob b2', null, bg);
scenes.forEach((sc, i) => {
  const D = Math.max(1.5, +sc.duration || 5), S = cursor; cursor += D;
  const root = $('section', 'scene s-' + sc.type, null, stage);
  const fn = SCENES[sc.type];
  const ctx = makeCtx(sc, S, D, root, i);
  if (fn) { try { fn(ctx); } catch (e) { console.error('scene build error', i, sc.type, e); root.innerHTML = '<div class="h">Scene error: ' + esc(sc.type) + '</div>'; } }
  else root.innerHTML = '<div class="h">Unknown scene type: ' + esc(sc.type) + '</div>';
  const last = i === scenes.length - 1, a = .6 / D, b = (D - .4) / D;
  const kf = [{ opacity: 0, transform: 'translateY(28px) scale(.985)', filter: 'blur(10px)', offset: 0, easing: EASE }, { opacity: 1, transform: 'translateY(0) scale(1)', filter: 'none', offset: a }];
  if (!last) kf.push({ opacity: 1, transform: 'translateY(0) scale(1)', filter: 'none', offset: b, easing: 'ease-in' }, { opacity: 0, transform: 'translateY(-20px) scale(1.01)', filter: 'blur(8px)', offset: 1 });
  else kf.push({ opacity: 1, transform: 'translateY(0) scale(1)', filter: 'none', offset: 1 });
  const an = root.animate(kf, { delay: Math.round(S * 1000), duration: Math.round(D * 1000), fill: 'both', easing: 'linear' }); an.pause(); ANIMS.push(an);
  INFO.push({ S, D, type: sc.type, root, scene: sc });
});
const TOTAL = cursor + .6;
window.__duration = TOTAL;
window.__scenes = INFO.map(x => ({ S: x.S, D: x.D, type: x.type }));

/* chrome: brand, url, caption, progress */
const brand = $('div', '', `<span class="mini">${esc(String(M.product || 'P').trim().charAt(0).toUpperCase())}</span><span>${esc(M.product || '')}</span>`, stage); brand.id = 'brand';
const urltag = $('div', '', esc(M.url || ''), stage); urltag.id = 'urltag';
const cap = $('div', '', '', stage); cap.id = 'caption';
const prog = $('div', '', '<i></i>', stage); prog.id = 'progress';
const chunks = [];
INFO.forEach(s => {
  const text = String(s.scene.narration || '').trim(); if (!text) return;
  const sents = (text.match(/[^.!?]+[.!?]+["')\]]*|[^.!?]+$/g) || [text]).map(x => x.trim()).filter(Boolean);
  const lead = .5, tail = .45, span = Math.max(1, s.D - lead - tail), tot = sents.reduce((a, x) => a + x.length, 0); let t = s.S + lead;
  sents.forEach(x => { const dur = span * x.length / tot; chunks.push({ t0: t, t1: t + dur, text: x }); t += dur; });
});
window.__chunks = chunks;
let capIdx = -2;
TICKS.push(t => {
  prog.firstChild.style.width = (clamp(t / TOTAL, 0, 1) * 100) + '%';
  const cur = INFO.find(s => t >= s.S && t < s.S + s.D) || INFO[INFO.length - 1];
  const showChrome = M.brand && cur && cur.type !== 'title' && cur.type !== 'cta';
  const o = showChrome ? clamp((t - cur.S) / .5, 0, 1) * clamp((cur.S + cur.D - t) / .4, 0, 1) : 0;
  brand.style.opacity = o; urltag.style.opacity = o;
  if (!M.captions) { cap.style.opacity = 0; return; }
  const ci = chunks.findIndex(ch => t >= ch.t0 && t < ch.t1);
  if (ci < 0) { cap.style.opacity = 0; return; }
  if (ci !== capIdx) { cap.textContent = chunks[ci].text; capIdx = ci; }
  const ch = chunks[ci]; cap.style.opacity = clamp(Math.min((t - ch.t0) / .25, (ch.t1 - t) / .25), 0, 1);
});
/* background drift */
TICKS.push(t => { b1.style.transform = `translate(${Math.sin(t * .23) * 90}px,${Math.cos(t * .19) * 70}px)`; b2.style.transform = `translate(${Math.cos(t * .21) * -90}px,${Math.sin(t * .17) * 60}px)`; gridbg.style.transform = `translate(${(t * 6) % 70}px,${(t * 4) % 70}px)`; });
/* scene visibility */
INFO.forEach((s, i) => TICKS.push(t => { const last = i === INFO.length - 1; s.root.style.visibility = (t >= s.S - .001 && (t < s.S + s.D + .001 || last)) ? 'visible' : 'hidden'; }));

/* ---------- API ---------- */
window.__seek = t => { t = clamp(t, 0, TOTAL); const ms = t * 1000; for (let i = 0; i < ANIMS.length; i++) ANIMS[i].currentTime = ms; for (let i = 0; i < TICKS.length; i++) TICKS[i](t); };
window.__audit = idx => {
  const s = INFO[idx]; const t = Math.min(s.S + s.D - .6, s.S + s.D * .86); window.__seek(t);
  const issues = [], sr = stage.getBoundingClientRect(), capReserve = PORTRAIT ? 330 : 205, sc = sr.width / DIMS[0];
  const bottom = sr.top + (DIMS[1] - capReserve + 6) * sc;
  s.root.querySelectorAll('*').forEach(el => {
    if (el.closest('svg') && el.tagName !== 'svg') return; if (el.closest('[data-noaudit]') && !el.hasAttribute('data-noaudit')) return;
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || +cs.opacity < .05 || cs.display === 'none') return;
    let hidden = false; for (let p = el.parentElement; p && p !== s.root; p = p.parentElement) { if (+getComputedStyle(p).opacity < .05) { hidden = true; break; } } if (hidden) return;
    const hasText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (!hasText && !['IMG'].includes(el.tagName)) return;
    const r = el.getBoundingClientRect(); if (r.width < 2 || r.height < 2) return;
    const tag = (el.className && el.className.baseVal === undefined ? '.' + String(el.className).split(' ')[0] : el.tagName.toLowerCase()) + ' "' + (el.textContent || '').trim().slice(0, 34) + '"';
    if (r.left < sr.left - 3 || r.right > sr.right + 3 || r.top < sr.top - 3) issues.push(`off-stage: ${tag}`);
    else if (r.bottom > bottom) issues.push(`collides with caption zone: ${tag}`);
    if (el.scrollWidth > el.clientWidth + 3 && cs.overflow !== 'visible' && cs.textOverflow !== 'ellipsis') issues.push(`text clipped: ${tag}`);
    if (cs.textOverflow === 'ellipsis' && el.scrollWidth > el.clientWidth + 3) issues.push(`truncated with ellipsis: ${tag}`);
  });
  return [...new Set(issues)].slice(0, 8);
};

/* ---------- ready + player ---------- */
window.__ready = (async () => {
  try { await document.fonts.ready; } catch (e) { }
  await Promise.all(IMG_WAIT.map(im => im.decode ? im.decode().catch(() => { }) : Promise.resolve()));
  LAYOUTS.forEach(fn => { try { fn(); } catch (e) { console.error('layout error', e); } });
  window.__seek(0);
  return true;
})();

function fit() { if (RENDER) return; const ui = EMBED ? 0 : 54; const s = Math.min(innerWidth / DIMS[0], (innerHeight - ui) / DIMS[1]); stage.style.transform = `scale(${s})`; wrap.style.paddingBottom = ui + 'px'; }
window.addEventListener('resize', () => { fit(); window.__ready.then(() => { LAYOUTS.forEach(f => f()); }); });
fit();
if (!RENDER) {
  const ui = $('div', '', '<button id="pp">❚❚</button><input id="sc" type="range" min="0" max="1000" value="0"><span id="tm">0:00</span>', document.body); ui.id = 'ui';
  let playing = true, t0 = performance.now(), off = 0;
  const pp = ui.querySelector('#pp'), sc = ui.querySelector('#sc'), tm = ui.querySelector('#tm');
  const fmt = x => Math.floor(x / 60) + ':' + String(Math.floor(x % 60)).padStart(2, '0');
  pp.onclick = () => { if (playing) off += (performance.now() - t0) / 1000; playing = !playing; pp.textContent = playing ? '❚❚' : '▶'; if (playing) t0 = performance.now(); };
  sc.oninput = () => { off = sc.value / 1000 * TOTAL; t0 = performance.now(); window.__seek(off); };
  window.__ready.then(() => {
    const loop = () => { if (playing) { let t = off + (performance.now() - t0) / 1000; if (t >= TOTAL) { off = 0; t0 = performance.now(); t = 0; } window.__seek(t); sc.value = t / TOTAL * 1000; tm.textContent = fmt(t) + ' / ' + fmt(TOTAL); } requestAnimationFrame(loop); };
    loop();
  });
}
})();
