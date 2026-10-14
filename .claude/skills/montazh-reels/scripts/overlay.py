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
import re
import shlex
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cards
import sfx as sfxlib

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


def silences(path, t0, t1, floor="-34dB", minlen=0.7):
    """Паузы в звуке: [(начало, конец), ...] в координатах исходника."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-ss", str(t0)] +
        (["-t", str(t1 - t0)] if t1 else []) +
        ["-i", path, "-af", f"silencedetect=noise={floor}:d={minlen}",
         "-f", "null", "-"], capture_output=True, text=True)
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    out = []
    for i, a in enumerate(starts):
        b = ends[i] if i < len(ends) else (t1 - t0 if t1 else a)
        out.append((t0 + a, t0 + b))
    return out


def keep_segments(t0, t1, gaps, pad):
    """Куски, которые остаются после вырезания пауз."""
    segs, cur = [], t0
    for a, b in gaps:
        a, b = a + pad, b - pad
        if b - a <= 0.05:
            continue
        if a > cur:
            segs.append((cur, a))
        cur = b
    if t1 > cur:
        segs.append((cur, t1))
    return segs


def remap(segs):
    """Функция: время в исходнике -> время в сжатой версии."""
    def f(t):
        acc = 0.0
        for a, b in segs:
            if t < a:
                return acc
            if t <= b:
                return acc + (t - a)
            acc += b - a
        return acc
    return f


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

    tg = spec.get("tighten")
    segs = [(t0, t1)] if t1 else []
    if tg and t1:
        gaps = silences(src, t0, t1, tg.get("floor", "-34dB"),
                        float(tg.get("min_silence", 0.7)))
        segs = keep_segments(t0, t1, gaps, float(tg.get("keep", 0.22)))
    at = remap(segs) if len(segs) > 1 else (lambda x: x - t0)

    if len(segs) > 1:
        vs, as_ = [], []
        for i, (a, b) in enumerate(segs):
            chain.append(f"[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS[tv{i}]")
            chain.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[ta{i}]")
            vs.append(f"[tv{i}]")
            as_.append(f"[ta{i}]")
        pairs = "".join(v + a for v, a in zip(vs, as_))
        chain.append(f"{pairs}concat=n={len(segs)}:v=1:a=1[cv][ca]")
        src_v, src_a = "[cv]", "[ca]"
        total = sum(b - a for a, b in segs)
    else:
        src_v, src_a = "[0:v]", "[0:a]"
        total = (t1 - t0) if t1 else None

    base = (f"{src_v}trim=start=" + ("0" if len(segs) > 1 else str(t0)) +
            (f":end={total if len(segs) > 1 else t1}" if t1 else "") +
            ",setpts=PTS-STARTPTS,"
            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
            f"fps={fps},setsar=1")

    punches = [(at(float(t)), float(sv)) for t, sv in spec.get("punch", [])]
    if punches:
        # наезд на событии: кадр подрезается и тянется обратно, затухая за ~1 с
        # через zoompan, а не crop: у crop ширина и высота считаются один раз
        # при инициализации, времени t в них нет
        z = "+".join(f"{sv}*exp(-7*(it-{pt:.3f}))*between(it,{pt:.3f},{pt + 1.1:.3f})"
                     for pt, sv in punches)
        base += (f",zoompan=z='1+{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                 f"d=1:s={W}x{H}:fps={fps}")
    sh = float(g.get("shadows", 0.0))
    hi = float(g.get("highlights", 0.0))
    sat = float(g.get("saturation", 1.0))
    if sh or hi:
        base += (f",curves=all='0/{sh:.3f} 0.5/{0.5 + sh * 0.6:.3f} "
                 f"1/{1 + hi:.3f}'")
    if sat != 1.0:
        base += f",eq=saturation={sat}"
    light = spec.get("light") or []
    if light:
        terms = "+".join(f"(between(t,{at(a):.3f},{at(b):.3f})*{v})"
                         for a, b, v in light)
        base += f",eq=eval=frame:brightness='{terms}'"
    base += ",format=rgba[bg]"
    chain.append(base)

    cur = "[bg]"
    idx = 1
    for n, b in enumerate(spec.get("blocks", [])):
        lines = [(t, int(a)) for t, a in b["lines"]]
        size = int(b.get("size", 64))
        pos = b.get("pos", "tl")
        step = float(b.get("step", 0.28))
        start = at(float(b["t"]))
        end = at(float(b["t"]) + float(b["dur"]))
        align = "right" if pos in ("tr", "br") else "left"
        # отдельная картинка на каждое состояние: 1 строка, 2 строки, ...
        for k in range(1, len(lines) + 1):
            a = start + (k - 1) * step
            z = (start + k * step) if k < len(lines) else end
            # окно состояния схлопнулось (блок попал в вырезанную паузу) —
            # пропускаем до того, как заводить вход, иначе номера входов
            # разъедутся с номерами в графе
            if z <= a:
                continue
            img = draw_block(lines[:k], size, W, align)
            # блок растёт вниз, якорь держим по верхней строке
            full_h = draw_block(lines, size, W, align).size[1]
            x, y = place(pos, img.size[0], full_h, W, H)
            path = os.path.join(workdir, f"b{n}_{k}.png")
            img.save(path)
            inputs += ["-i", path]
            out = f"[v{idx}]"
            chain.append(f"{cur}[{idx}:v]overlay={x}:{y}:"
                         f"enable='between(t,{a:.3f},{z:.3f})'{out}")
            cur = out
            idx += 1

    for n, w in enumerate(spec.get("widgets", [])):
        render = cards.RENDERERS.get(w["type"])
        if render is None:
            sys.exit(f"неизвестный виджет: {w['type']}")
        t = at(float(w["t"]))
        dur = max(0.4, at(float(w["t"]) + float(w["dur"])) - t)
        frames = max(2, int(dur * fps))
        wd = os.path.join(workdir, f"w{n}")
        os.makedirs(wd, exist_ok=True)
        size = None
        for k in range(frames):
            im = render(w, k / (frames - 1))
            im.save(os.path.join(wd, f"{k:05d}.png"))
            size = im.size
        x = w.get("x")
        y = w.get("y")
        if x is None or y is None:
            x, y = place(w.get("pos", "tr"), size[0], size[1], W, H)
        inputs += ["-framerate", str(fps), "-start_number", "0",
                   "-i", os.path.join(wd, "%05d.png")]
        chain.append(f"[{idx}:v]setpts=PTS+{t}/TB[w{idx}]")
        out = f"[v{idx}]"
        chain.append(f"{cur}[w{idx}]overlay={x}:{y}:"
                     f"enable='between(t,{t},{t + dur:.3f})'{out}")
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
    atrim = (f"{src_a}atrim=start=0:end={total}" if len(segs) > 1
             else f"[0:a]atrim=start={t0}" + (f":end={t1}" if t1 else ""))
    # Три шага, и порядок важен. loudnorm задаёт уровень, но не сужает диапазон;
    # компрессор на тихом исходнике почти не срабатывает, пока уровень не поднят.
    # Поэтому: подняли -> сжали -> выставили итоговую громкость.
    chain.append(f"{atrim},asetpts=PTS-STARTPTS,"
                 f"loudnorm=I={lufs - 2}:TP=-2,"
                 f"acompressor=threshold=-18dB:ratio=6:attack=5:release=150:makeup=3,"
                 f"loudnorm=I={lufs}:TP=-1.0,aresample=48000[voice]")

    hits = spec.get("sfx") or []
    music = spec.get("music")
    mixin = ["[voice]"]
    for n, h in enumerate(hits):
        kind = h.get("kind", "whoosh")
        if kind not in sfxlib.KINDS:
            sys.exit(f"нет такого звука: {kind}")
        wav = os.path.join(workdir, f"sfx{n}.wav")
        sfxlib.write_wav(wav, sfxlib.KINDS[kind]())
        inputs += ["-i", wav]
        ms = int(max(0.0, at(float(h["t"]))) * 1000)
        chain.append(f"[{idx}:a]aformat=channel_layouts=stereo,"
                     f"adelay={ms}|{ms},volume={h.get('gain_db', -6)}dB[s{idx}]")
        mixin.append(f"[s{idx}]")
        idx += 1
    bedspec = spec.get("bed")
    if bedspec and total:
        wav = os.path.join(workdir, "bed.wav")
        sfxlib.write_wav(wav, sfxlib.bed(total + 0.5,
                                         bpm=float(bedspec.get("bpm", 104)),
                                         key=float(bedspec.get("key", 55.0))))
        inputs += ["-i", wav]
        chain.append(f"[{idx}:a]aformat=channel_layouts=stereo,"
                     f"volume={bedspec.get('gain_db', -20)}dB,"
                     f"afade=t=in:st=0:d=0.8,"
                     f"afade=t=out:st={max(0.0, total - 1.5):.2f}:d=1.5[bed]")
        mixin.append("[bed]")
        idx += 1
    if music and os.path.exists(music.get("file", "")):
        inputs += ["-i", music["file"]]
        chain.append(f"[{idx}:a]volume={music.get('gain_db', -17)}dB,"
                     f"afade=t=out:st={max(0.0, (total or 10) - 1.2):.2f}:d=1.2[mus]")
        mixin.append("[mus]")
        idx += 1
    if len(mixin) > 1:
        chain.append("".join(mixin) +
                     f"amix=inputs={len(mixin)}:duration=first:normalize=0,"
                     f"alimiter=limit=0.85:level=disabled[aout]")
    else:
        chain.append("[voice]anull[aout]")

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
