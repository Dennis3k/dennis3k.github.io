/* ui.js — device mockups, Gemini UI, code-drawn posters */
import { TAU, roundRect, rgba, font, glow, clamp, lerp, inv, smooth, field, eOutCubic } from './core.js';
import { sparkle, iconDrive, iconGmail, iconPhotos, iconGemini, googleG, gemGrad, twinkle } from './brand.js';

/** where the Gemini tile sits inside the screen, in screen-local units */
export function geminiIconPos(w, h) { return { x: w * 0.5 - w * 0.215 * 0.5, y: h * 0.56 }; }

export function iconMaps(ctx, x, y, s) {
  ctx.save(); ctx.translate(x, y);
  ctx.fillStyle = '#34A853';
  ctx.beginPath(); ctx.moveTo(-s * 0.5, s * 0.5); ctx.lineTo(s * 0.5, s * 0.2); ctx.lineTo(s * 0.5, s * 0.5); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#FBBC05';
  ctx.beginPath(); ctx.moveTo(-s * 0.5, -s * 0.1); ctx.lineTo(s * 0.1, -s * 0.5); ctx.lineTo(s * 0.5, s * 0.1); ctx.lineTo(-s * 0.5, s * 0.5); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#EA4335';
  ctx.beginPath(); ctx.arc(0, -s * 0.08, s * 0.24, 0, TAU); ctx.fill();
  ctx.beginPath(); ctx.moveTo(-s * 0.16, s * 0.02); ctx.lineTo(s * 0.16, s * 0.02); ctx.lineTo(0, s * 0.42); ctx.closePath(); ctx.fill();
  ctx.fillStyle = '#4285F4'; ctx.beginPath(); ctx.arc(0, -s * 0.08, s * 0.09, 0, TAU); ctx.fill();
  ctx.restore();
}
export function iconYouTube(ctx, x, y, s) {
  ctx.save(); ctx.fillStyle = '#FF0033';
  roundRect(ctx, x - s * 0.5, y - s * 0.34, s, s * 0.68, s * 0.18); ctx.fill();
  ctx.fillStyle = '#fff'; ctx.beginPath();
  ctx.moveTo(x - s * 0.10, y - s * 0.17); ctx.lineTo(x + s * 0.20, y); ctx.lineTo(x - s * 0.10, y + s * 0.17);
  ctx.closePath(); ctx.fill(); ctx.restore();
}
export function iconCalendar(ctx, x, y, s) {
  ctx.save(); ctx.fillStyle = '#fff';
  roundRect(ctx, x - s * 0.44, y - s * 0.44, s * 0.88, s * 0.88, s * 0.12); ctx.fill();
  ctx.fillStyle = '#4285F4'; roundRect(ctx, x - s * 0.44, y - s * 0.44, s * 0.88, s * 0.26, s * 0.12); ctx.fill();
  ctx.fillRect(x - s * 0.44, y - s * 0.30, s * 0.88, s * 0.12);
  ctx.fillStyle = '#2B2F3A'; font(ctx, s * 0.46, 600);
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('14', x, y + s * 0.12); ctx.restore();
}

export const PHONE_AR = 0.462;      // w / h of the device body
const SCREEN_INSET = 0.028;         // bezel as a fraction of body height

