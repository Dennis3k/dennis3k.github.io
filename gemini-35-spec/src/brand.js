/* brand.js — brand marks built geometrically in code (no bitmaps, no redraw-by-hand) */
import { TAU, roundRect, rgba, font } from './core.js';

export const G_BLUE = '#4285F4', G_RED = '#EA4335', G_YEL = '#FBBC05', G_GRN = '#34A853';
/* Gemini gradient ramp: blue -> violet -> pink -> red */
export const GEM_RAMP = [
  [0.00, '#2E7CF6'],
  [0.28, '#5A8CF8'],
  [0.52, '#9B72CB'],
  [0.76, '#D96570'],
  [1.00, '#EA4335'],
];
export function gemGrad(ctx, x0, y0, x1, y1) {
  const g = ctx.createLinearGradient(x0, y0, x1, y1);
  for (const [p, c] of GEM_RAMP) g.addColorStop(p, c);
  return g;
}
/** blue-only ramp used on dark stages */
export function blueGrad(ctx, x0, y0, x1, y1) {
  const g = ctx.createLinearGradient(x0, y0, x1, y1);
  g.addColorStop(0, '#9CC6FF'); g.addColorStop(0.5, '#4E92F7'); g.addColorStop(1, '#2A63D8');
  return g;
}

/* ---------- Gemini sparkle: 4-point star, concave sides ---------- */
export function sparklePath(ctx, x, y, r, rot = 0, pinch = 0.085) {
  ctx.beginPath();
  for (let i = 0; i < 4; i++) {
    const a0 = rot + (i * TAU) / 4;
    const a1 = rot + ((i + 1) * TAU) / 4;
    const p0 = [x + Math.cos(a0) * r, y + Math.sin(a0) * r];
    const p1 = [x + Math.cos(a1) * r, y + Math.sin(a1) * r];
    const am = (a0 + a1) / 2;
    const c = [x + Math.cos(am) * r * pinch, y + Math.sin(am) * r * pinch];
    if (i === 0) ctx.moveTo(p0[0], p0[1]);
    ctx.quadraticCurveTo(c[0], c[1], p1[0], p1[1]);
  }
  ctx.closePath();
}
export function sparkle(ctx, x, y, r, { rot = 0, fill = null, alpha = 1, glowPx = 0 } = {}) {
  ctx.save();
  ctx.globalAlpha *= alpha;
  if (glowPx > 0) {
    ctx.save(); ctx.filter = `blur(${glowPx}px)`; ctx.globalAlpha *= 0.55;
    sparklePath(ctx, x, y, r * 1.12, rot); ctx.fillStyle = fill || gemGrad(ctx, x - r, y - r, x + r, y + r); ctx.fill();
    ctx.restore();
  }
  sparklePath(ctx, x, y, r, rot);
  ctx.fillStyle = fill || gemGrad(ctx, x - r, y - r, x + r, y + r);
  ctx.fill();
  ctx.restore();
}
/** tiny 4-ray twinkle */
export function twinkle(ctx, x, y, r, a = 1, color = '#fff') {
  ctx.save(); ctx.globalAlpha *= a; ctx.fillStyle = color;
  sparklePath(ctx, x, y, r, 0, 0.02); ctx.fill();
  ctx.restore();
}

/* ---------- Google G ---------- */
/* math angles (ccw, 0 = 3 o'clock) converted to canvas (cw, y-down) */
const A = (deg) => (-deg * Math.PI) / 180;
export function googleG(ctx, x, y, R, { alpha = 1, mono = null } = {}) {
  const w = R * 0.30;             // stroke width
  const rr = R - w / 2;           // centre-line radius
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.lineWidth = w;
  ctx.lineCap = 'butt';
  const seg = (from, to, color) => {
    ctx.strokeStyle = mono || color;
    ctx.beginPath();
    ctx.arc(x, y, rr, A(from), A(to), true); // ccw in math == anticlockwise=true in canvas
    ctx.stroke();
  };
  seg(52, 162, G_RED);
  seg(162, 222, G_YEL);
  seg(222, 292, G_GRN);
  seg(292, 360, G_BLUE);
  // Перекладина. Её верхняя грань лежит ровно на центре круга — там же,
  // где кончается синяя дуга. Если поднять её выше, угол торчит в пустой
  // середине буквы отдельным прямоугольным зубцом.
  ctx.save();
  ctx.beginPath(); ctx.arc(x, y, R, 0, TAU); ctx.clip();   // правый край режет сам круг
  ctx.fillStyle = mono || G_BLUE;
  roundRect(ctx, x + R * 0.04, y, R * 1.10, w, w * 0.08);
  ctx.fill();
  ctx.restore();
  ctx.restore();
}

