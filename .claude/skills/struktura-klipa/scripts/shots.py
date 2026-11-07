#!/usr/bin/env python3
"""Паспорт ролика: таблица кадров + контактный лист под разметку глазами.

Считает то, что считается машиной: границы кадров, их длины, движение по
пикселям, яркость, громкость. Графы, которые определяются только глазами
(крупность, ракурс, ИИ-риск, связь с предыдущим), остаются пустыми —
их заполняет человек или модель по контактному листу.

Работает на ffmpeg/ffprobe и PIL. Сторонних библиотек не нужно.

  python3 shots.py ref.mp4 -o razbor/ref01
  python3 shots.py ref.mp4 -o razbor/ref01 --threshold 0.18 --views 420000

Порог --threshold по умолчанию 0.30. Плавные переходы и засветки требуют
0.15-0.20, тряская камера 0.40+. ВСЕГДА сверь число кадров с контактным
листом перед тем, как считать по ним статистику.
"""
import argparse
import csv
import json
import os
import re
import statistics
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

FONT_BOLD = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FONT_REG = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
MAX_TILES = 120
SAMPLE_STEP = 0.25  # шаг выборки кривых: fps=4
GUARD = SAMPLE_STEP  # защитная зона у границ кадра

# Колонки разметки: порядок зафиксирован контрактом скилла, менять нельзя.
LABEL_COLS = ["блок", "крупность", "ракурс", "движение камеры",
              "движение в кадре", "что в кадре", "ИИ-риск",
              "связь с предыдущим", "тип склейки"]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", path])
    if r.returncode != 0:
        sys.exit(f"ffprobe не прочитал файл:\n{r.stderr.strip()}")
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s.get("codec_type") == "video"), None)
    if v is None:
        sys.exit("в файле нет видеопотока")
    num, _, den = v.get("r_frame_rate", "0/1").partition("/")
    try:
        fps = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    w, h = int(v.get("width", 0)), int(v.get("height", 0))
    dur = float(d["format"].get("duration") or v.get("duration") or 0)
    has_audio = any(s.get("codec_type") == "audio" for s in d["streams"])
    return {"fps": round(fps, 3), "width": w, "height": h,
            "duration": round(dur, 3), "has_audio": has_audio,
            "aspect": f"{w}:{h}", "vertical": h > w}


def meta(path, vf, key):
    """Кривая (время, значение) из фильтра metadata=print."""
    r = run(["ffmpeg", "-v", "error", "-i", path, "-vf", vf,
             "-an", "-f", "null", "-"])
    pairs, t = [], None
    for line in r.stdout.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(re.escape(key) + r"=([-0-9.eE+]+)", line)
        if m and t is not None:
            try:
                pairs.append((t, float(m.group(1))))
            except ValueError:
                pass
            t = None
    return pairs


def cuts(path, threshold):
    vf = (f"select='gt(scene,{threshold})',"
          "metadata=print:key=lavfi.scene_score:file=-")
    return [t for t, _ in meta(path, vf, "lavfi.scene_score")]


def curve_motion(path):
    vf = ("fps=4,tblend=all_mode=difference,signalstats,"
          "metadata=print:key=lavfi.signalstats.YAVG:file=-")
    return meta(path, vf, "lavfi.signalstats.YAVG")


def curve_bright(path):
    vf = "fps=4,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-"
    return meta(path, vf, "lavfi.signalstats.YAVG")


def loudness(path):
    r = run(["ffmpeg", "-v", "error", "-i", path, "-af",
             "ebur128=metadata=1,ametadata=print:key=lavfi.r128.M:file=-",
             "-f", "null", "-"])
    vals = [float(m.group(1)) for m in
            re.finditer(r"lavfi\.r128\.M=([-0-9.]+)", r.stdout)]
    if not vals:
        return None
    return {"peak_momentary_lufs": round(max(vals), 1),
            "mean_momentary_lufs": round(statistics.fmean(vals), 1)}


def window(pairs, a, b, drop_peak=False):
    """Среднее по кадру с отступом GUARD от обеих границ.

    Отступ обязателен для кривой движения: отсчёт, попавший на склейку,
    показывает разницу между двумя РАЗНЫМИ кадрами, а не движение внутри
    одного. Без отступа статичный кадр читается как подвижный — проверено
    на синтетике: навесной статичный кадр давал 9.8 вместо 0.0.
    """
    vals = [v for t, v in pairs if a + GUARD <= t < b - GUARD]
    if vals:
        return round(statistics.fmean(vals), 2)
    vals = [v for t, v in pairs if a <= t < b]
    if len(vals) > 1:
        if drop_peak:
            vals.remove(max(vals))
        return round(statistics.fmean(vals), 2)
    if vals:
        return round(vals[0], 2)
    if not pairs:
        return None
    mid = (a + b) / 2
    return round(min(pairs, key=lambda p: abs(p[0] - mid))[1], 2)


def build_shots(bounds, duration, min_shot):
    """Границы кадров. Детекции ближе min_shot друг к другу — вспышка,
    засветка или строб внутри кадра, а не склейка: они отбрасываются."""
    raw = sorted({round(t, 3) for t in bounds if 0.05 < t < duration - 0.05})
    kept, dropped, last = [], 0, 0.0
    for t in raw:
        if t - last >= min_shot:
            kept.append(t)
            last = t
        else:
            dropped += 1
    while kept and duration - kept[-1] < min_shot:
        kept.pop()
        dropped += 1
    edges = [0.0] + kept + [round(duration, 3)]
    shots = [{"n": i + 1, "in": edges[i], "out": edges[i + 1],
              "dur": round(edges[i + 1] - edges[i], 3)}
             for i in range(len(edges) - 1)]
    return shots, dropped