/** device body + clipped screen. draw(ctx, w, h) gets screen-local coords. */
export function phone(ctx, x, y, bodyH, opts, draw) {
  const { rot = 0, neon = 0, shadowA = 0.45, alpha = 1, glass = 1 } = opts || {};
  const bw = bodyH * PHONE_AR, bh = bodyH;
  const r = bw * 0.135;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.translate(x, y); ctx.rotate(rot);
  if (shadowA > 0) {
    ctx.save(); ctx.filter = `blur(${bodyH * 0.055}px)`;
    ctx.fillStyle = `rgba(6,12,32,${shadowA})`;
    roundRect(ctx, -bw / 2, -bh / 2 + bodyH * 0.045, bw, bh, r); ctx.fill(); ctx.restore();
  }
  if (neon > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.filter = `blur(${bodyH * 0.03}px)`;
    ctx.lineWidth = bodyH * 0.012; ctx.globalAlpha = neon;
    ctx.strokeStyle = gemGrad(ctx, -bw / 2, -bh / 2, bw / 2, bh / 2);
    roundRect(ctx, -bw / 2, -bh / 2, bw, bh, r); ctx.stroke(); ctx.restore();
  }
  // body
  const bg = ctx.createLinearGradient(-bw / 2, -bh / 2, bw / 2, bh / 2);
  bg.addColorStop(0, '#2B3140'); bg.addColorStop(0.5, '#171B26'); bg.addColorStop(1, '#2B3140');
  ctx.fillStyle = bg; roundRect(ctx, -bw / 2, -bh / 2, bw, bh, r); ctx.fill();
  // screen
  const ins = bodyH * SCREEN_INSET;
  const sw = bw - ins * 2, sh = bh - ins * 2, sr = r - ins * 0.7;
  ctx.save();
  roundRect(ctx, -sw / 2, -sh / 2, sw, sh, sr); ctx.clip();
  ctx.translate(-sw / 2, -sh / 2);
  ctx.fillStyle = '#0A0D14'; ctx.fillRect(0, 0, sw, sh);
  if (draw) draw(ctx, sw, sh);
  ctx.restore();
  // glass sheen
  if (glass > 0) {
    ctx.save(); roundRect(ctx, -sw / 2, -sh / 2, sw, sh, sr); ctx.clip();
    const sg = ctx.createLinearGradient(-bw / 2, -bh / 2, bw * 0.1, bh * 0.2);
    sg.addColorStop(0, `rgba(255,255,255,${0.14 * glass})`);
    sg.addColorStop(0.45, 'rgba(255,255,255,0)');
    ctx.fillStyle = sg; ctx.fillRect(-bw, -bh, bw * 2, bh * 2); ctx.restore();
  }
  ctx.strokeStyle = 'rgba(255,255,255,0.16)'; ctx.lineWidth = Math.max(1, bodyH * 0.0022);
  roundRect(ctx, -bw / 2, -bh / 2, bw, bh, r); ctx.stroke();
  ctx.restore();
  return { bw, bh, sw: bw - ins * 2, sh: bh - ins * 2 };
}

export function statusBar(ctx, w, h, dark = true) {
  const s = h * 0.016, y = h * 0.032;
  ctx.save();
  ctx.fillStyle = dark ? 'rgba(255,255,255,0.92)' : 'rgba(20,24,34,0.92)';
  font(ctx, s * 1.35, 600); ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText('9:41', w * 0.085, y);
  // signal / battery
  for (let i = 0; i < 4; i++) { const bh2 = s * (0.4 + i * 0.22); ctx.fillRect(w - w * 0.30 + i * s * 0.6, y - bh2 / 2 + s * 0.2, s * 0.38, bh2); }
  roundRect(ctx, w - w * 0.145, y - s * 0.42, s * 2.2, s * 0.9, s * 0.25); ctx.fill();
  ctx.restore();
}

