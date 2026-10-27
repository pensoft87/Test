// Shared by etiqueta.html (6 x 2.5 in label) and muestra.html (2.3 x 1.5 in sample sachet):
// the copy of each variant and the drawing helpers. css() reads the palette off #label.
const VARIANTES = {
  'sin-fragancia': {
    cinta: 'Sin fragancia',
    propiedades: 'Vaselina nutritiva formulada para ayudar a sellar la hidratación, suavizar, aportar brillo ' +
                 'y facilitar el peinado. Con manteca de karité y aceites de jojoba y argán que aportan nutrición.',
    ingredientes: 'Manteca de karité, aceite de salvado de arroz, aceite de jojoba, aceite de argán, vaselina y vitamina E.',
  },
  'batana': {
    cinta: 'Enriquecida con batana',
    propiedades: 'Vaselina nutritiva formulada con ingredientes nutritivos como la batana, jojoba, argán y manteca ' +
                 'de karité que aportan nutrición y ayudan a sellar la hidratación, suavizar, dar brillo y ' +
                 'facilitar el peinado.',
    ingredientes: 'Aceite de batana, manteca de karité, aceite de salvado de arroz, aceite de jojoba, aceite de ' +
                  'argán, vaselina, vitamina E y fragancia.',
  },
};
const MODO = 'Aplicar de medios a puntas y peinar como de costumbre.';

const NS = 'http://www.w3.org/2000/svg';
const css = n => getComputedStyle(document.getElementById('label')).getPropertyValue(n).trim();
function el(parent, tag, attrs = {}, text) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (text != null) e.textContent = text;
  parent.appendChild(e);
  return e;
}

// ---- shared gradients -------------------------------------------------------------------
function defs(svg, id) {
  const d = el(svg, 'defs');
  const lin = (name, stops, x2 = 0, y2 = 1, extra = {}) => {
    const g = el(d, 'linearGradient', { id: name + id, x1: 0, y1: 0, x2, y2, ...extra });
    stops.forEach(([o, c]) => el(g, 'stop', { offset: o, 'stop-color': c }));
  };
  lin('gold', [[0, '#7a4e0e'], [.22, '#c8963c'], [.45, '#fff0b5'], [.6, '#e3b558'], [.82, '#a8721f'], [1, '#6e4409']], 1, 1);
  lin('goldV', [[0, '#fff3c4'], [.35, '#e7bd5e'], [.7, '#b07a22'], [1, '#7a4e0e']]);
  lin('leaf', [[0, css('--leaf-a')], [1, css('--leaf-b')]], 1, 1);
  lin('ribbon', [[0, css('--ribbon-a')], [.55, css('--ribbon-b')], [1, css('--ribbon-c')]]);
  lin('ribbonBack', [[0, css('--ribbon-c')], [1, css('--ribbon-b')]]);
  lin('brush', [[0, css('--brush-a')], [1, css('--brush-b')]], 1, 0);
  const rad = (name, stops, attrs) => {
    const g = el(d, 'radialGradient', { id: name + id, ...attrs });
    stops.forEach(([o, c, a = 1]) => el(g, 'stop', { offset: o, 'stop-color': c, 'stop-opacity': a }));
  };
  rad('oval', [[0, css('--oval-in')], [.7, css('--oval-in')], [1, css('--oval-out')]], { cx: .5, cy: .42, r: .62 });
  rad('glow', [[0, '#fff8dc', .95], [.5, '#fff3c8', .45], [1, '#fff3c8', 0]], {});
  rad('drop', [[0, css('--drop-a')], [.55, css('--drop-b')], [1, css('--drop-c')]], { cx: .38, cy: .62, r: .7 });
  rad('seal', [[0, css('--seal-a')], [1, css('--seal-b')]], { cx: .4, cy: .35, r: .75 });
  const f = el(d, 'filter', { id: 'rough' + id, x: '-5%', y: '-20%', width: '110%', height: '140%' });
  el(f, 'feTurbulence', { type: 'fractalNoise', baseFrequency: '0.035 0.18', numOctaves: 3, seed: 7, result: 'n' });
  el(f, 'feDisplacementMap', { in: 'SourceGraphic', in2: 'n', scale: 16, xChannelSelector: 'R', yChannelSelector: 'G' });
  const sh = el(d, 'filter', { id: 'shadow' + id, x: '-20%', y: '-20%', width: '140%', height: '140%' });
  el(sh, 'feDropShadow', { dx: 0, dy: 3, stdDeviation: 4, 'flood-color': '#3b2200', 'flood-opacity': .28 });
  return id;
}