def grab(path, t, dst):
    run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path,
         "-frames:v", "1", "-q:v", "3", "-y", dst])
    return os.path.exists(dst) and os.path.getsize(dst) > 0


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def contact_sheet(path, shots, outdir, vertical):
    """Середина каждого кадра плиткой, с номером и длиной под каждой."""
    tw = 200
    th = int(tw * 16 / 9) if vertical else int(tw * 9 / 16)
    cols = 6 if vertical else 4
    bar, pad = 34, 8
    shown = shots[:MAX_TILES]
    rows = (len(shown) + cols - 1) // cols
    W = cols * (tw + pad) + pad
    H = rows * (th + bar + pad) + pad
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    f_num = font(FONT_BOLD, 17)
    f_dur = font(FONT_REG, 15)
    tmp = os.path.join(outdir, "_frame.jpg")
    for i, s in enumerate(shown):
        x = pad + (i % cols) * (tw + pad)
        y = pad + (i // cols) * (th + bar + pad)
        mid = s["in"] + s["dur"] / 2
        if grab(path, mid, tmp):
            with Image.open(tmp) as im:
                sheet.paste(im.convert("RGB").resize((tw, th)), (x, y))
        else:
            d.rectangle([x, y, x + tw, y + th], fill=(40, 40, 44))
        d.text((x + 2, y + th + 6), f"{s['n']}", font=f_num, fill=(255, 255, 255))
        d.text((x + tw - 2, y + th + 7), f"{s['dur']:.2f}s", font=f_dur,
               fill=(150, 150, 158), anchor="ra")
    if os.path.exists(tmp):
        os.remove(tmp)
    dst = os.path.join(outdir, "contact.jpg")
    sheet.save(dst, quality=88)
    return dst, len(shown)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--threshold", type=float, default=0.30)
    ap.add_argument("--min-shot", type=float, default=0.25,
                    help="кадр короче этого считается вспышкой, не склейкой")
    ap.add_argument("--views", default="неизвестно",
                    help="охват ролика, попадает в паспорт")
    ap.add_argument("--no-sheet", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.video):
        sys.exit(f"нет файла: {a.video}")
    os.makedirs(a.outdir, exist_ok=True)

    info = probe(a.video)
    if info["duration"] <= 0:
        sys.exit("нулевая длительность — файл битый или это не видео")

    shots, dropped = build_shots(cuts(a.video, a.threshold),
                                 info["duration"], a.min_shot)
    mot, bri = curve_motion(a.video), curve_bright(a.video)
    for s in shots:
        s["motion"] = window(mot, s["in"], s["out"], drop_peak=True)
        s["bright"] = window(bri, s["in"], s["out"])

    durs = [s["dur"] for s in shots]
    passport = {
        "file": os.path.basename(a.video),
        "views": a.views,
        **info,
        "threshold": a.threshold,
        "min_shot": a.min_shot,
        "flashes_dropped": dropped,
        "shots": len(shots),
        "dur_mean": round(statistics.fmean(durs), 2),
        "dur_median": round(statistics.median(durs), 2),
        "dur_min": round(min(durs), 2),
        "dur_max": round(max(durs), 2),
        "cuts_per_sec": round((len(shots) - 1) / info["duration"], 2),
        "loudness": loudness(a.video) if info["has_audio"] else None,
    }

    with open(os.path.join(a.outdir, "video.json"), "w") as fh:
        json.dump(passport, fh, ensure_ascii=False, indent=2)

    cols = ["n", "in", "out", "dur", "motion", "bright"] + LABEL_COLS
    with open(os.path.join(a.outdir, "shots.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for s in shots:
            w.writerow({k: s.get(k, "") for k in cols})

    head = ["№", "in–out", "длина", "движ.", "ярк."] + LABEL_COLS
    lines = ["| " + " | ".join(head) + " |",
             "|" + "---|" * len(head)]
    for s in shots:
        lines.append("| " + " | ".join([
            str(s["n"]), f"{s['in']:.2f}–{s['out']:.2f}", f"{s['dur']:.2f}",
            "" if s["motion"] is None else f"{s['motion']:.1f}",
            "" if s["bright"] is None else f"{s['bright']:.0f}",
        ] + [""] * len(LABEL_COLS)) + " |")
    with open(os.path.join(a.outdir, "shots.md"), "w") as fh:
        fh.write(f"# Кадры: {passport['file']}\n\n"
                 f"Порог детекции {a.threshold}, минимальный кадр "
                 f"{a.min_shot} с, отброшено вспышек: {dropped}. "
                 f"Кадров: {len(shots)}.\n\n"
                 f"`движ.` — средняя разница между кадрами внутри плана, "
                 f"0 это полная статика; отсчёты на склейках исключены. "
                 f"`ярк.` — средняя яркость, 0-255.\n\n"
                 f"Пустые графы заполняются глазами по `contact.jpg`, "
                 f"значения только из `references/slovari.md`.\n\n")
        fh.write("\n".join(lines) + "\n")

    print(json.dumps(passport, ensure_ascii=False, indent=2))
    if not a.no_sheet:
        dst, shown = contact_sheet(a.video, shots, a.outdir, info["vertical"])
        note = "" if shown == len(shots) else f" (первые {shown} из {len(shots)})"
        print(f"\nконтактный лист: {dst}{note}")
    print(f"таблица: {os.path.join(a.outdir, 'shots.md')}")
    if dropped:
        print(f"\n! отброшено детекций как вспышки: {dropped} "
              f"(короче {a.min_shot} с) — сверь по контактному листу")
    if len(shots) < 2:
        print("\n! кадр один — либо непрерывный дубль, либо порог завышен")


if __name__ == "__main__":
    main()