/* ---------------- Android home screen ---------------- */
export function homeScreen(ctx, w, h, t, { geminiBloom = 0, dim = 0 } = {}) {
  const g = ctx.createLinearGradient(0, 0, w, h);
  g.addColorStop(0, '#0E1C44'); g.addColorStop(0.5, '#132A66'); g.addColorStop(1, '#0A1430');
  ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  ctx.save(); ctx.globalCompositeOperation = 'screen';
  glow(ctx, w * 0.25, h * 0.18, w * 0.8, [60, 120, 240], 0.35);
  glow(ctx, w * 0.8, h * 0.78, w * 0.7, [140, 90, 220], 0.28);
  ctx.restore();
  statusBar(ctx, w, h, true);

  // widget clock
  ctx.save();
  ctx.fillStyle = 'rgba(255,255,255,0.95)'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  font(ctx, w * 0.26, 300, -w * 0.004); ctx.fillText('9:41', w * 0.5, h * 0.165);
  font(ctx, w * 0.052, 500); ctx.fillStyle = 'rgba(255,255,255,0.72)';
  ctx.fillText('Tue, Jan 14', w * 0.5, h * 0.235);
  ctx.restore();

  // app grid
  const cols = 4, s = w * 0.155, gapX = w * 0.215, x0 = w * 0.5 - gapX * 1.5;
  const rows = [h * 0.42, h * 0.56];
  const tile = (cx, cy, fn, label) => {
    ctx.save();
    ctx.fillStyle = 'rgba(255,255,255,0.10)';
    roundRect(ctx, cx - s / 2, cy - s / 2, s, s, s * 0.28); ctx.fill();
    fn(cx, cy);
    ctx.fillStyle = 'rgba(255,255,255,0.80)'; font(ctx, w * 0.035, 500);
    ctx.textAlign = 'center'; ctx.textBaseline = 'top';
    ctx.fillText(label, cx, cy + s * 0.62);
    ctx.restore();
  };
  tile(x0 + gapX * 0, rows[0], (x, y) => iconDrive(ctx, x, y, s * 0.6), 'Drive');
  tile(x0 + gapX * 1, rows[0], (x, y) => iconGmail(ctx, x, y, s * 0.6), 'Gmail');
  tile(x0 + gapX * 2, rows[0], (x, y) => iconPhotos(ctx, x, y, s * 0.62), 'Photos');
  tile(x0 + gapX * 3, rows[0], (x, y) => { ctx.save(); ctx.fillStyle = '#fff'; roundRect(ctx, x - s * 0.3, y - s * 0.3, s * 0.6, s * 0.6, s * 0.16); ctx.fill(); googleG(ctx, x, y, s * 0.22); ctx.restore(); }, 'Google');

  // second row + the Gemini icon that blooms before the dive
  tile(x0 + gapX * 0, rows[1], (x, y) => iconMaps(ctx, x, y, s * 0.62), 'Maps');
  tile(x0 + gapX * 2, rows[1], (x, y) => iconYouTube(ctx, x, y, s * 0.62), 'YouTube');
  tile(x0 + gapX * 3, rows[1], (x, y) => iconCalendar(ctx, x, y, s * 0.60), 'Calendar');
  const gx = x0 + gapX * 1, gy = rows[1];
  const b = clamp(geminiBloom);
  ctx.save();
  if (b > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, gx, gy, s * (1.0 + b * 3.2), [150, 185, 255], 0.75 * b);
    ctx.restore();
  }
  const sc = 1 + b * 0.25;
  ctx.translate(gx, gy); ctx.scale(sc, sc); ctx.translate(-gx, -gy);
  ctx.fillStyle = 'rgba(255,255,255,0.10)';
  roundRect(ctx, gx - s / 2, gy - s / 2, s, s, s * 0.28); ctx.fill();
  iconGemini(ctx, gx, gy, s * 0.82);
  ctx.fillStyle = 'rgba(255,255,255,0.86)'; font(ctx, w * 0.035, 500);
  ctx.textAlign = 'center'; ctx.textBaseline = 'top'; ctx.fillText('Gemini', gx, gy + s * 0.62);
  ctx.restore();

  // search pill
  ctx.save();
  ctx.fillStyle = 'rgba(255,255,255,0.14)';
  roundRect(ctx, w * 0.10, h * 0.845, w * 0.80, h * 0.052, h * 0.026); ctx.fill();
  googleG(ctx, w * 0.175, h * 0.871, h * 0.016);
  ctx.fillStyle = 'rgba(255,255,255,0.55)'; font(ctx, w * 0.042, 450);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText('Search', w * 0.24, h * 0.871);
  sparkle(ctx, w * 0.82, h * 0.871, h * 0.014, {});
  ctx.restore();

  if (dim > 0) { ctx.fillStyle = `rgba(255,255,255,${dim})`; ctx.fillRect(0, 0, w, h); }
}

