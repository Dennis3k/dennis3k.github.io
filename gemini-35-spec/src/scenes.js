/* scenes.js — one function per beat-sheet scene. t is scene-local seconds. */
import {
  TAU, clamp, lerp, inv, smooth, smoother, decay, field, rgba, roundRect, font,
  fitSize, glow, eOutExpo, eInExpo, eOutQuint, eOutQuart, eOutCubic, eInCubic,
  eInQuart, eInOutCubic, eInOutQuint, eOutBack, camEase, noShadow,
} from './core.js';
import { navyStage, whiteStage, dotGrid, bokeh, vignette, shockwave, streaks } from './stages.js';
import {
  sparkle, sparklePath, gemGrad, blueGrad, googleG, iconGemini, wordGemini, twinkle,
  G_BLUE, G_RED, G_YEL, G_GRN,
} from './brand.js';
import { phone, homeScreen, geminiApp, inputBar, poster, FILMS, browserWindow, wrapText, answerList, geminiIconPos } from './ui.js';
import { VO } from './timing.js';

/* ───────────────────────── shared pieces ───────────────────────── */

/** camera: scale+translate about a point, C1 by construction */
function cam(ctx, cx, cy, s, dx = 0, dy = 0) {
  ctx.translate(cx + dx, cy + dy); ctx.scale(s, s); ctx.translate(-cx, -cy);
}
/** overscan so frame shake never exposes an edge */
function overscan(ctx, L, k = 1.06) { cam(ctx, L.W / 2, L.H / 2, k); }

function heavyWord(ctx, L, text, size, x, y, { fill = '#fff', alpha = 1, blurPx = 0, scale = 1, rot = 0 } = {}) {
  ctx.save();
  ctx.globalAlpha *= alpha;
  if (blurPx > 0.3) ctx.filter = `blur(${blurPx}px)`;
  ctx.translate(x, y); ctx.rotate(rot); ctx.scale(scale, scale);
  font(ctx, size, 900, -size * 0.022);
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = fill;
  ctx.fillText(text, 0, 0);
  ctx.restore();
}

/* ───────────────────────── S1 · 0.0–2.5 · word SLAM ───────────────────────── */
export function S1(ctx, L, t) {
  const { W, H, u } = L;
  const words = VO.l1;
  const RUSH = 0.14;

  // frame shake, decaying, from every impact so far
  let shx = 0, shy = 0;
  words.forEach((w, i) => {
    const d = t - w.t;
    if (d < 0) return;
    const amp = (i === 3 ? 30 : 18) * u;
    shx += decay(d, 12.5, 0.115) * amp;
    shy += decay(d + 0.012, 10.5, 0.115) * amp * 0.62;
  });

  ctx.save();
  overscan(ctx, L, 1.07);
  ctx.translate(shx, shy);
  navyStage(ctx, L, t, { zoom: 1 + t * 0.018, drift: -t * 0.0035 });
  vignette(ctx, L, 0.42);

  // depth streaks + shockwaves keyed to each impact
  words.forEach((w, i) => {
    const d = t - w.t;
    streaks(ctx, L, W / 2, H / 2, inv(-RUSH, 0.20, t - w.t), { seed: 21 + i * 7, n: 54, len: 0.5 });
    if (d >= 0) {
      shockwave(ctx, L, W / 2, H / 2, inv(0, i === 3 ? 0.95 : 0.65, d), { max: i === 3 ? 1.15 : 0.8, width: i === 3 ? 1.5 : 1 });
      // sub-boom bloom
      const b = Math.pow(clamp(1 - d / 0.3), 2);
      if (b > 0.01) { ctx.save(); ctx.globalCompositeOperation = 'screen'; glow(ctx, W / 2, H / 2, Math.max(W, H) * 0.6, [70, 120, 230], 0.5 * b); ctx.restore(); }
    }
  });

  ctx.restore();

  // type rides the shake but never the overscan, so nothing clips
  ctx.save();
  ctx.translate(shx * 0.7, shy * 0.7);
  const maxW = [0.78, 0.84, 0.70, 0.90];
  const capH = L.vert ? H * 0.132 : H * 0.42;

  if (!L.vert) {
    // 16:9 — each word owns the frame, punched through by the next
    words.forEach((w, i) => {
      const p = inv(w.t - RUSH, w.t, t);
      if (p <= 0) return;
      const nxt = words[i + 1];
      const out = nxt ? inv(nxt.t - RUSH, nxt.t - RUSH + 0.10, t) : (i === 3 ? 0 : 0);
      if (out >= 1) return;
      const size = Math.min(fitSize(ctx, w.w, W * maxW[i], 900, 900, -0.022), capH);
      const d = t - w.t;
      let sc = lerp(0.24, 1, eInQuart(p));
      if (d >= 0) sc = 1 + 0.05 * decay(d, 9, 0.085);
      sc *= 1 + out * 0.55;
      const a = Math.pow(p, 0.55) * (1 - out);
      const bl = (1 - p) * 26 * u + out * 20 * u;
      heavyWord(ctx, L, w.w, size, W / 2, H / 2, { alpha: a, blurPx: bl, scale: sc });
    });
  } else {
    // 9:16 — fixed rows, each word slams into its own row (never re-centres)
    const rowY = [0.30, 0.42, 0.54, 0.675].map((k) => H * k);
    words.forEach((w, i) => {
      const p = inv(w.t - RUSH, w.t, t);
      if (p <= 0) return;
      const size = Math.min(fitSize(ctx, w.w, W * maxW[i] * 1.02, 900, 900, -0.022), capH * (i === 3 ? 1.22 : 1));
      const d = t - w.t;
      let sc = lerp(0.24, 1, eInQuart(p));
      if (d >= 0) sc = 1 + 0.05 * decay(d, 9, 0.085);
      const settled = clamp(inv(0, 0.22, d));
      const a = Math.pow(p, 0.55) * lerp(1, i === 3 ? 1 : 0.62, settled * clamp(inv(w.t, words[3].t, t)));
      const bl = (1 - p) * 26 * u;
      heavyWord(ctx, L, w.w, size, W / 2, rowY[i], { alpha: a, blurPx: bl, scale: sc });
    });
  }
  ctx.restore();
}

