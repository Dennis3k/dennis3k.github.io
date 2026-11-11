#!/usr/bin/env python3
"""Markdown -> PDF: сценарий или промты одним файлом для заказчика.

Заточено под файлы этого скилла: заголовки, таблицы, блоки кода с переносом,
разрыв страницы перед каждым кадром, титул и колонтитул с номером страницы.

  python3 vpdf.py raskadrovka.md -o out.pdf --title "Название клипа" \
      --sub "Промты на 10 кадров" --meta "артист · локация<br>дата"

Рендерит Chromium через playwright: он уже стоит в окружении, даёт кириллицу
из коробки и оставляет текст выделяемым — промты копируются прямо из PDF.
Кегль моноширинного блока подобран так, чтобы промт на кадр умещался на одну
страницу A4: 7.0pt при интерлиньяже 1.36. Крупнее — промты рвутся пополам и
копировать их неудобно.
"""

import html, re, sys

def inline(t):
    t = html.escape(t)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', t)
    return t

def convert(md):
    out, i, lines = [], 0, md.split("\n")
    while i < len(lines):
        L = lines[i]
        if L.startswith("```"):
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append('<pre>' + html.escape("\n".join(buf)) + '</pre>')
            continue
        if L.strip() == "---":
            i += 1; continue
        if L.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            cells = [c for c in cells if not all(set(x) <= set("-: ") for x in c)]
            if cells:
                out.append("<table><thead><tr>" +
                           "".join(f"<th>{inline(c)}</th>" for c in cells[0]) +
                           "</tr></thead><tbody>")
                for r in cells[1:]:
                    out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
                out.append("</tbody></table>")
            continue
        m = re.match(r'^(#{1,4})\s+(.*)$', L)
        if m:
            n, txt = len(m.group(1)), m.group(2)
            cls = ' class="shot"' if txt.startswith(("КАДР", "Порядок", "Чеклист")) else ""
            out.append(f"<h{n}{cls}>{inline(txt)}</h{n}>"); i += 1; continue
        if L.startswith(("- ", "* ")):
            items = []
            while i < len(lines) and lines[i].startswith(("- ", "* ")):
                items.append(inline(lines[i][2:])); i += 1
            out.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            continue
        if re.match(r'^\d+\.\s', L):
            items = []
            while i < len(lines) and re.match(r'^\d+\.\s', lines[i]):
                items.append(inline(re.sub(r'^\d+\.\s', '', lines[i]))); i += 1
            out.append("<ol>" + "".join(f"<li>{x}</li>" for x in items) + "</ol>")
            continue
        if L.strip():
            buf = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(
                    ("#", "|", "```", "- ", "* ")) and lines[i].strip() != "---":
                buf.append(lines[i].strip()); i += 1
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
            continue
        i += 1
    return "\n".join(out)

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm 16mm; }
* { box-sizing: border-box; }
body { font-family: Inter, "DejaVu Sans", sans-serif; font-size: 10pt;
       line-height: 1.5; color: #1a1a1c; margin: 0; }
h1 { font-size: 20pt; font-weight: 800; letter-spacing: -0.02em;
     margin: 0 0 4mm; line-height: 1.2; }
h2 { font-size: 13pt; font-weight: 700; margin: 7mm 0 3mm;
     padding-bottom: 2mm; border-bottom: 1.5px solid #d8d8dc; line-height: 1.3; }
h2.shot { page-break-before: always; margin-top: 0; }
h3 { font-size: 11pt; font-weight: 700; margin: 5mm 0 2mm; }
p { margin: 0 0 3mm; }
ul, ol { margin: 0 0 3mm; padding-left: 6mm; }
li { margin-bottom: 1.2mm; }
strong { font-weight: 700; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.5pt;
       background: #f0f0f3; padding: 0.4mm 1mm; border-radius: 1mm; }
pre { font-family: "DejaVu Sans Mono", monospace; font-size: 7.0pt;
      line-height: 1.36; background: #f7f7f9; border: 1px solid #e2e2e6;
      border-left: 2.5mm solid #2f6fd0; border-radius: 1.5mm;
      padding: 3.5mm 4mm; margin: 0 0 4mm;
      white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; }
pre code { background: none; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; margin: 0 0 4mm; font-size: 8.8pt; }
th { background: #eef1f6; font-weight: 700; text-align: left; }
th, td { border: 1px solid #d8d8dc; padding: 1.6mm 2.2mm; vertical-align: top; }
h2, h3 { page-break-after: avoid; }
pre, table, li { page-break-inside: avoid; }
.cover { page-break-after: always; padding-top: 55mm; }
.cover h1 { font-size: 30pt; margin-bottom: 6mm; }
.cover .sub { font-size: 13pt; color: #55555c; margin-bottom: 2mm; }
.cover .meta { margin-top: 14mm; font-size: 9.5pt; color: #6a6a72; line-height: 1.8; }
.cover .rule { height: 3px; background: #2f6fd0; width: 34mm; margin: 8mm 0; }
"""

RENDER = """
const { chromium } = require('playwright');
(async () => {
  const [src, dst, foot] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + src, { waitUntil: 'networkidle' });
  await page.pdf({
    path: dst, format: 'A4', printBackground: true,
    displayHeaderFooter: true, headerTemplate: '<div></div>',
    footerTemplate:
      '<div style="width:100%;font-family:sans-serif;font-size:7pt;color:#8a8a92;'
      + 'padding:0 16mm;display:flex;justify-content:space-between;">'
      + '<span>' + foot + '</span><span class="pageNumber"></span></div>',
    margin: { top: '18mm', bottom: '20mm', left: '16mm', right: '16mm' }
  });
  await browser.close();
})();
"""


def main():
    import argparse, subprocess, tempfile, os
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--sub", default="")
    ap.add_argument("--meta", default="", help="подзаголовок титула, можно <br>")
    ap.add_argument("--no-cover", action="store_true",
                    help="без титула и колонтитула: только содержимое файла")
    ap.add_argument("--pre-pt", default="7.0",
                    help="кегль блоков кода; для длинных промтов с полным замком личности 6.2")
    a = ap.parse_args()
    css = CSS.replace("font-size: 7.0pt;", f"font-size: {a.pre_pt}pt;")
    src, dst, title, sub, meta = a.markdown, a.out, a.title, a.sub, a.meta
    body = convert(open(src, encoding="utf-8").read())
    body = re.sub(r'^<h1>.*?</h1>\n?', '', body, count=1)
    cover = "" if a.no_cover else (f'<div class="cover"><h1>{html.escape(title)}</h1>'
             f'<div class="rule"></div>'
             f'<div class="sub">{html.escape(sub)}</div>'
             f'<div class="meta">{meta}</div></div>')
    tmp = tempfile.mkdtemp()
    page = os.path.join(tmp, "doc.html")
    js = os.path.join(tmp, "render.js")
    open(page, "w", encoding="utf-8").write(
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8">'
        f'<title>{html.escape(title)}</title><style>{css}</style></head>'
        f'<body>{cover}{body}</body></html>')
    open(js, "w", encoding="utf-8").write(RENDER)
    foot = " " if a.no_cover else (f"{title} · {sub}" if sub else title)
    r = subprocess.run(["node", js, page, os.path.abspath(dst), foot],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("playwright не отрендерил:\n" + r.stderr[-800:])
    print(f"pdf: {dst}")


if __name__ == "__main__":
    main()
