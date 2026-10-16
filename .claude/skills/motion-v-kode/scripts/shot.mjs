/* shot.mjs — render still frames (and contact sheets) for review */
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { serve } from './serve.mjs';
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');

const args = process.argv.slice(2);
const fmt = args[0] === 'v' ? 'v' : 'h';
const times = args.slice(1).map(Number);
const [W, H] = fmt === 'v' ? [1080, 1920] : [1920, 1080];
const outDir = resolve(ROOT, 'out/stills');
mkdirSync(outDir, { recursive: true });

const srv = await serve(ROOT);
const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
const page = await browser.newPage({ viewport: { width: 500, height: 300 } });
page.on('pageerror', (e) => console.error('PAGE ERROR:', e.message));
page.on('console', (m) => { if (m.type() === 'error') console.error('CONSOLE:', m.text()); });
await page.goto(`http://127.0.0.1:${srv.port}/index.html?w=${W}&h=${H}`);
await page.waitForFunction('window.__ready===true', null, { timeout: 60000 });
console.log('fonts:', JSON.stringify(await page.evaluate(() => window.__fontCheck)));
for (const t of times) {
  const d = await page.evaluate(([tt]) => window.__at(tt, 2), [t]);
  const f = `${outDir}/${fmt}_${t.toFixed(2)}.png`;
  writeFileSync(f, Buffer.from(d.slice(d.indexOf(',') + 1), 'base64'));
  console.log('wrote', f);
}
await browser.close(); srv.close();