/* ---------------- Gemini app screen ---------------- */
export function geminiApp(ctx, w, h, t, o = {}) {
  const {
    greetWords = 0,          // 0..1 reveal of the greeting, word by word (fractional = partial)
    promptText = '',         // text sitting in the input bar
    caret = false,
    sendGlow = 0,
    magenta = 0.0,
    orb = 0,                 // 0..1 mic -> send orb morph
    chips = 1,
    tapFlash = 0,
    answers = null,          // film list -> answer view
    answerIn = 0,
  } = o;
  // bg
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, '#12131A'); g.addColorStop(1, '#0A0B10');
  ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
  ctx.save(); ctx.globalCompositeOperation = 'screen';
  glow(ctx, w * 0.82, h * 0.80, w * 1.0, [210, 70, 160], 0.30 * (0.35 + magenta));
  glow(ctx, w * 0.15, h * 0.22, w * 0.9, [60, 110, 240], 0.22);
  ctx.restore();
  statusBar(ctx, w, h, true);

  // top bar
  ctx.save();
  sparkle(ctx, w * 0.11, h * 0.082, w * 0.030, {});
  ctx.fillStyle = 'rgba(255,255,255,0.92)'; font(ctx, w * 0.044, 500);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText('Gemini', w * 0.165, h * 0.082);
  ctx.fillStyle = 'rgba(255,255,255,0.28)';
  ctx.beginPath(); ctx.arc(w * 0.88, h * 0.082, w * 0.032, 0, TAU); ctx.fill();
  ctx.restore();

  if (answers) { answerList(ctx, w, h, answers, answerIn, t); }
  else {
    // greeting, word by word
    const words = ['Do', 'you', 'have', 'new', 'ideas', 'to', 'explore?'];
    const size = w * 0.092;
    font(ctx, size, 600, -size * 0.015);
    const lines = [['Do', 'you', 'have', 'new'], ['ideas', 'to', 'explore?']];
    let idx = 0;
    const yTop = h * 0.30;
    ctx.save(); ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
    lines.forEach((ln, li) => {
      const full = ln.join(' ');
      const totalW = ctx.measureText(full).width;
      let x = w * 0.5 - totalW / 2;
      const y = yTop + li * size * 1.22;
      ln.forEach((wd) => {
        const p = clamp((greetWords * words.length - idx));
        if (p > 0) {
          const a = smooth(p), dy = (1 - a) * size * 0.45;
          ctx.save(); ctx.globalAlpha = a;
          const wdw = ctx.measureText(wd).width;
          const grad = ctx.createLinearGradient(w * 0.15, 0, w * 0.85, 0);
          grad.addColorStop(0, '#CFE0FF'); grad.addColorStop(0.5, '#FFFFFF'); grad.addColorStop(1, '#F4D4EA');
          ctx.fillStyle = grad;
          ctx.filter = `blur(${(1 - a) * size * 0.12}px)`;
          ctx.fillText(wd, x, y + dy);
          ctx.restore();
          void wdw;
        }
        x += ctx.measureText(wd + ' ').width;
        idx++;
      });
    });
    ctx.restore();
    // suggestion chips
    if (chips > 0) {
      const labels = ['Plan a trip', 'Explain this photo', 'Write a toast'];
      ctx.save(); ctx.globalAlpha = chips;
      labels.forEach((l, i) => {
        const y = h * 0.50 + i * h * 0.062;
        ctx.fillStyle = 'rgba(255,255,255,0.07)';
        font(ctx, w * 0.040, 450);
        const tw = ctx.measureText(l).width;
        roundRect(ctx, w * 0.5 - (tw + w * 0.14) / 2, y - h * 0.022, tw + w * 0.14, h * 0.044, h * 0.022); ctx.fill();
        ctx.fillStyle = 'rgba(255,255,255,0.70)'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(l, w * 0.5, y);
      });
      ctx.restore();
    }
  }

  inputBar(ctx, w, h, { text: promptText, caret, orb, sendGlow, t });
  if (tapFlash > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, w * 0.845, h * 0.895, w * 0.9 * tapFlash, [255, 255, 255], tapFlash);
    ctx.restore();
  }
}

