/* stages.js — reusable backgrounds */
import { TAU, field, rgba, clamp, lerp, glow, roundRect } from './core.js';

export const NAVY_0 = '#060B1E', NAVY_1 = '#0B1538', NAVY_2 = '#13245C';

const STARS = field(1337, 420, (r) => ({
  x: r(), y: r(), r: 0.6 + r() * 2.6, a: 0.12 + r() * 0.85, ph: r() * TAU, sp: 0.4 + r() * 1.6,
  blue: r() < 0.55,
}));

/** deep navy stage, soft blue stars, radial lift in the centre */
export function navyStage(ctx, L, t, { starA = 1, zoom = 1, drift = 0, lift = 1 } = {}) {
  const { W, H } = L;
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, NAVY_0); g.addColorStop(0.55, '#081029'); g.addColorStop(1, '#05091A');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  if (lift > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, W * 0.5, H * 0.52, Math.max(W, H) * 0.62, [30, 70, 180], 0.30 * lift);
    glow(ctx, W * 0.5, H * 0.52, Math.max(W, H) * 0.28, [60, 110, 230], 0.18 * lift);
    ctx.restore();
  }
  if (starA <= 0) return;
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  const cx = W / 2, cy = H / 2;
  for (const s of STARS) {
    let x = (s.x - 0.5) * W * 1.35, y = (s.y - 0.5) * H * 1.35;
    x *= zoom; y *= zoom;
    x += cx; y += cy + drift * (0.4 + s.r * 0.3) * H;
    if (x < -20 || x > W + 20 || y < -20 || y > H + 20) continue;
    const tw = 0.55 + 0.45 * Math.sin(t * s.sp * 2.2 + s.ph);
    const a = s.a * tw * starA;
    const col = s.blue ? [150, 190, 255] : [255, 255, 255];
    glow(ctx, x, y, s.r * 6 * zoom, col, a * 0.5);
    ctx.fillStyle = rgba(col, a);
    ctx.beginPath(); ctx.arc(x, y, s.r * 0.8 * zoom, 0, TAU); ctx.fill();
  }
  ctx.restore();
}

const BLOBS = field(99, 7, (r) => ({ x: r(), y: r(), r: 0.3 + r() * 0.5, h: r() * 360, sp: 0.2 + r() * 0.5, ph: r() * TAU }));
/** white stage with soft pastel rainbow glows */
export function whiteStage(ctx, L, t, { amount = 1, bg = '#FFFFFF' } = {}) {
  const { W, H } = L;
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  if (amount <= 0) return;
  ctx.save();
  ctx.globalCompositeOperation = 'multiply';
  const pastel = [[206, 223, 255], [255, 219, 238], [226, 220, 255], [255, 230, 236], [214, 232, 255]];
  BLOBS.forEach((b, i) => {
    const x = (b.x * 1.2 - 0.1) * W + Math.sin(t * b.sp + b.ph) * W * 0.05;
    const y = (b.y * 1.2 - 0.1) * H + Math.cos(t * b.sp * 0.8 + b.ph) * H * 0.05;
    const c = pastel[i % pastel.length];
    const g = ctx.createRadialGradient(x, y, 0, x, y, b.r * Math.max(W, H) * 0.7);
    g.addColorStop(0, rgba(c, 0.34 * amount));
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  });
  ctx.restore();
}

/** blue dot grid on deep blue, with perspective fade */
export function dotGrid(ctx, L, t, { amount = 1, scroll = 0, spacing = 64, bg = true, persp = 0.0 } = {}) {
  const { W, H } = L;
  if (bg) {
    const g = ctx.createLinearGradient(0, 0, 0, H);
    g.addColorStop(0, '#0A1B4E'); g.addColorStop(0.5, '#0D2266'); g.addColorStop(1, '#071233');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, W * 0.5, H * 0.5, Math.max(W, H) * 0.55, [40, 100, 220], 0.35);
    ctx.restore();
  }
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  const sp = spacing;
  const oy = ((scroll % sp) + sp) % sp;
  for (let y = -sp; y < H + sp; y += sp) {
    for (let x = -sp; x < W + sp; x += sp) {
      const px = x, py = y + oy;
      const d = Math.hypot(px - W / 2, py - H / 2) / (Math.max(W, H) * 0.7);
      const a = clamp(1 - d) * 0.75 * amount;
      if (a <= 0.01) continue;
      const rr = lerp(1.6, 3.2, clamp(1 - d));
      ctx.fillStyle = rgba([150, 195, 255], a);
      ctx.beginPath(); ctx.arc(px, py, rr, 0, TAU); ctx.fill();
    }
  }
  ctx.restore();
}