/* ───────── S2 · 2.5–3.5 · dark collapses into a sparkle window on white ───────── */
export function S2(ctx, L, t) {
  const { W, H, u } = L;
  const diag = Math.hypot(W, H);
  const pc = inv(0.0, 0.44, t);                       // collapse
  const rTarget = L.vert ? W * 0.085 : H * 0.115;
  const r = lerp(diag * 0.82, rTarget, eInOutQuint(pc));
  const pinch = lerp(0.0, 0.085, smooth(inv(0.05, 0.5, t)));
  const rot = lerp(-0.35, 0, eInOutCubic(pc));

  // final sparkle seat + the word
  const wordSize = L.vert ? W * 0.20 : H * 0.20;
  ctx.save(); font(ctx, wordSize, 600, -wordSize * 0.012);
  const wW = ctx.measureText('Gemini').width; ctx.restore();
  const gap = rTarget * 1.5;
  const seatX = L.vert ? W / 2 : W / 2 - wW / 2 - gap;
  const seatY = L.vert ? H * 0.40 : H / 2;
  const wordX = L.vert ? W / 2 : seatX + gap + wW / 2;
  const wordY = L.vert ? H * 0.545 : H / 2;

  // the window travels from frame centre to its seat
  const pm = smoother(inv(0.30, 0.72, t));
  const cx = lerp(W / 2, seatX, pm), cy = lerp(H / 2, seatY, pm);

  // white stage underneath
  whiteStage(ctx, L, t, { amount: 1 });
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  glow(ctx, seatX, seatY, Math.max(W, H) * 0.35, [120, 170, 255], 0.22 * pm);
  ctx.restore();

  // the word resolving out of blur
  const pw = inv(0.40, 0.86, t);
  if (pw > 0) {
    ctx.save();
    ctx.globalAlpha = Math.pow(pw, 0.7);
    ctx.filter = `blur(${(1 - eOutQuart(pw)) * 36 * u}px)`;
    const sc = lerp(1.07, 1, eOutQuart(pw));
    ctx.translate(wordX, wordY); ctx.scale(sc, sc); ctx.translate(-wordX, -wordY);
    wordGemini(ctx, wordX, wordY, wordSize, { weight: 600 });
    ctx.restore();
  }

  // the dark frame, clipped to the sparkle
  ctx.save();
  sparklePath(ctx, cx, cy, r, rot, pinch);
  ctx.clip();
  navyStage(ctx, L, t + 2.5, { zoom: 1.045, drift: -0.009 });
  ctx.restore();

  // recolour the window into the brand sparkle as it lands
  const pg = inv(0.42, 0.68, t);
  if (pg > 0) {
    ctx.save(); ctx.globalAlpha = smooth(pg);
    sparkle(ctx, cx, cy, r, { rot, glowPx: 12 * u });
    ctx.globalAlpha *= 0.55; sparkle(ctx, cx, cy, r, { rot });
    ctx.restore();
  }
  // landing twinkle
  const pt = inv(0.60, 0.80, t);
  if (pt > 0 && pt < 1) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, cx, cy, r * (1.6 + pt * 5), [210, 225, 255], (1 - pt) * 0.30);
    twinkle(ctx, cx, cy, r * (0.30 + pt * 0.9), (1 - pt) * 0.40);
    ctx.restore();
  }
}

/* ───────────────── S3 · 3.5–5.5 · drop 1, glossy 3D "3.5" ───────────────── */
function glossy35(ctx, x, y, size, { yaw = 0, pitch = 0, depth = 1, alpha = 1 } = {}) {
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.translate(x, y);
  const sx = Math.cos(yaw), sh = Math.sin(pitch) * 0.30;
  ctx.transform(Math.max(0.12, sx), sh * 0.6, -Math.sin(yaw) * 0.18, Math.cos(pitch), 0, 0);
  font(ctx, size, 800, -size * 0.030);
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const txt = '3.5';
  // extrusion
  const steps = Math.round(26 * depth);
  const dx = Math.sin(yaw) * size * 0.052 + size * 0.012;
  const dy = size * 0.040;
  for (let i = steps; i >= 1; i--) {
    const k = i / steps;
    ctx.fillStyle = `rgb(${lerp(10, 36, 1 - k) | 0},${lerp(28, 86, 1 - k) | 0},${lerp(86, 190, 1 - k) | 0})`;
    ctx.fillText(txt, dx * k, dy * k);
  }
  // front face
  const g = ctx.createLinearGradient(0, -size * 0.58, 0, size * 0.58);
  g.addColorStop(0, '#DDEBFF'); g.addColorStop(0.22, '#8FC0FF');
  g.addColorStop(0.44, '#2F6FEB'); g.addColorStop(0.52, '#7FB2FF');
  g.addColorStop(0.72, '#1E4FD0'); g.addColorStop(1, '#0B2A86');
  ctx.fillStyle = g;
  ctx.fillText(txt, 0, 0);
  // specular rim
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  ctx.globalAlpha *= 0.85;
  ctx.filter = `blur(${size * 0.012}px)`;
  const g2 = ctx.createLinearGradient(0, -size * 0.55, 0, -size * 0.12);
  g2.addColorStop(0, 'rgba(255,255,255,0.95)'); g2.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g2; ctx.fillText(txt, 0, -size * 0.012);
  ctx.restore();
  ctx.restore();
}

export function S3(ctx, L, t) {
  const { W, H, u } = L;
  const impact = VO.three - 3.5;                   // ≈0.12
  const pIn = inv(impact - 0.18, impact, t);
  const d = t - impact;
  const pOut = inv(1.35, 1.92, t);

  // stage: white → pale blue, blue bokeh in depth
  const bgT = clamp(inv(0, 0.5, t));
  ctx.save();
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#FFFFFF'); g.addColorStop(1, `rgb(${lerp(255, 222, bgT) | 0},${lerp(255, 236, bgT) | 0},255)`);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.restore();
  whiteStage(ctx, L, t + 3.5, { amount: 0.55, bg: 'rgba(0,0,0,0)' });

  const push = lerp(1, 1.12, smooth(inv(0.2, 1.3, t))) * lerp(1, 7.5, eInCubic(pOut));
  ctx.save();
  cam(ctx, W / 2, H * 0.5, push);

  bokeh(ctx, L, t, { light: true, amount: 1.0 * (1 - pOut * 0.6), zoom: 1 + 0.25 * smooth(inv(0, 1.4, t)), hue: [70, 130, 235] });

  // impact shock + ripple on the bokeh
  shockwave(ctx, L, W / 2, H * 0.5, inv(0, 0.8, d), { max: 0.9, color: [90, 150, 255], width: 1.2 });

  if (pIn > 0) {
    const size = Math.min(W * (L.vert ? 0.80 : 0.62), H * 0.66);
    let sc = lerp(2.9, 1, eInQuart(pIn));
    let rot = lerp(-0.30, 0, eOutQuart(pIn));
    let yoff = lerp(-H * 0.16, 0, eInQuart(pIn));
    if (d >= 0) {
      sc = 1 + 0.07 * decay(d, 8.5, 0.10);
      rot = 0.035 * decay(d, 7, 0.16);
      yoff = 0;
    }
    // 3D drift after the crash
    const dr = clamp(inv(0.15, 1.35, t));
    const yaw = Math.sin(dr * 2.1) * 0.30 * smooth(dr) + (1 - pIn) * -0.5;
    const pitch = Math.cos(dr * 1.6) * 0.16 * smooth(dr);
    const dxx = Math.sin(dr * 1.3) * W * 0.035 * smooth(dr);
    const dyy = Math.cos(dr * 1.9) * H * 0.030 * smooth(dr);
    ctx.save();
    ctx.globalAlpha = clamp(pIn * 1.4) * (1 - clamp(inv(0.80, 1.0, pOut)));
    if (pIn < 1) ctx.filter = `blur(${(1 - pIn) * 30 * u}px)`;
    ctx.translate(W / 2 + dxx, H * 0.5 + yoff + dyy);
    ctx.rotate(rot); ctx.scale(sc, sc);
    // contact shadow
    ctx.save(); ctx.globalAlpha *= 0.28; ctx.filter = `blur(${size * 0.09}px)`;
    ctx.fillStyle = '#2A4FA8';
    ctx.beginPath(); ctx.ellipse(0, size * 0.52, size * 0.62, size * 0.10, 0, 0, TAU); ctx.fill(); ctx.restore();
    glossy35(ctx, 0, 0, size, { yaw, pitch });
    ctx.restore();
  }
  ctx.restore();

  // blow out to white on the fly-past
  if (pOut > 0) {
    ctx.save(); ctx.globalAlpha = Math.pow(pOut, 1.6); ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, W, H); ctx.restore();
  }
}