export function inputBar(ctx, w, h, { text = '', caret = false, orb = 0, sendGlow = 0, t = 0 } = {}) {
  const bx = w * 0.07, bw = w * 0.86, by = h * 0.868, bh = h * 0.055, br = bh / 2;
  ctx.save();
  ctx.fillStyle = 'rgba(255,255,255,0.09)';
  roundRect(ctx, bx, by, bw, bh, br); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.14)'; ctx.lineWidth = Math.max(1, w * 0.002);
  roundRect(ctx, bx, by, bw, bh, br); ctx.stroke();
  // text
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  font(ctx, w * 0.040, 450);
  const cy = by + bh / 2;
  if (text) { ctx.fillStyle = 'rgba(255,255,255,0.92)'; ctx.fillText(text, bx + w * 0.055, cy); }
  else { ctx.fillStyle = 'rgba(255,255,255,0.42)'; ctx.fillText('Ask Gemini', bx + w * 0.055, cy); }
  if (caret) {
    const cx = bx + w * 0.055 + (text ? ctx.measureText(text).width : 0) + w * 0.008;
    ctx.fillStyle = `rgba(160,190,255,${0.55 + 0.45 * Math.sin(t * 12)})`;
    ctx.fillRect(cx, cy - bh * 0.28, Math.max(1.5, w * 0.004), bh * 0.56);
  }
  sparkle(ctx, bx + w * 0.032, cy, w * 0.021, { alpha: 0.9 });
  // right control: mic morphing into send
  const rx = bx + bw - bh * 0.62, ry = cy, rr = bh * 0.36;
  const k = clamp(orb);
  if (sendGlow > 0) { ctx.save(); ctx.globalCompositeOperation = 'screen'; glow(ctx, rx, ry, rr * (4 + sendGlow * 6), [150, 190, 255], 0.6 * sendGlow); ctx.restore(); }
  ctx.save();
  ctx.fillStyle = k > 0.02 ? gemGrad(ctx, rx - rr, ry - rr, rx + rr, ry + rr) : 'rgba(255,255,255,0.0)';
  ctx.globalAlpha = k;
  ctx.beginPath(); ctx.arc(rx, ry, rr * (0.8 + 0.25 * k), 0, TAU); ctx.fill();
  ctx.restore();
  // send arrow appears at the end of the morph
  if (k > 0.55) {
    const a = inv(0.55, 1, k);
    ctx.save(); ctx.globalAlpha = a; ctx.strokeStyle = '#fff'; ctx.lineWidth = Math.max(1.5, rr * 0.16);
    ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    ctx.beginPath(); ctx.moveTo(rx, ry + rr * 0.42); ctx.lineTo(rx, ry - rr * 0.42);
    ctx.moveTo(rx - rr * 0.34, ry - rr * 0.08); ctx.lineTo(rx, ry - rr * 0.44); ctx.lineTo(rx + rr * 0.34, ry - rr * 0.08);
    ctx.stroke(); ctx.restore();
  }
  // mic glyph fades out as the orb takes over
  if (k < 0.95) {
    ctx.save(); ctx.globalAlpha = 1 - k; ctx.fillStyle = 'rgba(255,255,255,0.70)';
    roundRect(ctx, rx - rr * 0.18, ry - rr * 0.52, rr * 0.36, rr * 0.66, rr * 0.18); ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.70)'; ctx.lineWidth = Math.max(1, rr * 0.10);
    ctx.beginPath(); ctx.arc(rx, ry + rr * 0.02, rr * 0.36, 0.15 * Math.PI, 0.85 * Math.PI); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(rx, ry + rr * 0.38); ctx.lineTo(rx, ry + rr * 0.58); ctx.stroke();
    ctx.restore();
  }
  ctx.restore();
}

/* ---------------- answers ---------------- */
export const FILMS = [
  { title: 'Ex Machina', img: 'exmachina', rating: '7.7', year: '2014',
    meta: 'Sci-fi · 1h 48m', dir: 'Alex Garland',
    why: 'A test with no right answer.', seed: 11, pal: ['#0E2A6B', '#2B6CF6', '#9BD1FF'] },
  { title: 'Alita: Battle Angel', img: 'alita', rating: '7.3', year: '2019',
    meta: 'Action · 2h 02m', dir: 'Robert Rodriguez',
    why: 'Weightless, and it knows it.', seed: 23, pal: ['#1B1040', '#7A4FD6', '#F3C7FF'] },
  { title: 'Upgrade', img: 'upgrade', rating: '7.5', year: '2018',
    meta: 'Thriller · 1h 40m', dir: 'Leigh Whannell',
    why: 'Lean, fast, and very mean.', seed: 37, pal: ['#4A1620', '#E0624F', '#FFD9A8'] },
];

