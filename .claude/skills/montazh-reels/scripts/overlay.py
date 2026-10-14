#!/usr/bin/env python3
"""Сборка ролика жанра «обогащение»: оверлеи поверх непрерывного дубля.

Берёт JSON-спецификацию, рисует текстовые блоки в PIL, накладывает их через
ffmpeg, правит экспозицию и нормализует громкость. Один рендер — один файл.

Спецификация (spec.json):

{
  "input": "src.mp4",
  "output": "out.mp4",
  "in": 0.0, "out": 15.0,
  "width": 1080, "height": 1920, "fps": 30,
  "loudness": -14,
  "grade": {"shadows": 0.05, "highlights": -0.08, "saturation": 1.06},
  "badge": "ТЕСТ СТИЛЯ",
  "blocks": [
    {"t": 0.6, "dur": 2.4, "pos": "tl", "size": 64,
     "lines": [["я просто покажу", 0], ["ЧТО ОН УМЕЕТ", 1]]}
  ]
}

У строки второе значение — акцент: 0 белая, 1 акцентным цветом.
Строки блока появляются по одной, с шагом "step" (по умолчанию 0.28 с).
pos: tl, tr, bl, br, c.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
WHITE = (255, 255, 255, 255)
ACCENT = (79, 140, 255, 255)
MARGIN = 72


def font(size):
    return ImageFont.truetype(FONT, size)


def draw_block(lines, size, width, align="left"):
    """PNG с текстовым блоком: белый текст, акцентные строки цветом, тень."""
    f = font(size)
    lh = int(size * 1.18)
    pad = int(size * 0.5)
    probe = Image.new("RGBA", (10, 10))
    d0 = ImageDraw.Draw(probe)
    widths = [d0.textbbox((0, 0), t, font=f)[2] for t, _ in lines]
    w = min(width - 2 * MARGIN, max(widths) + 2 * pad)
    h = lh * len(lines) + 2 * pad
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    stroke = max(2, int(size * 0.055))
    for i, (text, accent) in enumerate(lines):
        y = pad + i * lh
        x = pad if align == "left" else w - pad - widths[i]
        # тень плюс обводка: на светлой стене одной тени не хватает
        d.text((x, y + int(size * 0.06)), text, font=f, fill=(0, 0, 0, 90),
               stroke_width=stroke + 2, stroke_fill=(0, 0, 0, 90))
        d.text((x, y), text, font=f, fill=ACCENT if accent else WHITE,
               stroke_width=stroke, stroke_fill=(0, 0, 0, 180))
    return img


def place(pos, bw, bh, W, H):
    top, bottom = 250, H - 420
    if pos == "tl":
        return MARGIN, top
    if pos == "tr":
        return W - MARGIN - bw, top
    if pos == "bl":
        return MARGIN, bottom - bh
    if pos == "br":
        return W - MARGIN - bw, bottom - bh
    return (W - bw) // 2, (H - bh) // 2


def build(spec, workdir):
    src = spec["input"]
    if not os.path.exists(src):
        sys.exit(f"нет файла: {src}")
    W = int(spec.get("width", 1080))
    H = int(spec.get("height", 1920))
    fps = int(spec.get("fps", 30))
    t0 = float(spec.get("in", 0.0))
    t1 = float(spec.get("out", 0.0)) or None
    g = spec.get("grade", {})

    inputs = ["-i", src]
    chain = []
    base = (f"[0:v]trim=start={t0}" + (f":end={t1}" if t1 else "") +
            ",setpts=PTS-STARTPTS,"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"fps={fps},setsar=1")
    sh = float(g.get("shadows", 0.0))
    hi = float(g.get("highlights", 0.0))
    sat = float(g.get("saturation", 1.0))
    if sh or hi:
        base += (f",curves=all='0/{sh:.3f} 0.5/{0.5 + sh * 0.6:.3f} "
                 f"1/{1 + hi:.3f}'")
    if sat != 1.0:
        base += f",eq=saturation={sat}"
    base += ",format=rgba[bg]"
    chain.append(base)

    cur = "[bg]"
    idx = 1
    for n, b in enumerate(spec.get("blocks", [])):
        lines = [(t, int(a)) for t, a in b["lines"]]
        size = int(b.get("size", 64))
        pos = b.get("pos", "tl")
        step = float(b.get("step", 0.28))
        start = float(b["t"])
        end = start + float(b["dur"])
        align = "right" if pos in ("tr", "br") else "left"
        # отдельная картинка на каждое состояние: 1 строка, 2 строки, ...
        for k in range(1, len(lines) + 1):
            img = draw_block(lines[:k], size, W, align)
            # блок растёт вниз, якорь держим по верхней строке
            full_h = draw_block(lines, size, W, align).size[1]
            x, y = place(pos, img.size[0], full_h, W, H)
            path = os.path.join(workdir, f"b{n}_{k}.png")
            img.save(path)
            inputs += ["-i", path]
            a = start + (k - 1) * step
            z = (start + k * step) if k < len(lines) else end
            if z <= a:
                continue
            out = f"[v{idx}]"
            chain.append(f"{cur}[{idx}:v]overlay={x}:{y}:"
                         f"enable='between(t,{a:.3f},{z:.3f})'{out}")
            cur = out
            idx += 1

    if spec.get("badge"):
        img = draw_block([(spec["badge"], 0)], 30, W)
        path = os.path.join(workdir, "badge.png")
        img.save(path)
        inputs += ["-i", path]
        chain.append(f"{cur}[{idx}:v]overlay={W - img.size[0] - 20}:20[v{idx}]")
        cur = f"[v{idx}]"
        idx += 1

    chain.append(f"{cur}format=yuv420p[vout]")

    lufs = spec.get("loudness", -14)
    atrim = f"[0:a]atrim=start={t0}" + (f":end={t1}" if t1 else "")
    # Три шага, и порядок важен. loudnorm задаёт уровень, но не сужает диапазон;
    # компрессор на тихом исходнике почти не срабатывает, пока уровень не поднят.
    # Поэтому: подняли -> сжали -> выставили итоговую громкость.
    chain.append(f"{atrim},asetpts=PTS-STARTPTS,"
                 f"loudnorm=I={lufs - 2}:TP=-2,"
                 f"acompressor=threshold=-18dB:ratio=6:attack=5:release=150:makeup=3,"
                 f"loudnorm=I={lufs}:TP=-1.0,aresample=48000[aout]")

    return (["ffmpeg", "-hide_banner", "-y"] + inputs +
            ["-filter_complex", ";".join(chain),
             "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             "-c:a", "aac", "-b:a", "256k", spec.get("output", "out.mp4")])


def main():
    p = argparse.ArgumentParser(description="Оверлеи поверх непрерывного дубля")
    p.add_argument("spec")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        cmd = build(spec, td)
        if a.dry_run:
            print(" ".join(shlex.quote(c) for c in cmd))
            return
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("ffmpeg:\n" + r.stderr[-2500:])
    print("готово:", spec.get("output", "out.mp4"))


if __name__ == "__main__":
    main()