/* ───────────────── S4 · 5.5–7.5 · phone rises, dive into the icon ───────────────── */
export function S4(ctx, L, t) {
  const { W, H, u } = L;
  const rise = eOutQuint(inv(0.02, 0.62, t));
  const bloom = clamp(inv(0.95, 1.30, t));
  const dive = inv(1.28, 1.98, t);

  whiteStage(ctx, L, t + 5.5, { amount: 0.9 });

  const bodyH = L.vert ? H * 0.72 : H * 0.88;
  const px = W / 2, py = H * (L.vert ? 0.52 : 0.55);
  // the dive target comes from the same geometry the screen draws with
  const ins = bodyH * 0.028, sw = bodyH * 0.462 - ins * 2, sh = bodyH - ins * 2;
  const ip = geminiIconPos(sw, sh);
  const iconX = px - sw / 2 + ip.x, iconY = py - sh / 2 + ip.y;

  const zoom = lerp(1, 22, eInCubic(dive));
  ctx.save();
  cam(ctx, iconX, iconY, zoom);
  const float = Math.sin(t * 1.6) * 6 * u * (1 - dive);
  const yNow = lerp(H + bodyH * 0.65, py, rise) + float;
  const rot = lerp(0.06, 0, eOutQuint(inv(0.02, 0.72, t))) + Math.sin(t * 1.1) * 0.004;
  phone(ctx, px, yNow, bodyH, { rot, shadowA: 0.28 * rise, alpha: 1 }, (c, w, h) => {
    homeScreen(c, w, h, t, { geminiBloom: bloom });
  });
  ctx.restore();

  // the bloom takes over the frame as the camera lands in the icon
  if (dive > 0.34) {
    const k = inv(0.34, 1, dive);
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, iconX, iconY, Math.max(W, H) * (0.3 + k * 1.2), [170, 200, 255], Math.pow(k, 1.4));
    ctx.restore();
    ctx.save(); ctx.globalAlpha = Math.pow(inv(0.80, 1, dive), 1.5); ctx.fillStyle = '#E9F0FF';
    ctx.fillRect(0, 0, W, H); ctx.restore();
  }
}

/* ───────────────── full-frame Gemini app (laid out per format) ───────────────── */
export function appGeom(L) {
  const { W, H, vert } = L;
  const barW = vert ? W * 0.86 : Math.min(W * 0.58, 1200);
  const barH = vert ? H * 0.055 : H * 0.098;
  const barX = W / 2 - barW / 2;
  const barY = vert ? H * 0.836 : H * 0.775;
  const send = { x: barX + barW - barH * 0.62, y: barY + barH / 2, r: barH * 0.33 };
  return { barX, barY, barW, barH, send, textX: barX + barH * 1.02, textY: barY + barH / 2, textSize: barH * 0.38 };
}