// ---- leaves --------------------------------------------------------------------------------
// A leafy branch: a curved stem from (x, y) heading at `ang` degrees, `len` long, bending by `bend`,
// with `n` pairs of pointed leaves that shrink toward the tip, and one leaf at the tip.
function branch(g, id, { x, y, ang, len, bend = 0.3, n = 5, size = 60, gold = false, flip = 1, op = 1 }) {
  const a = ang * Math.PI / 180, nx = -Math.sin(a), ny = Math.cos(a);
  const ex = x + Math.cos(a) * len, ey = y + Math.sin(a) * len;
  const cx = (x + ex) / 2 + nx * len * bend * flip, cy = (y + ey) / 2 + ny * len * bend * flip;
  const P = t => [(1 - t) ** 2 * x + 2 * (1 - t) * t * cx + t * t * ex, (1 - t) ** 2 * y + 2 * (1 - t) * t * cy + t * t * ey];
  const T = t => { const dx = 2 * (1 - t) * (cx - x) + 2 * t * (ex - cx), dy = 2 * (1 - t) * (cy - y) + 2 * t * (ey - cy); return Math.atan2(dy, dx); };
  const b = el(g, 'g', { opacity: op });
  el(b, 'path', { d: `M${x},${y} Q${cx},${cy} ${ex},${ey}`, fill: 'none', stroke: `url(#gold${id})`, 'stroke-width': size * 0.07, 'stroke-linecap': 'round' });
  const leaf = (px, py, rot, s, golden) => {
    const L = s, W = s * 0.36;
    const lg = el(b, 'g', { transform: `translate(${px},${py}) rotate(${rot * 180 / Math.PI})` });
    el(lg, 'path', { d: `M0,0 C${L * .25},${-W} ${L * .7},${-W * .9} ${L},0 C${L * .7},${W * .9} ${L * .25},${W} 0,0Z`,
                     fill: golden ? `url(#goldV${id})` : `url(#leaf${id})`, stroke: `url(#gold${id})`, 'stroke-width': Math.max(1.4, s * 0.035) });
    el(lg, 'path', { d: `M${L * .04},0 Q${L * .5},${-W * .12} ${L * .92},0`, fill: 'none',
                     stroke: golden ? '#9c6a1c' : css('--leaf-vein'), 'stroke-width': Math.max(1, s * 0.022), opacity: .8 });
  };
  for (let i = 0; i < n; i++) {
    const t = 0.18 + 0.72 * i / Math.max(n - 1, 1);
    const [px, py] = P(t), th = T(t), s = size * (1 - 0.45 * t);
    leaf(px, py, th - 0.75, s, gold && i % 2 === 0);
    leaf(px, py, th + 0.75, s * 0.95, gold && i % 2 === 1);
  }
  leaf(ex, ey, T(1), size * 0.6, gold);
}

function sparkle(g, x, y, r, id, op = 1) {
  const k = r * 0.2;
  el(g, 'path', { d: `M${x},${y - r} L${x + k},${y - k} L${x + r},${y} L${x + k},${y + k} L${x},${y + r} L${x - k},${y + k} L${x - r},${y} L${x - k},${y - k}Z`,
                  fill: `url(#goldV${id})`, opacity: op });
}

