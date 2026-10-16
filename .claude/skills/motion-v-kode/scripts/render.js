/* render.js — накопитель motion blur: усреднение субкадров бинарным деревом.
 * Самодостаточен: ничего не знает про сцены, получает их функцией.
 *
 *   import { Renderer } from './render.js';
 *   const R = new Renderer(1920, 1080, {
 *     fps: 30,
 *     draw: (ctx, t) => drawAt(ctx, L, t),   // кадр как функция времени
 *     blurAt: (t) => 4,                      // субкадров на этот момент
 *   });
 *   R.frame(outCtx, t);
 */

/** степень двойки — иначе дерево усреднения не сойдётся в один корень */
const pow2 = (n) => (n <= 1 ? 1 : n <= 3 ? 2 : n <= 6 ? 4 : n <= 12 ? 8 : n <= 24 ? 16 : 32);

export class Renderer {
  constructor(W, H, { fps = 30, draw, blurAt = () => 4 } = {}) {
    if (typeof draw !== 'function') throw new Error('Renderer needs draw(ctx, t)');
    this.W = W; this.H = H; this.fps = fps;
    this.draw = draw; this.blurAt = blurAt;
    this.free = [];
  }
  _take() {
    const c = this.free.pop() || (typeof OffscreenCanvas !== 'undefined'
      ? new OffscreenCanvas(this.W, this.H)
      : document.createElement('canvas'));
    c.width = this.W; c.height = this.H;
    return c;
  }
  _give(c) { this.free.push(c); }

  /**
   * Рисует кадр времени t в outCtx.
   * shutter — доля длительности кадра, по которой берётся выборка (0.85 держит
   * удар резким на его собственном кадре и мажет подлёт на предыдущем).
   * sub — принудительное число субкадров, иначе берётся из blurAt.
   */
  frame(outCtx, t, { shutter = 0.85, sub = null } = {}) {
    const dt = 1 / this.fps;
    const n = pow2(sub ?? this.blurAt(t));
    const levels = [];
    for (let i = 0; i < n; i++) {
      const c = this._take();
      const cx = c.getContext('2d', { alpha: false });
      cx.setTransform(1, 0, 0, 1, 0, 0);
      cx.globalAlpha = 1; cx.globalCompositeOperation = 'source-over'; cx.filter = 'none';
      cx.fillStyle = '#000'; cx.fillRect(0, 0, this.W, this.H);
      this.draw(cx, t + ((i + 0.5) / n) * dt * shutter);
      // поднимаем кадр по дереву: пока на уровне кто-то есть — усредняем 50/50
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