export function appStage(ctx, L, t, o = {}) {
  const { W, H, u, vert } = L;
  const { greetWords = 1, promptText = '', caret = false, orb = 0, sendGlow = 0, magenta = 1, chips = 1, dimUI = 0, bgOnly = false } = o;
  const g = ctx.createLinearGradient(0, 0, W * 0.3, H);
  g.addColorStop(0, '#13141C'); g.addColorStop(1, '#090A10');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.save(); ctx.globalCompositeOperation = 'screen';
  glow(ctx, W * (vert ? 0.82 : 0.78), H * 0.84, Math.max(W, H) * 0.70, [214, 60, 158], 0.30 * magenta);
  glow(ctx, W * 0.16, H * 0.18, Math.max(W, H) * 0.60, [50, 110, 245], 0.22);
  glow(ctx, W * 0.5, H * 0.5, Math.max(W, H) * 0.42, [60, 80, 180], 0.10);
  ctx.restore();
  if (bgOnly) return;

  const G = appGeom(L);
  ctx.save();
  ctx.globalAlpha = 1 - dimUI;
  // top bar
  const tbY = vert ? H * 0.072 : H * 0.085;
  const tbX = vert ? W * 0.10 : W * 0.065;
  sparkle(ctx, tbX, tbY, u * 20, {});
  ctx.fillStyle = 'rgba(255,255,255,0.90)'; font(ctx, u * 34, 500);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.fillText('Gemini', tbX + u * 36, tbY);
  ctx.restore();

  // greeting
  const lines = vert ? [['Do', 'you', 'have'], ['new', 'ideas'], ['to', 'explore?']] : [['Do', 'you', 'have', 'new'], ['ideas', 'to', 'explore?']];
  const size = vert ? W * 0.115 : H * 0.125;
  const lh = size * 1.18;
  const topY = (vert ? H * 0.40 : H * 0.40) - ((lines.length - 1) * lh) / 2;
  ctx.save();
  ctx.globalAlpha = 1 - dimUI;
  font(ctx, size, 600, -size * 0.018);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  let idx = 0;
  const total = VO.l3.length;
  lines.forEach((ln, li) => {
    const full = ln.join(' ');
    let x = W / 2 - ctx.measureText(full).width / 2;
    const y = topY + li * lh;
    ln.forEach((wd) => {
      const p = clamp(greetWords * total - idx);
      if (p > 0) {
        const a = smooth(p);
        ctx.save();
        ctx.globalAlpha *= a;
        ctx.filter = `blur(${(1 - a) * size * 0.11}px)`;
        const grad = ctx.createLinearGradient(W * 0.2, 0, W * 0.8, 0);
        grad.addColorStop(0, '#CFE0FF'); grad.addColorStop(0.5, '#FFFFFF'); grad.addColorStop(1, '#F6D2E8');
        ctx.fillStyle = grad;
        ctx.fillText(wd, x, y + (1 - a) * size * 0.40);
        ctx.restore();
      }
      x += ctx.measureText(wd + ' ').width;
      idx++;
    });
  });
  ctx.restore();

  // chips
  if (chips > 0.01) {
    const labels = ['Plan a trip', 'Explain this photo', 'Write a toast'];
    ctx.save(); ctx.globalAlpha = chips * (1 - dimUI);
    font(ctx, u * 30, 450);
    if (vert) {
      labels.forEach((l, i) => {
        const y = H * 0.615 + i * u * 72;
        const tw = ctx.measureText(l).width;
        ctx.fillStyle = 'rgba(255,255,255,0.07)';
        roundRect(ctx, W / 2 - (tw + u * 90) / 2, y - u * 28, tw + u * 90, u * 56, u * 28); ctx.fill();
        ctx.fillStyle = 'rgba(255,255,255,0.68)'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(l, W / 2, y);
      });
    } else {
      const ws = labels.map((l) => ctx.measureText(l).width + u * 90);
      const totalW = ws.reduce((a, b) => a + b, 0) + u * 24 * (labels.length - 1);
      let x = W / 2 - totalW / 2;
      labels.forEach((l, i) => {
        ctx.fillStyle = 'rgba(255,255,255,0.07)';
        roundRect(ctx, x, H * 0.615 - u * 29, ws[i], u * 58, u * 29); ctx.fill();
        ctx.fillStyle = 'rgba(255,255,255,0.68)'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(l, x + ws[i] / 2, H * 0.615);
        x += ws[i] + u * 24;
      });
    }
    ctx.restore();
  }

  // input bar
  ctx.save();
  ctx.fillStyle = 'rgba(255,255,255,0.085)';
  roundRect(ctx, G.barX, G.barY, G.barW, G.barH, G.barH / 2); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = Math.max(1, u * 2);
  roundRect(ctx, G.barX, G.barY, G.barW, G.barH, G.barH / 2); ctx.stroke();
  sparkle(ctx, G.barX + G.barH * 0.55, G.textY, G.barH * 0.22, { alpha: 0.92 });
  font(ctx, G.textSize, 450);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  if (promptText) { ctx.fillStyle = 'rgba(255,255,255,0.94)'; ctx.fillText(promptText, G.textX, G.textY); }
  else { ctx.fillStyle = 'rgba(255,255,255,0.40)'; ctx.fillText('Ask Gemini', G.textX, G.textY); }
  if (caret) {
    const cx = G.textX + (promptText ? ctx.measureText(promptText).width : 0) + u * 8;
    ctx.fillStyle = `rgba(170,200,255,${0.5 + 0.5 * Math.sin(t * 13)})`;
    ctx.fillRect(cx, G.textY - G.barH * 0.26, Math.max(2, u * 4), G.barH * 0.52);
  }
  ctx.restore();

  // mic → orb → send
  const k = clamp(orb), S = G.send;
  if (sendGlow > 0) { ctx.save(); ctx.globalCompositeOperation = 'screen'; glow(ctx, S.x, S.y, S.r * (4 + sendGlow * 9), [160, 195, 255], 0.65 * sendGlow); ctx.restore(); }
  if (k < 0.96) {
    ctx.save(); ctx.globalAlpha = 1 - k;
    ctx.fillStyle = 'rgba(255,255,255,0.72)';
    roundRect(ctx, S.x - S.r * 0.18, S.y - S.r * 0.55, S.r * 0.36, S.r * 0.70, S.r * 0.18); ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.72)'; ctx.lineWidth = Math.max(1.5, S.r * 0.10);
    ctx.beginPath(); ctx.arc(S.x, S.y + S.r * 0.02, S.r * 0.38, 0.15 * Math.PI, 0.85 * Math.PI); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(S.x, S.y + S.r * 0.40); ctx.lineTo(S.x, S.y + S.r * 0.62); ctx.stroke();
    ctx.restore();
  }
  if (k > 0.01) {
    ctx.save(); ctx.globalAlpha = k;
    ctx.fillStyle = gemGrad(ctx, S.x - S.r, S.y - S.r, S.x + S.r, S.y + S.r);
    ctx.beginPath(); ctx.arc(S.x, S.y, S.r * (0.75 + 0.35 * k), 0, TAU); ctx.fill();
    if (k > 0.55) {
      const a = inv(0.55, 1, k);
      ctx.globalAlpha = a; ctx.strokeStyle = '#fff'; ctx.lineWidth = Math.max(2, S.r * 0.15);
      ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.beginPath(); ctx.moveTo(S.x, S.y + S.r * 0.44); ctx.lineTo(S.x, S.y - S.r * 0.44);
      ctx.moveTo(S.x - S.r * 0.34, S.y - S.r * 0.08); ctx.lineTo(S.x, S.y - S.r * 0.46); ctx.lineTo(S.x + S.r * 0.34, S.y - S.r * 0.08);
      ctx.stroke();
    }
    ctx.restore();
  }
}

/* ───────────────── S5 · 7.5–9.5 · the app, greeting word by word ───────────────── */
export function S5(ctx, L, t) {
  const { W, H } = L;
  const abs = t + 7.5;
  let done = 0;
  VO.l3.forEach((w) => { done += clamp(inv(w.t - 0.02, w.t + 0.16, abs)); });
  const greet = done / VO.l3.length;
  // the dive lands: a flash settles over the first 6 frames
  const land = inv(0, 0.22, t);
  ctx.save();
  cam(ctx, W / 2, H * 0.42, lerp(1.10, 1.0, eOutQuint(land)) * lerp(1, 1.025, inv(0.2, 2.0, t)));
  appStage(ctx, L, abs, { greetWords: greet, chips: smooth(inv(1.35, 1.75, t)), magenta: 0.7 + 0.3 * Math.sin(t * 0.9) });
  ctx.restore();
  if (land < 1) { ctx.save(); ctx.globalAlpha = Math.pow(1 - land, 1.5); ctx.fillStyle = '#E9F0FF'; ctx.fillRect(0, 0, W, H); ctx.restore(); }
}

