/* main.js — frame composition: scene routing + real sub-frame motion blur */
import * as SC from './scenes.js';
import { CUTS, FPS, TOTAL, blurAt } from './timing.js';

export function makeLayout(W, H) {
  return { W, H, vert: H > W, u: Math.min(W, H) / 1080, cx: W / 2, cy: H / 2 };
}

const ORDER = Object.keys(CUTS);
export function drawAt(ctx, L, t) {
  for (const k of ORDER) {
    const [a, b] = CUTS[k];
    if (t >= a && t < b) { ctx.save(); SC[k](ctx, L, t - a); ctx.restore(); return k; }
  }
  const last = ORDER[ORDER.length - 1];
  ctx.save(); SC[last](ctx, L, CUTS[last][1] - CUTS[last][0] - 1e-4); ctx.restore();
  return last;
}

/* power-of-two sub-frame count keeps the binary average exact */
const pow2 = (n) => (n <= 1 ? 1 : n <= 3 ? 2 : n <= 6 ? 4 : n <= 12 ? 8 : n <= 24 ? 16 : 32);

export class Renderer {
  constructor(W, H) {
    this.W = W; this.H = H;
    this.L = makeLayout(W, H);
    this.free = [];
  }
  _take() {
    const c = this.free.pop() || (() => {
      const cv = typeof OffscreenCanvas !== 'undefined' ? new OffscreenCanvas(this.W, this.H) : Object.assign(document.createElement('canvas'), { width: this.W, height: this.H });
      cv.width = this.W; cv.height = this.H;
      return cv;
    })();
    return c;
  }
  _give(c) { this.free.push(c); }

  /** average `n` sub-frames pairwise up a binary tree — 8-bit safe */
  frame(outCtx, t, { shutter = 0.85, sub = null } = {}) {
    const dt = 1 / FPS;
    const n = pow2(sub ?? blurAt(t));
    const levels = [];
    for (let i = 0; i < n; i++) {
      const c = this._take();
      const cx = c.getContext('2d', { alpha: false });
      cx.setTransform(1, 0, 0, 1, 0, 0);
      cx.globalAlpha = 1; cx.globalCompositeOperation = 'source-over'; cx.filter = 'none';
      cx.clearRect(0, 0, this.W, this.H);
      cx.fillStyle = '#000'; cx.fillRect(0, 0, this.W, this.H);
      const st = t + ((i + 0.5) / n) * dt * shutter;
      drawAt(cx, this.L, st);
      let cur = c, lvl = 0;
      while (levels[lvl]) {
        const a = levels[lvl];
        const ac = a.getContext('2d', { alpha: false });
        ac.setTransform(1, 0, 0, 1, 0, 0);
        ac.globalAlpha = 0.5; ac.globalCompositeOperation = 'source-over'; ac.filter = 'none';
        ac.drawImage(cur, 0, 0);
        ac.globalAlpha = 1;
        this._give(cur);
        cur = a; levels[lvl] = null; lvl++;
      }
      levels[lvl] = cur;
    }
    let res = null;
    for (const l of levels) if (l) res = l;
    outCtx.setTransform(1, 0, 0, 1, 0, 0);
    outCtx.globalAlpha = 1; outCtx.globalCompositeOperation = 'source-over'; outCtx.filter = 'none';
    outCtx.drawImage(res, 0, 0);
    this._give(res);
    return n;
  }
}
export { FPS, TOTAL, CUTS };