/** fully code-drawn poster artwork */
export function poster(ctx, x, y, w, h, film, t = 0) {
  const r = w * 0.07;
  const bm = (typeof window !== 'undefined' && window.__posters) ? window.__posters[film.img] : null;
  if (bm) {
    ctx.save();
    roundRect(ctx, x, y, w, h, r); ctx.clip();
    // вписываем по большей стороне: у обложек разные пропорции (2:3 и 3:4),
    // а рамка в карточке одна, иначе ряд телефонов «поедет»
    const k = Math.max(w / bm.width, h / bm.height);
    const dw = bm.width * k, dh = bm.height * k;
    ctx.drawImage(bm, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh);
    const g = ctx.createLinearGradient(0, y + h * 0.55, 0, y + h);
    g.addColorStop(0, 'rgba(6,8,16,0)'); g.addColorStop(1, 'rgba(6,8,16,0.35)');
    ctx.fillStyle = g; ctx.fillRect(x, y, w, h);
    ctx.restore();
    ctx.save();
    ctx.strokeStyle = 'rgba(255,255,255,0.16)'; ctx.lineWidth = Math.max(1, w * 0.006);
    roundRect(ctx, x, y, w, h, r); ctx.stroke();
    ctx.restore();
    return;
  }
  ctx.save();
  roundRect(ctx, x, y, w, h, r); ctx.clip();
  const [c0, c1, c2] = film.pal;
  const g = ctx.createLinearGradient(x, y, x + w * 0.4, y + h);
  g.addColorStop(0, c0); g.addColorStop(1, '#05070F');
  ctx.fillStyle = g; ctx.fillRect(x, y, w, h);
  const R = field(film.seed, 9, (rr) => ({ a: rr(), b: rr(), c: rr(), d: rr() }));
  ctx.save(); ctx.globalCompositeOperation = 'screen';
  glow(ctx, x + w * (0.3 + R[0].a * 0.4), y + h * 0.62, w * 1.05, hexRgb(c1), 0.85);
  glow(ctx, x + w * 0.5, y + h * 0.30, w * 0.70, hexRgb(c2), 0.22);
  ctx.restore();
  // geometry: sun disc + strata
  ctx.save();
  ctx.globalAlpha = 0.95;
  ctx.fillStyle = c2;
  ctx.beginPath(); ctx.arc(x + w * (0.3 + R[1].a * 0.4), y + h * 0.46, w * 0.17, 0, TAU); ctx.fill();
  ctx.restore();
  ctx.save(); ctx.globalCompositeOperation = 'overlay';
  for (let i = 0; i < 7; i++) {
    const yy = y + h * (0.56 + i * 0.055);
    ctx.fillStyle = rgba(hexRgb(c1), 0.22 + i * 0.05);
    ctx.fillRect(x, yy, w, h * 0.012 + i * h * 0.002);
  }
  ctx.restore();
  // silhouette ridge
  ctx.fillStyle = 'rgba(4,6,14,0.92)';
  ctx.beginPath(); ctx.moveTo(x, y + h);
  for (let i = 0; i <= 8; i++) {
    const px = x + (w * i) / 8;
    const py = y + h * (0.74 + Math.sin(i * 1.7 + film.seed) * 0.06);
    ctx.lineTo(px, py);
  }
  ctx.lineTo(x + w, y + h); ctx.closePath(); ctx.fill();
  // grain
  ctx.save(); ctx.globalAlpha = 0.06; ctx.globalCompositeOperation = 'overlay';
  const GR = field(film.seed + 5, 90, (rr) => ({ x: rr(), y: rr(), s: rr() }));
  ctx.fillStyle = '#fff';
  for (const p of GR) ctx.fillRect(x + p.x * w, y + p.y * h, 1.5 + p.s * 2, 1.5 + p.s * 2);
  ctx.restore();
  // title block
  ctx.save();
  ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic';
  font(ctx, w * 0.105, 700, -w * 0.001);
  ctx.fillStyle = '#fff';
  wrapText(ctx, film.title, x + w * 0.08, y + h * 0.84, w * 0.84, w * 0.115);
  ctx.restore();
  ctx.restore();
  ctx.save();
  ctx.strokeStyle = 'rgba(255,255,255,0.14)'; ctx.lineWidth = Math.max(1, w * 0.006);
  roundRect(ctx, x, y, w, h, r); ctx.stroke();
  ctx.restore();
}
function hexRgb(h) { h = h.replace('#', ''); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; }
export function wrapText(ctx, text, x, y, maxW, lh) {
  const words = text.split(' '); let line = '', yy = y; const out = [];
  for (const w of words) {
    const test = line ? line + ' ' + w : w;
    if (ctx.measureText(test).width > maxW && line) { out.push(line); line = w; } else line = test;
  }
  out.push(line);
  const start = yy - (out.length - 1) * lh;
  out.forEach((l, i) => ctx.fillText(l, x, start + i * lh));
  return out.length;
}