/* ───────────────── S6 · 9.5–11.0 · huge kinetic typing ───────────────── */
export const PROMPT = 'Recommend me a movie for tonight';
function typedCount(abs) {
  const p = clamp(inv(VO.typeStart, VO.typeEnd, abs));
  // type in word bursts so letters land with the syllables, never a metronome
  return Math.round(Math.pow(p, 0.94) * PROMPT.length);
}
/** layout of the huge prompt; returns lines + geometry */
function bigPromptLayout(ctx, L) {
  const { W, H, vert } = L;
  const lines = vert
    ? ['Recommend', 'me a movie', 'for tonight']
    : ['Recommend me', 'a movie for tonight'];
  const cap = vert ? H * 0.115 : H * 0.195;
  let size = cap;
  for (const ln of lines) size = Math.min(size, fitSize(ctx, ln, W * 0.86, 700, cap, -0.022));
  font(ctx, size, 700, -size * 0.022);
  const lh = size * 1.12;
  return { lines, size, lh, topY: H * 0.5 - ((lines.length - 1) * lh) / 2 };
}
export function S6(ctx, L, t, o = {}) {
  const { W, H, u } = L;
  const abs = t + 9.5;
  const n = o.count !== undefined ? o.count : typedCount(abs);
  appStage(ctx, L, abs, { bgOnly: true });
  // the chrome stays, dimmed; the greeting has already cleared
  ctx.save(); ctx.globalAlpha = 0.55;
  appStage(ctx, L, abs, { greetWords: 0, chips: 0, dimUI: 0.45 });
  ctx.restore();

  ctx.save();
  const { lines, size, lh, topY } = bigPromptLayout(ctx, L);
  // caret position drives the camera
  let seen = 0; let caretX = W / 2, caretY = topY, lineIdx = 0;
  const lineMeta = lines.map((ln) => {
    const w = ctx.measureText(ln).width;
    return { ln, w, x: W / 2 - w / 2 };
  });
  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];
    const start = seen; seen += ln.length + (i < lines.length - 1 ? 1 : 0);
    if (n <= seen) {
      const k = clamp(n - start, 0, ln.length);
      const sub = ln.slice(0, k);
      caretX = lineMeta[i].x + ctx.measureText(sub).width;
      caretY = topY + i * lh; lineIdx = i;
      break;
    }
    caretX = lineMeta[i].x + lineMeta[i].w; caretY = topY + i * lh; lineIdx = i;
  }
  // the camera follows the typing continuously — a per-character jump would
  // smear the whole block under a 0.85 shutter
  const pc = clamp(inv(VO.typeStart, VO.typeEnd, abs));
  const camX = o.camX !== undefined ? o.camX : W / 2 + W * 0.055 * Math.cos(pc * Math.PI);
  const camY = o.camY !== undefined ? o.camY : H / 2 + H * 0.030 * (pc - 0.5) * 2;
  ctx.restore();

  ctx.save();
  const z = o.zoom !== undefined ? o.zoom : lerp(1.10, 1.0, smooth(inv(0, 1.4, t)));
  cam(ctx, W / 2, H / 2, z, (W / 2 - camX) * 0.55, (H / 2 - camY) * 0.55);
  ctx.save();
  if (o.alpha !== undefined) ctx.globalAlpha = o.alpha;
  font(ctx, size, 700, -size * 0.022);
  ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  let used = 0;
  lines.forEach((ln, i) => {
    const x0 = lineMeta[i].x, y = topY + i * lh;
    let x = x0;
    for (let c = 0; c < ln.length; c++) {
      const gi = used + c;
      if (gi >= n) break;
      const ch = ln[c];
      const pop = clamp(1 - (n - gi) / 2.2);
      const grad = ctx.createLinearGradient(x0, 0, x0 + lineMeta[i].w, 0);
      grad.addColorStop(0, '#FFFFFF'); grad.addColorStop(1, '#D9E6FF');
      ctx.save();
      ctx.fillStyle = grad;
      const s = 1 + pop * 0.16;
      const cw = ctx.measureText(ch).width;
      ctx.translate(x + cw / 2, y); ctx.scale(s, s);
      ctx.fillText(ch, -cw / 2, 0);
      ctx.restore();
      x += cw;
    }
    used += ln.length + (i < lines.length - 1 ? 1 : 0);
  });
  // caret
  if (o.caret !== false) {
    ctx.fillStyle = `rgba(150,190,255,${0.55 + 0.45 * Math.sin(abs * 14)})`;
    ctx.fillRect(caretX + u * 6, (topY + lineIdx * lh) - size * 0.42, Math.max(3, u * 7), size * 0.84);
  }
  ctx.restore();
  ctx.restore();
}

/* ───────────────── S7 · 11.0–12.0 · the text flies into the bar ───────────────── */
export function S7(ctx, L, t) {
  const { W, H } = L;
  const abs = t + 11.0;
  const G = appGeom(L);
  const fly = eInOutQuint(inv(0.02, 0.52, t));
  const push = lerp(1, 1.42, camEase(inv(0.35, 1.0, t)));
  const fx = lerp(W / 2, G.send.x, camEase(inv(0.35, 1.0, t)) * 0.55);
  const fy = lerp(H / 2, G.send.y, camEase(inv(0.35, 1.0, t)) * 0.55);

  ctx.save();
  cam(ctx, fx, fy, push);
  appStage(ctx, L, abs, {
    greetWords: 0, chips: 0, dimUI: 0.45,
    promptText: fly > 0.72 ? PROMPT : '', orb: 0, magenta: 1,
  });
  // the huge block shrinking into the bar
  if (fly < 0.98) {
    ctx.save();
    const sc = lerp(1, 0.085, fly);
    const tx = lerp(W / 2, G.textX + (G.barW * 0.30), fly);
    const ty = lerp(H / 2, G.textY, fly);
    ctx.translate(tx, ty); ctx.scale(sc, sc); ctx.translate(-W / 2, -H / 2);
    ctx.globalAlpha = 1 - Math.pow(fly, 3.2);
    S6(ctx, L, abs - 9.5, { count: PROMPT.length, caret: false, zoom: 1, camX: W / 2, camY: H / 2, alpha: 1 });
    ctx.restore();
  }
  ctx.restore();
}

/* ───────────────── S8 · 12.0–12.75 · orb → send → tap → white ───────────────── */
export function S8(ctx, L, t) {
  const { W, H, u } = L;
  const abs = t + 12.0;
  const G = appGeom(L);
  const orb = smooth(inv(0.02, 0.42, t));
  const tap = inv(0.46, 0.56, t);
  const flash = inv(0.52, 0.75, t);
  const push = lerp(1.42, 1.62, camEase(inv(0, 0.6, t)));
  const squash = tap > 0 && tap < 1 ? 1 - 0.18 * Math.sin(tap * Math.PI) : 1;

  ctx.save();
  cam(ctx, G.send.x, G.send.y, push * squash);
  appStage(ctx, L, abs, {
    greetWords: 0, chips: 0, dimUI: 0.45, promptText: PROMPT,
    orb, sendGlow: orb * 0.6 + (tap > 0 ? (1 - tap) * 0.8 : 0), magenta: 1,
  });
  if (tap > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    const p = clamp(tap);
    ctx.strokeStyle = `rgba(190,215,255,${(1 - p) * 0.9})`;
    ctx.lineWidth = Math.max(2, 14 * (1 - p) * u);
    ctx.beginPath(); ctx.arc(G.send.x, G.send.y, G.send.r * (1 + p * 5), 0, TAU); ctx.stroke();
    ctx.restore();
  }
  ctx.restore();

  if (flash > 0) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, G.send.x, G.send.y, Math.max(W, H) * (0.2 + flash * 1.6), [235, 243, 255], Math.pow(flash, 0.8));
    ctx.restore();
    ctx.save(); ctx.globalAlpha = Math.pow(inv(0.55, 1, flash), 1.3);
    ctx.fillStyle = '#FFFFFF'; ctx.fillRect(0, 0, W, H); ctx.restore();
  }
}

