#!/usr/bin/env python3
"""Разбор чужого ролика: цифры вместо «динамично и ритмично».

Считает то, что потом можно повторить: монтажные события и интервалы между
ними, громкость, контактный лист кадров. Работает на ffmpeg/ffprobe,
сторонних библиотек не нужно.

Примеры:
  python3 analyze.py ref.mp4
  python3 analyze.py ref.mp4 --crop 654:370:33:270      # только часть кадра
  python3 analyze.py ref.mp4 --threshold 0.03 --every 1.5
"""
import argparse
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
             "-of", "json", path])
    if r.returncode != 0:
        sys.exit(f"ffprobe не смог прочитать файл:\n{r.stderr.strip()}")
    return json.loads(r.stdout)


def fps_of(stream):
    num, _, den = stream.get("r_frame_rate", "0/1").partition("/")
    try:
        return float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def events(path, crop, threshold, merge):
    """Времена монтажных событий; подряд идущие кадры анимации схлопываются."""
    with tempfile.TemporaryDirectory() as td:
        meta = os.path.join(td, "scenes.txt")
        chain = (f"crop={crop}," if crop else "")
        chain += f"select='gt(scene,{threshold})',metadata=print:file={meta}"
        r = run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                 "-i", path, "-filter_complex", chain, "-an", "-f", "null", "-"])
        if not os.path.exists(meta):
            if r.returncode != 0:
                sys.exit(f"ffmpeg не справился:\n{r.stderr.strip()}")
            return []
        times = [float(x) for x in
                 re.findall(r"pts_time:([\d.]+)", open(meta, encoding="utf-8").read())]
    out = []
    for t in times:
        if not out or t - out[-1] > merge:
            out.append(t)
    return out


def loudness(path):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
             "-af", "ebur128=peak=true", "-f", "null", "-"])
    # ebur128 сыплет теми же полями в каждой строке прогресса; нужен итог в конце
    txt = r.stderr
    head, sep, tail = txt.rpartition("Summary:")
    txt = tail if sep else txt

    def grab(pattern):
        found = re.findall(pattern, txt)
        return float(found[-1]) if found else None

    return {
        "I": grab(r"I:\s*(-?[\d.]+) LUFS"),
        "LRA": grab(r"LRA:\s*(-?[\d.]+) LU"),
        "peak": grab(r"Peak:\s*(-?[\d.]+) dBFS"),
    }


def sheet(path, crop, every, out_png, cols=5):
    rows = 4
    chain = (f"crop={crop}," if crop else "")
    chain += f"fps=1/{every},scale=380:-1,tile={cols}x{rows}:padding=4:color=black"
    r = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-i", path, "-vf", chain, "-frames:v", "1", out_png])
    return out_png if r.returncode == 0 and os.path.exists(out_png) else None


def main():
    p = argparse.ArgumentParser(description="Разбор ролика в цифрах")
    p.add_argument("video")
    p.add_argument("--crop", help="W:H:X:Y — считать события только в этой области "
                                  "(например, в сплит-скрине — только верхнее окно)")
    p.add_argument("--threshold", type=float, default=0.05,
                   help="порог детектора смены кадра (0.03 ловит оверлеи, 0.12 — только склейки)")
    p.add_argument("--merge", type=float, default=0.25,
                   help="события ближе этого порога считаются одной анимацией, с")
    p.add_argument("--every", type=float, default=1.5, help="шаг контактного листа, с")
    p.add_argument("--out", default=".", help="куда положить контактный лист")
    a = p.parse_args()

    if not os.path.exists(a.video):
        sys.exit(f"файл не найден: {a.video}")

    info = probe(a.video)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"].get("duration", 0))
    if not v:
        sys.exit("в файле нет видеодорожки")
    fps = fps_of(v)

    print("# ИСХОДНИК")
    print(f"  {v['width']}x{v['height']}, {fps:g} fps, {dur:.1f}с, "
          f"{int(info['format'].get('bit_rate', 0)) // 1000} кбит/с, {v['codec_name']}")
    print(f"  звук: {au['codec_name']}, {au.get('sample_rate')} Гц, "
          f"{au.get('channels')} кан." if au else "  звук: нет")

    ld = loudness(a.video)
    if ld["I"] is not None:
        verdict = "норма" if -15.5 <= ld["I"] <= -12.5 else "мимо нормы соцсетей (−14 LUFS)"
        print(f"\n# ГРОМКОСТЬ\n  интегрально {ld['I']} LUFS ({verdict}), "
              f"диапазон {ld['LRA']} LU, тру-пик {ld['peak']} dBFS")
        if ld["LRA"] is not None and ld["LRA"] < 5:
            print("  диапазон меньше 5 LU — голос сильно сжат, музыка держится ровно и тихо")

    ev = events(a.video, a.crop, a.threshold, a.merge)
    print(f"\n# СОБЫТИЯ (порог {a.threshold}{', область ' + a.crop if a.crop else ''})")
    if not ev:
        print("  ни одного — непрерывный кадр без склеек и без крупных оверлеев")
    else:
        print("  " + "  ".join(f"{t:.1f}" for t in ev))
        if len(ev) > 1:
            g = [ev[i + 1] - ev[i] for i in range(len(ev) - 1)]
            print(f"  всего {len(ev)}, в среднем каждые {dur / len(ev):.1f}с")
            print(f"  интервалы: мин {min(g):.1f}с, медиана {statistics.median(g):.1f}с, "
                  f"макс {max(g):.1f}с")
            if len(g) > 3 and statistics.pstdev(g) < 0.3:
                print("  ! интервалы почти одинаковые — ровная нарезка")
            if ev[0] > 2.5:
                print(f"  ! до {ev[0]:.1f}с детектор не увидел событий. Тонкий текст и "
                      f"мелкие оверлеи он не ловит — проверь хук глазами по листу")

    png = sheet(a.video, a.crop, a.every, os.path.join(a.out, "contact.png"))
    if png:
        print(f"\n# КОНТАКТНЫЙ ЛИСТ\n  {png} (кадр каждые {a.every:g}с) — посмотри его "
              f"глазами: текст, оверлеи, крупности")

    print("\nДальше: сверь это с эталоном в SKILL.md и references/overlay.md.")


if __name__ == "__main__":
    main()
