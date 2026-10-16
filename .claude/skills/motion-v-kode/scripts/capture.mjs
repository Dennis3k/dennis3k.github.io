/* capture.mjs — покадровый рендер страницы прямо в x264.
 *
 *   node capture.mjs h                    # 1920x1080 -> out/master_16x9.mp4
 *   node capture.mjs v --name myfilm      # 1080x1920 -> out/myfilm_9x16.mp4
 *
 * Страница должна отдавать window.__ready, window.__total, window.__fps
 * и window.__frame(n) -> dataURL PNG (см. references/pipeline.md).
 */
import { chromium } from 'playwright';
import { spawn } from 'child_process';
import { mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { serve } from './serve.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const argv = process.argv.slice(2);
const fmt = (argv[0] || 'h').toLowerCase();
const nameArg = argv.includes('--name') ? argv[argv.indexOf('--name') + 1] : 'master';
const [W, H] = fmt === 'v' ? [1080, 1920] : [1920, 1080];
const name = `${nameArg}_${fmt === 'v' ? '9x16' : '16x9'}`;
mkdirSync(resolve(ROOT, 'out'), { recursive: true });
const outFile = resolve(ROOT, `out/${name}.mp4`);

const srv = await serve(ROOT);
const browser = await chromium.launch({
  args: ['--force-color-profile=srgb', '--font-render-hinting=none', '--disable-dev-shm-usage'],
});
const page = await browser.newPage({ viewport: { width: 420, height: 260 } });
page.on('pageerror', (e) => console.error('PAGE ERROR:', e.message));
await page.goto(`http://127.0.0.1:${srv.port}/index.html?w=${W}&h=${H}`);
await page.waitForFunction('window.__ready===true', null, { timeout: 120000 });
const TOTAL = await page.evaluate(() => window.__total);
const FPS = await page.evaluate(() => window.__fps);
console.log(`[${name}] ${W}x${H} · ${TOTAL} frames @ ${FPS}fps`);

const ff = spawn('ffmpeg', [
  '-y', '-loglevel', 'error',
  '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-',
  '-c:v', 'libx264', '-preset', 'medium', '-crf', '15',
  '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
  '-movflags', '+faststart', outFile,
]);
ff.stderr.on('data', (d) => process.stderr.write(d));
const write = (buf) => new Promise((res) => (ff.stdin.write(buf) ? res() : ff.stdin.once('drain', res)));

const t0 = Date.now();
for (let f = 0; f < TOTAL; f++) {
  const d = await page.evaluate((i) => window.__frame(i), f);
  await write(Buffer.from(d.slice(d.indexOf(',') + 1), 'base64'));
  if (f % 30 === 0 || f === TOTAL - 1) {
    const el = (Date.now() - t0) / 1000;
    const eta = f ? (el / (f + 1)) * (TOTAL - f - 1) : 0;
    console.log(`  ${String(f + 1).padStart(3)}/${TOTAL}  t=${(f / FPS).toFixed(2)}s  elapsed ${el.toFixed(0)}s  eta ${eta.toFixed(0)}s`);
  }
}
ff.stdin.end();
await new Promise((res) => ff.on('close', res));
await browser.close(); srv.close();
console.log(`[${name}] done -> ${outFile}  (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