/* ───────────────── S9 · 12.75–16.0 · phones rise into a row of answers ───────────────── */
export function S9(ctx, L, t) {
  const { W, H, u, vert } = L;
  const settle = inv(0, 0.28, t);
  whiteStage(ctx, L, t + 12.75, { amount: 0.95 });

  const bodyH = vert ? H * 0.355 : H * 0.70;
  const slots = vert
    ? [{ x: -W * 0.305, y: H * 0.60, s: 0.86 }, { x: 0, y: H * 0.545, s: 1.06 }, { x: W * 0.305, y: H * 0.60, s: 0.86 }]
    : [{ x: -W * 0.245, y: H * 0.60, s: 0.88 }, { x: 0, y: H * 0.56, s: 1.06 }, { x: W * 0.245, y: H * 0.60, s: 0.88 }];

  const push = lerp(1.06, 1.0, camEase(inv(0.1, 1.2, t))) * lerp(1, 1.05, camEase(inv(1.4, 3.25, t)));
  ctx.save();
  cam(ctx, W / 2, H * 0.55, push, 0, Math.sin(t * 0.7) * 4 * u);

  const order = [1, 0, 2];
  order.forEach((i) => {
    const s = slots[i];
    const t0 = 0.10 + [0.00, 0.16, 0.26][order.indexOf(i)];
    const rise = eOutQuint(inv(t0, t0 + 0.62, t));
    if (rise <= 0) return;
    const slide = eInOutQuint(inv(t0 + 0.22, t0 + 0.92, t));
    const open = inv(t0 + 0.55, t0 + 1.35, t);
    const x = W / 2 + s.x * slide;
    const y = lerp(H + bodyH * 0.7, s.y, rise) + Math.sin(t * 1.3 + i) * 5 * u;
    const rot = lerp(i === 1 ? 0 : (i === 0 ? -0.10 : 0.10), i === 0 ? -0.045 : i === 2 ? 0.045 : 0, slide) + Math.sin(t * 0.9 + i) * 0.004;
    phone(ctx, x, y, bodyH * s.s, { rot, shadowA: 0.22 * rise }, (c, w, h) => {
      geminiApp(c, w, h, t, { answers: [FILMS[i]], answerIn: open, chips: 0, promptText: '', magenta: 0.4 });
    });
  });
  ctx.restore();

  if (settle < 1) { ctx.save(); ctx.globalAlpha = Math.pow(1 - settle, 1.4); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H); ctx.restore(); }
}

/* ───────────────── S10 · 16.0–18.5 · drop 2, "All answered. In seconds." ───────────────── */
export function S10(ctx, L, t) {
  const { W, H, u, vert } = L;
  const abs = t + 16.0;
  const pull = camEase(inv(1.18, 1.82, t));
  // big enough to crop, never so big that the word the voice is on falls off frame
  const zoom = lerp(lerp(vert ? 1.62 : 1.78, vert ? 1.30 : 1.33, camEase(inv(0.15, 0.75, t))), 1.0, pull)
    * lerp(1, 1.04, inv(1.9, 2.5, t));

  // frame shake from each slam
  let shx = 0, shy = 0;
  VO.l5.forEach((w, i) => {
    const d = abs - w.t; if (d < 0) return;
    const amp = (i === 1 ? 26 : 16) * u;
    shx += decay(d, 12, 0.11) * amp; shy += decay(d + 0.01, 10, 0.11) * amp * 0.6;
  });

  ctx.save();
  overscan(ctx, L, 1.05);
  dotGrid(ctx, L, abs, { amount: 1, scroll: -abs * 26, spacing: (vert ? 56 : 64) * (1 / zoom > 0.5 ? 1 : 1) });
  ctx.restore();

  ctx.save();
  overscan(ctx, L, 1.05);
  ctx.translate(shx, shy);
  const l1y = H * (vert ? 0.42 : 0.40), l2y = H * (vert ? 0.58 : 0.60);
  // line 1 — fixed word slots, slams in place
  const l1 = ['All', 'answered.'];
  const size1 = Math.min(fitSize(ctx, l1.join(' '), W * 0.92, 900, 1200, -0.022), H * (vert ? 0.17 : 0.30));
  font(ctx, size1, 900, -size1 * 0.022);
  const totalW = ctx.measureText(l1.join(' ')).width;
  const wAll = ctx.measureText('All').width, spW0 = ctx.measureText(' ').width;
  // the camera rides from the first word to the second, then centres for the pull-out
  const cxA = W / 2 - totalW / 2 + wAll / 2;
  const cxB = W / 2 - totalW / 2 + wAll + spW0 + (totalW - wAll - spW0) / 2;
  const camX = lerp(lerp(cxA, cxB, camEase(inv(0.30, 0.64, t))), W / 2, pull);
  cam(ctx, camX, l1y, zoom, W / 2 - camX, 0);
  let x = W / 2 - totalW / 2;
  const spaceW = ctx.measureText(' ').width;
  l1.forEach((wd, i) => {
    const wv = VO.l5[i];
    const p = inv(wv.t - 0.13, wv.t, abs);
    const ww = ctx.measureText(wd).width;
    if (p > 0) {
      const d = abs - wv.t;
      let sc = lerp(0.3, 1, eInQuart(p));
      if (d >= 0) sc = 1 + 0.055 * decay(d, 9, 0.085);
      ctx.save();
      ctx.globalAlpha = Math.pow(p, 0.6);
      if (p < 1) ctx.filter = `blur(${(1 - p) * 24 * u}px)`;
      ctx.translate(x + ww / 2, l1y); ctx.scale(sc, sc);
      font(ctx, size1, 900, -size1 * 0.022);
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillStyle = '#fff';
      ctx.fillText(wd, 0, 0);
      ctx.restore();
      shockwave(ctx, L, x + ww / 2, l1y, inv(0, 0.7, d), { max: 0.55, color: [150, 200, 255] });
    }
    x += ww + (i === 0 ? spaceW : 0);
  });

  // line 2 — arrives inside the pull-back
  const l2 = ['In', 'seconds.'];
  const size2 = Math.min(fitSize(ctx, l2.join(' '), W * 0.62, 900, 1200, -0.022), H * (vert ? 0.13 : 0.22));
  font(ctx, size2, 900, -size2 * 0.022);
  const tw2 = ctx.measureText(l2.join(' ')).width;
  let x2 = W / 2 - tw2 / 2;
  const sp2 = ctx.measureText(' ').width;
  l2.forEach((wd, i) => {
    const wv = VO.l5[i + 2];
    const p = inv(wv.t - 0.13, wv.t, abs);
    const ww = ctx.measureText(wd).width;
    if (p > 0) {
      const d = abs - wv.t;
      let sc = lerp(0.45, 1, eInQuart(p));
      if (d >= 0) sc = 1 + 0.05 * decay(d, 9, 0.09);
      ctx.save();
      ctx.globalAlpha = Math.pow(p, 0.6);
      if (p < 1) ctx.filter = `blur(${(1 - p) * 16 * u}px)`;
      ctx.translate(x2 + ww / 2, l2y); ctx.scale(sc, sc);
      font(ctx, size2, 900, -size2 * 0.022);
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      const lx = (W / 2 - tw2 / 2) - (x2 + ww / 2);
      ctx.fillStyle = gemGrad(ctx, lx, 0, lx + tw2, 0);
      ctx.fillText(wd, 0, 0);
      ctx.restore();
    }
    x2 += ww + (i === 0 ? sp2 : 0);
  });
  ctx.restore();
  vignette(ctx, L, 0.30);
}