function starMark(ctx, x, y, r, color = '#F5C518') {
  ctx.save(); ctx.fillStyle = color; ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    const rr = i % 2 ? r * 0.44 : r;
    ctx[i ? 'lineTo' : 'moveTo'](x + Math.cos(a) * rr, y + Math.sin(a) * rr);
  }
  ctx.closePath(); ctx.fill(); ctx.restore();
}

/** answer view inside a phone: one film card */
export function answerList(ctx, w, h, films, p, t) {
  const pin = clamp(p);
  ctx.save();
  ctx.globalAlpha = clamp(pin * 2);
  ctx.fillStyle = 'rgba(255,255,255,0.09)';
  font(ctx, w * 0.038, 450);
  const q = 'Recommend me a movie for tonight';
  const qw = Math.min(ctx.measureText(q).width + w * 0.09, w * 0.80);
  roundRect(ctx, w * 0.93 - qw, h * 0.14, qw, h * 0.042, h * 0.021); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.85)'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(q, w * 0.93 - qw / 2, h * 0.161);
  ctx.restore();

  const f = films[0];
  const a = clamp((pin - 0.1) / 0.6);
  ctx.save(); ctx.globalAlpha = a;
  ctx.translate(0, (1 - a) * h * 0.06);

  sparkle(ctx, w * 0.11, h * 0.233, w * 0.026, {});
  ctx.fillStyle = 'rgba(255,255,255,0.72)'; font(ctx, w * 0.036, 450);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText('Here are three for tonight', w * 0.17, h * 0.233);

  // обложка слева, данные справа — так помещается и название, и рейтинг
  const px = w * 0.10, pw = w * 0.38, ph = pw * 1.5;
  const py = h * 0.278;
  poster(ctx, px, py, pw, ph, f, t);

  const cx = px + pw + w * 0.055;
  const cw = w * 0.90 - cx;
  ctx.textAlign = 'left';
  ctx.fillStyle = '#fff';
  const ts = w * 0.050;
  font(ctx, ts, 600, -ts * 0.01);
  ctx.textBaseline = 'alphabetic';
  const lines = wrapText(ctx, f.title, cx, py + ts * 1.9, cw, ts * 1.12);

  let yy = py + ts * 1.9 + ts * 0.95;
  const rs = w * 0.040;
  starMark(ctx, cx + rs * 0.42, yy, rs * 0.52);
  font(ctx, rs, 600);
  ctx.fillStyle = '#fff';
  ctx.textBaseline = 'middle';
  ctx.fillText(f.rating, cx + rs * 1.15, yy);
  const rw = ctx.measureText(f.rating).width;
  font(ctx, rs * 0.72, 450);
  ctx.fillStyle = 'rgba(255,255,255,0.45)';
  ctx.fillText('/10  IMDb', cx + rs * 1.25 + rw, yy + rs * 0.04);

  yy += rs * 1.35;
  font(ctx, w * 0.033, 450);
  ctx.fillStyle = 'rgba(255,255,255,0.62)';
  ctx.fillText(`${f.year} · ${f.meta}`, cx, yy);
  yy += w * 0.048;
  ctx.fillStyle = 'rgba(255,255,255,0.45)';
  ctx.fillText(f.dir, cx, yy);

  ctx.fillStyle = 'rgba(255,255,255,0.70)'; font(ctx, w * 0.036, 450);
  ctx.textBaseline = 'alphabetic';
  wrapText(ctx, f.why, w * 0.10, py + ph + h * 0.052, w * 0.80, h * 0.042);
  void lines;
  ctx.restore();
}

