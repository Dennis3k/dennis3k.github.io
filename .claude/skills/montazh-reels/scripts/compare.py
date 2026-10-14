#!/usr/bin/env python3
"""Раскладка «до/после»: смонтированная версия сверху, исходник снизу.

Формат демо-роликов про монтаж: зритель видит, что именно сделано, потому что
исходник идёт синхронно под результатом. Обе версии должны быть одной длины
и порезаны одинаково — собирай их overlay.py из одного спека, у «до» просто
выключены оверлеи.

  python3 compare.py after.mp4 before.mp4 -o out.mp4 --title "Ai-CLIP" --label "оригинал"
"""
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"


def probe_size(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    w, h = r.stdout.strip().split(",")
    return int(w), int(h)


def backdrop(W, H, title, label, box, gap_label_y, path):
    """Фон и подписи одной картинкой: синий градиент, как в демо-форматах."""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line((0, y, W, y), fill=(int(3 + 22 * t), int(8 + 64 * t), int(36 + 196 * t)))
    # мягкое пятно света справа внизу
    glow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(glow).ellipse((W * 0.45, H * 0.7, W * 1.4, H * 1.3), fill=90)
    img = Image.composite(Image.new("RGB", (W, H), (60, 120, 255)), img,
                          glow.filter(__import__("PIL.ImageFilter", fromlist=["x"])
                                      .GaussianBlur(120)))
    d = ImageDraw.Draw(img)
    tf = ImageFont.truetype(FONT, 92)
    tw = d.textlength(title, font=tf)
    d.text(((W - tw) / 2, box[1] - 130), title, font=tf, fill=(255, 255, 255))
    lf = ImageFont.truetype(FONT, 66)
    lw = d.textlength(label, font=lf)
    d.text(((W - lw) / 2, gap_label_y), label, font=lf, fill=(255, 255, 255))
    img.save(path)


def main():
    ap = argparse.ArgumentParser(description="До/после в одном вертикальном кадре")
    ap.add_argument("after")
    ap.add_argument("before")
    ap.add_argument("-o", "--output", default="compare.mp4")
    ap.add_argument("--title", default="ПОСЛЕ")
    ap.add_argument("--label", default="оригинал")
    ap.add_argument("--top", type=int, default=320, help="верх окна «после», px")
    a = ap.parse_args()

    for f in (a.after, a.before):
        if not os.path.exists(f):
            sys.exit(f"нет файла: {f}")
    bw, bh = probe_size(a.after)
    W, H = 1080, 1920
    x = (W - bw) // 2
    y1 = a.top
    label_y = y1 + bh + 18
    y2 = label_y + 84
    if y2 + bh > H:
        sys.exit(f"окна {bw}x{bh} не помещаются в 1920 по высоте — уменьши их")

    with tempfile.TemporaryDirectory() as td:
        bg = os.path.join(td, "bg.png")
        backdrop(W, H, a.title, a.label, (x, y1), label_y, bg)
        cmd = ["ffmpeg", "-hide_banner", "-y", "-loop", "1", "-i", bg,
               "-i", a.after, "-i", a.before,
               "-filter_complex",
               f"[0:v]format=yuv420p[bg];"
               f"[2:v]scale={bw}:{bh},setsar=1[b];"
               f"[bg][1:v]overlay={x}:{y1}:shortest=1[t];"
               f"[t][b]overlay={x}:{y2}:shortest=1,format=yuv420p[v]",
               "-map", "[v]", "-map", "1:a",
               "-c:v", "libx264", "-preset", "medium", "-crf", "19",
               "-c:a", "copy", "-movflags", "+faststart", "-shortest", a.output]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("ffmpeg:\n" + r.stderr[-2000:])
    print("готово:", a.output)


if __name__ == "__main__":
    main()
