/* tiny static server so ES modules load without file:// CORS */
import { createServer } from 'http';
import { readFile } from 'fs/promises';
import { extname, resolve, normalize } from 'path';
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css', '.json': 'application/json' };
export function serve(root) {
  return new Promise((res) => {
    const srv = createServer(async (req, rq) => {
      try {
        const p = resolve(root, '.' + normalize(decodeURIComponent(req.url.split('?')[0])));
        if (!p.startsWith(root)) { rq.writeHead(403).end(); return; }
        const body = await readFile(p);
        rq.writeHead(200, { 'content-type': TYPES[extname(p)] || 'application/octet-stream' });
        rq.end(body);
      } catch { rq.writeHead(404).end('nope'); }
    });
    srv.listen(0, '127.0.0.1', () => res({ port: srv.address().port, close: () => srv.close() }));
  });
}