/* ---------------- browser window ---------------- */
export function browserWindow(ctx, x, y, w, h, t, { neon = 0, name = 'Denis', reveal = 1 } = {}) {
  const r = w * 0.022;
  ctx.save();
  ctx.save(); ctx.filter = `blur(${h * 0.05}px)`; ctx.fillStyle = 'rgba(8,14,36,0.45)';
  roundRect(ctx, x - w / 2, y - h / 2 + h * 0.04, w, h, r); ctx.fill(); ctx.restore();
  if (neon > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'screen'; ctx.filter = `blur(${h * 0.028}px)`;
    ctx.globalAlpha = neon; ctx.lineWidth = h * 0.012;
    ctx.strokeStyle = gemGrad(ctx, x - w / 2, y - h / 2, x + w / 2, y + h / 2);
    roundRect(ctx, x - w / 2, y - h / 2, w, h, r); ctx.stroke(); ctx.restore();
  }
  roundRect(ctx, x - w / 2, y - h / 2, w, h, r); ctx.save(); ctx.clip();
  ctx.fillStyle = '#15161C'; ctx.fillRect(x - w / 2, y - h / 2, w, h);
  // chrome
  const barH = h * 0.11;
  ctx.fillStyle = '#23242C'; ctx.fillRect(x - w / 2, y - h / 2, w, barH);
  ['#FF5F57', '#FEBC2E', '#28C840'].forEach((c, i) => {
    ctx.fillStyle = c; ctx.beginPath();
    ctx.arc(x - w / 2 + w * (0.03 + i * 0.022), y - h / 2 + barH / 2, h * 0.014, 0, TAU); ctx.fill();
  });
  ctx.fillStyle = '#34353E';
  roundRect(ctx, x - w / 2 + w * 0.12, y - h / 2 + barH * 0.22, w * 0.52, barH * 0.56, barH * 0.28); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.68)'; font(ctx, h * 0.038, 450);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText('gemini.google.com', x - w / 2 + w * 0.15, y - h / 2 + barH / 2);
  // page
  const pg = ctx.createLinearGradient(x - w / 2, y, x + w / 2, y + h);
  pg.addColorStop(0, '#111219'); pg.addColorStop(1, '#0C0D13');
  ctx.fillStyle = pg; ctx.fillRect(x - w / 2, y - h / 2 + barH, w, h - barH);
  ctx.save(); ctx.globalCompositeOperation = 'screen';
  glow(ctx, x + w * 0.22, y + h * 0.30, w * 0.5, [190, 80, 160], 0.26);
  glow(ctx, x - w * 0.28, y - h * 0.05, w * 0.45, [60, 120, 240], 0.22);
  ctx.restore();
  const rv = clamp(reveal);
  ctx.save(); ctx.globalAlpha = rv;
  sparkle(ctx, x - w * 0.36, y - h * 0.10, h * 0.055, {});
  const size = h * 0.14;
  font(ctx, size, 600, -size * 0.015);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  const txt = `Hello, ${name}`;
  const grad = ctx.createLinearGradient(x - w * 0.28, 0, x + w * 0.2, 0);
  grad.addColorStop(0, '#CFE0FF'); grad.addColorStop(1, '#F6D6EC');
  ctx.fillStyle = grad;
  ctx.fillText(txt, x - w * 0.28, y - h * 0.10);
  ctx.restore();
  // input
  ctx.fillStyle = 'rgba(255,255,255,0.07)';
  roundRect(ctx, x - w * 0.40, y + h * 0.22, w * 0.80, h * 0.13, h * 0.065); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.40)'; font(ctx, h * 0.045, 450);
  ctx.fillText('Ask Gemini', x - w * 0.32, y + h * 0.285);
  ctx.restore();
  ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = Math.max(1, h * 0.004);
  roundRect(ctx, x - w / 2, y - h / 2, w, h, r); ctx.stroke();
  ctx.restore();
}