/* ───────────────── S11 · 18.5–21.0 · experience Gemini ───────────────── */
export function S11(ctx, L, t) {
  const { W, H, u, vert } = L;
  const abs = t + 18.5;
  navyStage(ctx, L, abs, { zoom: 1 + t * 0.008, drift: -t * 0.0015, lift: 0.8 });
  ctx.save();
  ctx.globalCompositeOperation = 'screen';
  glow(ctx, W * 0.5, H * 0.78, Math.max(W, H) * 0.7, [40, 90, 210], 0.30);
  ctx.restore();

  const push = lerp(1.05, 1.0, camEase(inv(0, 1.0, t))) * lerp(1, 1.045, camEase(inv(0.9, 2.5, t)));
  ctx.save();
  cam(ctx, W / 2, H * 0.5, push);

  // devices
  const dev = eOutQuint(inv(0.30, 1.15, t));
  const dev2 = eOutQuint(inv(0.44, 1.32, t));
  const neon = smooth(inv(0.75, 1.5, t));
  if (vert) {
    const bw = W * 0.86, bh = bw * 0.66;
    const by = lerp(H + bh, H * 0.515, dev2);
    browserWindow(ctx, W * 0.5, by, bw, bh, abs, { neon: neon * 1.35, reveal: smooth(inv(0.95, 1.5, t)) });
    const bodyH = H * 0.30;
    const py = lerp(H + bodyH, H * 0.775, dev);
    phone(ctx, W * 0.5, py + Math.sin(t * 1.2) * 4 * u, bodyH, { rot: -0.03, neon: neon * 1.4, shadowA: 0.4 }, (c, w, h) => {
      geminiApp(c, w, h, abs, { greetWords: 1, chips: 0.8, magenta: 1 });
    });
  } else {
    const bw = W * 0.46, bh = bw * 0.60;
    const bx = W * 0.62, by = lerp(H + bh, H * 0.70, dev2);
    browserWindow(ctx, bx, by, bw, bh, abs, { neon: neon * 1.35, reveal: smooth(inv(0.95, 1.5, t)) });
    const bodyH = H * 0.56;
    const py = lerp(H + bodyH, H * 0.74, dev);
    phone(ctx, W * 0.30, py + Math.sin(t * 1.2) * 4 * u, bodyH, { rot: -0.04, neon: neon * 1.4, shadowA: 0.42 }, (c, w, h) => {
      geminiApp(c, w, h, abs, { greetWords: 1, chips: 0.8, magenta: 1 });
    });
  }

  // headline — fixed slots, no re-centring
  const cap = Math.min(vert ? W * 0.125 : H * 0.135, H * 0.16);
  const size = Math.min(cap, fitSize(ctx, 'Experience Gemini', W * 0.86, 600, cap, -0.018));
  font(ctx, size, 600, -size * 0.018);
  const w1 = ctx.measureText('Experience ').width, w2 = ctx.measureText('Gemini').width;
  const hx = W / 2 - (w1 + w2) / 2, hy = H * (vert ? 0.20 : 0.25);
  const pA = smooth(inv(VO.experience - 18.5 - 0.12, VO.experience - 18.5 + 0.22, t));
  const pB = smooth(inv(VO.geminiWord - 18.5 - 0.12, VO.geminiWord - 18.5 + 0.22, t));
  ctx.save(); ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  if (pA > 0) {
    ctx.save(); ctx.globalAlpha = pA; ctx.filter = `blur(${(1 - pA) * 20 * u}px)`;
    ctx.fillStyle = '#fff';
    ctx.translate(0, (1 - pA) * size * 0.25);
    ctx.fillText('Experience', hx, hy); ctx.restore();
  }
  if (pB > 0) {
    ctx.save(); ctx.globalAlpha = pB; ctx.filter = `blur(${(1 - pB) * 20 * u}px)`;
    ctx.translate(0, (1 - pB) * size * 0.25);
    ctx.fillStyle = gemGrad(ctx, hx + w1, 0, hx + w1 + w2, 0);
    ctx.fillText('Gemini', hx + w1, hy); ctx.restore();
  }
  ctx.restore();

  // url
  const pu = smooth(inv(1.05, 1.5, t));
  if (pu > 0) {
    ctx.save(); ctx.globalAlpha = pu;
    const us = size * 0.30;
    font(ctx, us, 500, us * 0.02);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    const uw = ctx.measureText('gemini.google.com').width;
    ctx.fillStyle = 'rgba(255,255,255,0.09)';
    roundRect(ctx, W / 2 - uw / 2 - us * 1.1, hy + size * 0.80 - us * 0.95, uw + us * 2.2, us * 1.9, us * 0.95); ctx.fill();
    ctx.fillStyle = 'rgba(226,236,255,0.92)';
    ctx.fillText('gemini.google.com', W / 2, hy + size * 0.80);
    ctx.restore();
  }
  ctx.restore();
  vignette(ctx, L, 0.34);
}