// The four "free" seals, drawn into `box`
function freeSeals(box) {
  const seals = [
    ['PARABEN', 'FREE', 'leaf'], ['SILICONE', 'FREE', 'flask'], ['CRUELTY', 'FREE', 'bunny'], ['SULFATE', 'FREE', 'bubbles'],
  ];
  seals.forEach(([a, b, icon], i) => {
    const s = el(box, 'svg', { viewBox: '0 0 86 86' });
    const id = defs(s, 'fr' + i);
    el(s, 'circle', { cx: 43, cy: 43, r: 40, fill: css('--qr-card'), stroke: `url(#gold${id})`, 'stroke-width': 4 });
    el(s, 'circle', { cx: 43, cy: 43, r: 33.5, fill: 'none', stroke: css('--accent'), 'stroke-width': 1.2, opacity: .6 });
    const ic = el(s, 'g', { fill: 'none', stroke: css('--accent-dark'), 'stroke-width': 2.4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
    if (icon === 'leaf') { el(ic, 'path', { d: 'M33,44 C34,30 42,22 54,20 C53,33 46,41 35,42' }); el(ic, 'path', { d: 'M33,46 C38,38 43,33 49,27' }); }
    if (icon === 'flask') { el(ic, 'path', { d: 'M38,19 h10 M40,19 v9 l-9,15 a3,3 0 0 0 3,4 h18 a3,3 0 0 0 3,-4 l-9,-15 v-9' }); el(ic, 'path', { d: 'M34,38 h18' }); }
    if (icon === 'bunny') {
      el(ic, 'path', { d: 'M38,32 C34,22 35,16 38,16 C41,16 42,24 41,31 M47,31 C47,23 49,16 52,17 C55,18 53,25 49,32' });
      el(ic, 'path', { d: 'M36,42 a9,8 0 1 1 18,0 a9,8 0 1 1 -18,0' }); el(ic, 'circle', { cx: 41.5, cy: 40, r: .8, fill: css('--accent-dark') });
    }
    if (icon === 'bubbles') { el(ic, 'circle', { cx: 38, cy: 36, r: 8 }); el(ic, 'circle', { cx: 51, cy: 28, r: 5 }); el(ic, 'circle', { cx: 51, cy: 42, r: 4 }); }
    el(s, 'text', { x: 43, y: 58, 'text-anchor': 'middle', 'font-family': 'PT Serif', 'font-weight': 700, 'font-size': 9.6, fill: css('--accent-dark'), 'letter-spacing': .2 }, a);
    el(s, 'text', { x: 43, y: 68, 'text-anchor': 'middle', 'font-family': 'PT Serif', 'font-weight': 700, 'font-size': 9.6, fill: css('--accent-dark') }, b);
  });
}

// The four benefits, each a round plum icon over its caption, drawn into `box`
function beneficios(box) {
  const items = [
    ['Sella la hidratación', 'drop'], ['Suaviza', 'feather'], ['Aporta brillo', 'shine'], ['Facilita el peinado', 'comb'],
  ];
  items.forEach(([label, icon], i) => {
    const d = document.createElement('div'); d.className = 'b'; box.appendChild(d);
    const s = el(d, 'svg', { viewBox: '0 0 78 78' });
    const id = defs(s, 'bn' + i);
    el(s, 'circle', { cx: 39, cy: 39, r: 36, fill: `url(#seal${id})`, stroke: `url(#gold${id})`, 'stroke-width': 3.5 });
    const ic = el(s, 'g', { fill: 'none', stroke: '#fbe7b5', 'stroke-width': 2.6, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' });
    if (icon === 'drop') { el(ic, 'path', { d: 'M39,18 C44,27 51,34 51,43 a12,12 0 0 1 -24,0 C27,34 34,27 39,18Z' }); el(ic, 'path', { d: 'M33,44 l4,4 l8,-9' }); }
    if (icon === 'feather') { el(ic, 'path', { d: 'M24,55 C30,40 40,26 55,20 C55,36 46,47 31,50' }); el(ic, 'path', { d: 'M27,53 L46,32 M34,46 h9 M39,40 h8' }); }
    if (icon === 'shine') {
      el(ic, 'path', { d: 'M39,19 L42.5,35.5 L59,39 L42.5,42.5 L39,59 L35.5,42.5 L19,39 L35.5,35.5Z', fill: '#fbe7b5', stroke: 'none' });
      el(ic, 'path', { d: 'M54,22 l0,6 M51,25 l6,0 M24,52 l0,5 M21.5,54.5 l5,0' });
    }
    if (icon === 'comb') {
      el(ic, 'path', { d: 'M22,33 h34 a3,3 0 0 1 3,3 v3 h-40 v-3 a3,3 0 0 1 3,-3Z', fill: '#fbe7b5' });
      for (let x = 23; x <= 56; x += 4.6) el(ic, 'path', { d: `M${x},39 v${x < 40 ? 14 : 10}` });
    }
    const sp = document.createElement('span'); sp.textContent = label; d.appendChild(sp);
  });
}

// Justified copy without hyphens: each paragraph gets the type size (within 0.5 px of the design size, or data-range)
// and letter spacing (within 0.4 px) whose line breaks leave the evenest, narrowest word gaps.
function justify(p) {
  const words = p.textContent.trim().split(/\s+/);
  p.innerHTML = words.map(w => `<span>${w}</span>`).join(' ');
  const spans = [...p.children], base = parseFloat(getComputedStyle(p).fontSize), W = p.clientWidth;
  p.style.textAlign = 'left';
  let best = null;
  const range = +(p.dataset.range || 0.5);
  for (let ds = -range; ds <= range + .001; ds += 0.125) for (let ls = -0.4; ls <= 0.401; ls += 0.1) {
    p.style.fontSize = (base + ds) + 'px'; p.style.letterSpacing = ls + 'px';
    const lines = [];
    for (const sp of spans) {
      const r = sp.getBoundingClientRect();
      const last = lines[lines.length - 1];
      if (last && Math.abs(last.top - r.top) < 4) { last.right = r.right; last.n++; } else lines.push({ top: r.top, left: r.left, right: r.right, n: 1 });
    }
    const space = (base + ds) * 0.27;
    let cost = Math.abs(ds) * 2 + Math.max(0, -ls) * 6;               // stay near the design size
    lines.forEach((l, i) => {
      const slack = W - (l.right - l.left);
      if (i === lines.length - 1) cost += slack > W * 0.65 ? 40 : 0;          // no lonely last word
      else cost += l.n > 1 ? (slack / (l.n - 1) / space) ** 2 * (l.n - 1) : 50;
    });
    if (!best || cost < best.cost) best = { cost, ds, ls };
  }
  p.style.fontSize = (base + best.ds) + 'px'; p.style.letterSpacing = best.ls + 'px'; p.style.textAlign = '';
}
