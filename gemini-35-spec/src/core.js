/* core.js — math, easing, deterministic noise, canvas helpers */
export const TAU = Math.PI * 2;
export const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const mix = lerp;
/** normalized progress of v inside [a,b], clamped */
export const inv = (a, b, v) => clamp((v - a) / (b - a || 1e-9));
export const smooth = (t) => { t = clamp(t); return t * t * (3 - 2 * t); };
export const smoother = (t) => { t = clamp(t); return t * t * t * (t * (t * 6 - 15) + 10); };

/* ---- easings (all take 0..1) ---- */
export const eOutExpo = (t) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));
export const eInExpo = (t) => (t <= 0 ? 0 : Math.pow(2, 10 * t - 10));
export const eOutQuint = (t) => 1 - Math.pow(1 - t, 5);
export const eOutQuart = (t) => 1 - Math.pow(1 - t, 4);
export const eOutCubic = (t) => 1 - Math.pow(1 - t, 3);
export const eInCubic = (t) => t * t * t;
export const eInQuart = (t) => t * t * t * t;
export const eInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const eInOutQuint = (t) => (t < 0.5 ? 16 * t ** 5 : 1 - Math.pow(-2 * t + 2, 5) / 2);
export const eOutBack = (t, s = 1.70158) => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2);
export const eInBack = (t, s = 1.70158) => (s + 1) * t * t * t - s * t * t;
/** C1 camera spline: smooth acceleration AND deceleration, no velocity pops */
export const camEase = eInOutQuint;
/** decaying oscillation, 0 at t<=0 */
export const decay = (t, freq = 9, tau = 0.17) => (t <= 0 ? 0 : Math.exp(-t / tau) * Math.sin(TAU * freq * t));

/* ---- deterministic rng ---- */
export function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
/** stable array of n objects built from a seeded rng */
export function field(seed, n, make) {
  const r = mulberry32(seed); const out = [];
  for (let i = 0; i < n; i++) out.push(make(r, i));
  return out;
}

/* ---- color ---- */
export const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
export function hex2rgb(h) {
  h = h.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
export function mixRgb(a, b, t) { return [lerp(a[0], b[0], t) | 0, lerp(a[1], b[1], t) | 0, lerp(a[2], b[2], t) | 0]; }

/* ---- canvas helpers ---- */
export function roundRect(ctx, x, y, w, h, r) {
  r = Math.min(r, Math.abs(w) / 2, Math.abs(h) / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
/** font string; family is the Google Sans Flex stand-in */
export const FAM = '"Inter Display","Inter",sans-serif';
export function font(ctx, size, weight = 500, tracking = 0) {
  ctx.font = `${weight} ${size}px ${FAM}`;
  ctx.letterSpacing = `${tracking}px`;
}
/** largest size (<=cap) at which text fits maxW */
export function fitSize(ctx, text, maxW, weight, cap = 4000, tracking = 0) {
  let lo = 4, hi = cap;
  for (let i = 0; i < 26; i++) {
    const m = (lo + hi) / 2;
    font(ctx, m, weight, tracking * m);
    if (ctx.measureText(text).width <= maxW) lo = m; else hi = m;
  }
  font(ctx, lo, weight, tracking * lo);
  return lo;
}
/** radial glow blob */
export function glow(ctx, x, y, r, color, a = 1, inner = 0) {
  const g = ctx.createRadialGradient(x, y, r * inner, x, y, r);
  g.addColorStop(0, rgba(color, a));
  g.addColorStop(0.45, rgba(color, a * 0.32));
  g.addColorStop(1, rgba(color, 0));
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
}
/** draw with a temporary blur filter */
export function blurred(ctx, px, fn) {
  ctx.save(); ctx.filter = `blur(${px}px)`; fn(); ctx.restore();
}
export function shadow(ctx, color, blur, ox = 0, oy = 0) {
  ctx.shadowColor = color; ctx.shadowBlur = blur; ctx.shadowOffsetX = ox; ctx.shadowOffsetY = oy;
}
export function noShadow(ctx) { ctx.shadowColor = 'transparent'; ctx.shadowBlur = 0; ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0; }