/* ───────────────── S12 · 21.0–24.0 · orb swirls, bursts into the G ───────────────── */
export function S12(ctx, L, t) {
  const { W, H, u } = L;
  const abs = t + 21.0;
  const cx = W / 2, cy = H * 0.48;
  const R = Math.min(W, H) * 0.56;
  const burst = 1.30;
  const push = lerp(1.0, 1.085, camEase(inv(0, 3.0, t)));

  navyStage(ctx, L, abs, { zoom: 1 + t * 0.006, drift: -t * 0.001, lift: 0.8 });
  ctx.save();
  cam(ctx, cx, cy, push);

  const orbAt = (p) => {
    const e = eInOutCubic(clamp(p));
    const a = -Math.PI * 0.35 + TAU * 2.15 * e;
    const r = R * (1 - eInCubic(clamp(p))) * (0.78 + 0.22 * Math.cos(p * 5.0));
    return [cx + Math.cos(a) * r, cy + Math.sin(a) * r * 0.78];
  };

  if (t < burst + 0.1) {
    const p = clamp(t / burst);
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    for (let j = 26; j >= 0; j--) {
      const pp = p - j * 0.011;
      if (pp < 0) continue;
      const [x, y] = orbAt(pp);
      const k = 1 - j / 27;
      glow(ctx, x, y, u * (10 + 60 * k), [170, 205, 255], 0.38 * k * k);
    }
    const [ox, oy] = orbAt(p);
    glow(ctx, ox, oy, u * 110, [210, 230, 255], 0.65);
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.arc(ox, oy, u * 11, 0, TAU); ctx.fill();
    ctx.restore();
  }

  // burst
  const pb = inv(burst, burst + 0.42, t);
  if (pb > 0 && pb < 1) {
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, cx, cy, Math.max(W, H) * (0.08 + pb * 0.55), [255, 255, 255], Math.pow(1 - pb, 2.1));
    glow(ctx, cx, cy, Math.max(W, H) * (0.03 + pb * 0.18), [255, 255, 255], Math.pow(1 - pb, 1.2));
    ctx.restore();
    shockwave(ctx, L, cx, cy, pb, { max: 0.7, color: [200, 225, 255], width: 1.4 });
    streaks(ctx, L, cx, cy, pb, { n: 40, seed: 404, len: 0.3, color: [200, 225, 255] });
  }

  // the G draws itself out of the burst
  const pg = inv(burst + 0.02, burst + 0.52, t);
  if (pg > 0) {
    const Rg = Math.min(W, H) * 0.165;
    ctx.save();
    const sweep = 308 * pg;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, Rg * 1.6, (-52 * Math.PI) / 180, (-(52 + sweep) * Math.PI) / 180, true);
    ctx.closePath();
    ctx.clip();
    googleG(ctx, cx, cy, Rg);
    ctx.restore();
    // the bar lands last
    if (pg > 0.92) {
      const k = inv(0.92, 1, pg);
      ctx.save(); ctx.globalAlpha = k;
      ctx.fillStyle = G_BLUE;
      const wbar = Rg * 0.30;
      roundRect(ctx, cx + Rg * 0.06, cy - wbar * 0.5, Rg * 0.94 * k, wbar, wbar * 0.12); ctx.fill();
      ctx.restore();
    }
  }
  // twinkle
  const tw = inv(1.95, 2.45, t);
  if (tw > 0 && tw < 1) {
    const Rg = Math.min(W, H) * 0.165;
    const a = Math.sin(tw * Math.PI);
    ctx.save(); ctx.globalCompositeOperation = 'screen';
    glow(ctx, cx + Rg * 0.72, cy - Rg * 0.66, u * 120 * a, [255, 255, 255], 0.55 * a);
    twinkle(ctx, cx + Rg * 0.72, cy - Rg * 0.66, u * (26 + 34 * a), a);
    ctx.restore();
  }
  // wordmark under the G
  const pw = inv(1.75, 2.25, t);
  if (pw > 0) {
    ctx.save();
    ctx.globalAlpha = smooth(pw);
    const s = Math.min(W, H) * 0.072;
    ctx.translate(0, (1 - smooth(pw)) * s * 0.3);
    wordGemini(ctx, cx, cy + Math.min(W, H) * 0.30, s, { weight: 600, light: true });
    ctx.restore();
  }
  ctx.restore();
  vignette(ctx, L, 0.40);
}

/* ───────────────── S13 · 24.0–26.0 · end card ───────────────── */
export function S13(ctx, L, t) {
  const { W, H, u } = L;
  const abs = t + 24.0;
  whiteStage(ctx, L, abs, { amount: 0.75 });
  const inP = smooth(inv(0.06, 0.55, t));
  const push = lerp(1.04, 1.0, camEase(inv(0, 1.4, t))) * lerp(1, 1.02, camEase(inv(1.2, 2.0, t)));
  ctx.save();
  cam(ctx, W / 2, H * 0.5, push);

  const cy = H * (L.vert ? 0.46 : 0.47);
  ctx.save();
  ctx.globalAlpha = inP;
  ctx.translate(0, (1 - inP) * 18 * u);
  sparkle(ctx, W / 2, cy - (L.vert ? H * 0.085 : H * 0.14), Math.min(W, H) * 0.045, {});
  const SIG = 'Denis Unagst';
  const sCap = Math.min(W, H) * (L.vert ? 0.115 : 0.105);
  const s = Math.min(sCap, fitSize(ctx, SIG, W * 0.78, 700, sCap, -0.02));
  font(ctx, s, 700, -s * 0.02);
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = '#0B0E18';
  ctx.fillText(SIG, W / 2, cy);
  const s2 = s * 0.22;
  font(ctx, s2, 500, s2 * 0.08);
  ctx.fillStyle = 'rgba(11,14,24,0.55)';
  ctx.fillText('AI MOTION  ·  BUILT ENTIRELY IN CODE', W / 2, cy + s * 0.72);
  ctx.restore();

  // thin gemini rule, wipes in
  const rule = eOutQuart(inv(0.35, 1.1, t));
  if (rule > 0) {
    const rw = Math.min(W * 0.46, 760) * rule;
    ctx.save();
    ctx.fillStyle = gemGrad(ctx, W / 2 - rw / 2, 0, W / 2 + rw / 2, 0);
    roundRect(ctx, W / 2 - rw / 2, cy + s * 1.12, rw, Math.max(2, u * 4), u * 2); ctx.fill();
    ctx.restore();
  }
  ctx.restore();

  // disclaimer
  const dp = smooth(inv(0.8, 1.4, t));
  if (dp > 0) {
    ctx.save(); ctx.globalAlpha = dp;
    const dTxt = 'Spec work for portfolio purposes only. Not affiliated with, sponsored or endorsed by Google LLC.';
    const dCap = Math.min(W, H) * 0.021;
    const ds = Math.min(dCap, fitSize(ctx, dTxt, W * 0.86, 450, dCap, 0));
    font(ctx, ds, 450, 0);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillStyle = 'rgba(11,14,24,0.58)';
    ctx.fillText(dTxt, W / 2, H * 0.90);
    ctx.restore();
  }
  // gentle sign-off
  const out = inv(1.82, 2.0, t);
  if (out > 0) { ctx.save(); ctx.globalAlpha = out; ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, W, H); ctx.restore(); }
}