/* ---------- small app marks for the home screen ---------- */
export function iconDrive(ctx, x, y, s) {
  const h = s * 0.76, w = s * 0.86;
  ctx.save(); ctx.translate(x, y);
  const L = [-w / 2, h / 2], R = [w / 2, h / 2], T = [0, -h / 2];
  const ml = [(L[0] + T[0]) / 2, (L[1] + T[1]) / 2], mr = [(R[0] + T[0]) / 2, (R[1] + T[1]) / 2], mb = [0, h / 2];
  const tri = (a, b, c, col) => { ctx.fillStyle = col; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.lineTo(c[0], c[1]); ctx.closePath(); ctx.fill(); };
  tri(L, ml, mb, '#1A73E8'); tri(ml, T, mr, '#34A853');
  tri(mr, R, mb, '#FBBC05'); tri(ml, mr, mb, '#4285F4');
  ctx.restore();
}
export function iconGmail(ctx, x, y, s) {
  const w = s * 0.92, h = s * 0.68, r = s * 0.08;
  ctx.save(); ctx.translate(x, y);
  ctx.fillStyle = '#fff'; roundRect(ctx, -w / 2, -h / 2, w, h, r); ctx.fill();
  ctx.save(); roundRect(ctx, -w / 2, -h / 2, w, h, r); ctx.clip();
  ctx.fillStyle = '#EA4335'; ctx.beginPath();
  ctx.moveTo(-w / 2, -h / 2); ctx.lineTo(0, h * 0.08); ctx.lineTo(w / 2, -h / 2);
  ctx.lineTo(w / 2, -h / 2 + h * 0.18); ctx.lineTo(0, h * 0.30); ctx.lineTo(-w / 2, -h / 2 + h * 0.18);
  ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#C5221F'; ctx.fillRect(-w / 2, -h / 2, w * 0.06, h);
  ctx.fillStyle = '#4285F4'; ctx.fillRect(w / 2 - w * 0.06, -h / 2, w * 0.06, h);
  ctx.restore(); ctx.restore();
}
export function iconPhotos(ctx, x, y, s) {
  const r = s * 0.44, k = r * 0.52;
  const blade = (ang, col) => {
    ctx.save(); ctx.translate(x, y); ctx.rotate(ang); ctx.fillStyle = col;
    ctx.beginPath(); ctx.moveTo(0, 0);
    ctx.arc(0, -k, k, Math.PI * 0.5, Math.PI * 1.5, false);
    ctx.lineTo(0, -k * 2 + k * 0); ctx.closePath(); ctx.fill(); ctx.restore();
  };
  blade(0, '#EA4335'); blade(Math.PI / 2, '#FBBC05'); blade(Math.PI, '#34A853'); blade(-Math.PI / 2, '#4285F4');
}
export function iconGemini(ctx, x, y, s, { bg = true } = {}) {
  if (bg) {
    ctx.save();
    const g = ctx.createLinearGradient(x - s / 2, y - s / 2, x + s / 2, y + s / 2);
    g.addColorStop(0, '#ffffff'); g.addColorStop(1, '#F1F5FF');
    ctx.fillStyle = g; roundRect(ctx, x - s / 2, y - s / 2, s, s, s * 0.26); ctx.fill(); ctx.restore();
  }
  sparkle(ctx, x, y, s * 0.36, {});
}
export function wordGemini(ctx, x, y, size, { align = 'center', weight = 600, alpha = 1, light = false } = {}) {
  ctx.save(); ctx.globalAlpha *= alpha;
  font(ctx, size, weight, -size * 0.012);
  ctx.textAlign = align; ctx.textBaseline = 'middle';
  const w = ctx.measureText('Gemini').width;
  const x0 = align === 'center' ? x - w / 2 : x;
  if (light) {
    const g = ctx.createLinearGradient(x0, y, x0 + w, y);
    g.addColorStop(0, '#8FB7FF'); g.addColorStop(0.45, '#B79BF0'); g.addColorStop(0.75, '#F39AA6'); g.addColorStop(1, '#FF8A7A');
    ctx.fillStyle = g;
  } else ctx.fillStyle = gemGrad(ctx, x0, y, x0 + w, y);
  ctx.fillText('Gemini', x, y);
  ctx.restore();
  return w;
}