/** soft blue bokeh bubbles floating in depth */
const BOKEH = field(7171, 26, (r) => ({ x: r(), y: r(), z: 0.25 + r() * 1.0, sp: 0.15 + r() * 0.5, ph: r() * TAU, a: 0.18 + r() * 0.5 }));
export function bokeh(ctx, L, t, { amount = 1, zoom = 1, hue = [120, 180, 255], light = false } = {}) {
  const { W, H } = L;
  ctx.save();
  if (!light) ctx.globalCompositeOperation = 'screen';
  for (const b of BOKEH) {
    const z = b.z * zoom;
    const x = ((b.x - 0.5) * 1.5 * W) * z + W / 2 + Math.sin(t * b.sp + b.ph) * 18 * z;
    const y = ((b.y - 0.5) * 1.5 * H) * z + H / 2 + Math.cos(t * b.sp * 0.7 + b.ph) * 18 * z;
    const r = (26 + b.z * 120) * z;
    if (light) {
      ctx.save();
      const g2 = ctx.createRadialGradient(x, y, r * 0.1, x, y, r);
      g2.addColorStop(0, rgba(hue, b.a * amount * 0.34));
      g2.addColorStop(0.72, rgba(hue, b.a * amount * 0.20));
      g2.addColorStop(1, rgba(hue, 0));
      ctx.fillStyle = g2; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU); ctx.fill();
      ctx.globalAlpha = b.a * amount * 0.55;
      ctx.strokeStyle = rgba([110, 160, 240], 0.45); ctx.lineWidth = Math.max(1, r * 0.035);
      ctx.beginPath(); ctx.arc(x, y, r * 0.80, 0, TAU); ctx.stroke();
      ctx.restore();
    } else {
      glow(ctx, x, y, r, hue, b.a * amount * 0.5);
      ctx.save(); ctx.globalAlpha = b.a * amount * 0.35;
      ctx.strokeStyle = rgba([200, 225, 255], 0.5); ctx.lineWidth = Math.max(1, r * 0.03);
      ctx.beginPath(); ctx.arc(x, y, r * 0.78, 0, TAU); ctx.stroke(); ctx.restore();
    }
  }
  ctx.restore();
}

export function vignette(ctx, L, a = 0.35) {
  const { W, H } = L;
  const g = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.25, W / 2, H / 2, Math.max(W, H) * 0.78);
  g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, `rgba(0,0,0,${a})`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
}

/** expanding shockwave ring */
export function shockwave(ctx, L, cx, cy, p, { max = 1, color = [170, 205, 255], width = 1 } = {}) {
  if (p <= 0 || p >= 1) return;
  const R = Math.max(L.W, L.H) * max * (1 - Math.pow(1 - p, 2.2));
  const a = Math.pow(1 - p, 2.0);
  ctx.save(); ctx.globalCompositeOperation = 'screen';
  ctx.strokeStyle = rgba(color, a * 0.75);
  ctx.lineWidth = Math.max(1.2, 12 * (1 - p) * width);
  ctx.beginPath(); ctx.arc(cx, cy, R, 0, TAU); ctx.stroke();
  ctx.globalAlpha = a * 0.34;
  ctx.filter = 'blur(30px)';
  ctx.lineWidth = Math.max(2, 46 * (1 - p) * width);
  ctx.beginPath(); ctx.arc(cx, cy, R * 0.98, 0, TAU); ctx.stroke();
  ctx.restore();
}

/** radial star streaks (speed lines) */
export function streaks(ctx, L, cx, cy, p, { n = 48, seed = 21, color = [180, 210, 255], len = 0.55 } = {}) {
  if (p <= 0 || p >= 1) return;
  const S = field(seed, n, (r) => ({ a: r() * TAU, r0: 0.08 + r() * 0.5, l: 0.4 + r() * 0.8, w: 0.6 + r() * 2 }));
  const D = Math.max(L.W, L.H);
  ctx.save(); ctx.globalCompositeOperation = 'screen';
  const k = Math.pow(p, 0.6), fade = Math.pow(1 - p, 1.6);
  for (const s of S) {
    const r0 = D * (s.r0 + k * 0.5);
    const r1 = r0 + D * len * s.l * k;
    ctx.strokeStyle = rgba(color, 0.5 * fade);
    ctx.lineWidth = s.w;
    ctx.beginPath();
    ctx.moveTo(cx + Math.cos(s.a) * r0, cy + Math.sin(s.a) * r0);
    ctx.lineTo(cx + Math.cos(s.a) * r1, cy + Math.sin(s.a) * r1);
    ctx.stroke();
  }
  ctx.restore();
}
