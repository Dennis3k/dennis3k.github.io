#!/usr/bin/env python3
"""Сборка чернового монтажа из JSON-плана через ffmpeg.

Черновик нужен, чтобы услышать ритм до того, как вкладываться в CapCut.
Ни титров, ни цвета, ни эффектов — только порядок, длины и музыка.

Пример плана (plan.json):

{
  "fps": 30,
  "width": 1080,
  "height": 1920,
  "output": "chernovik.mp4",
  "music": {"file": "track.mp3", "offset": 0.0, "gain_db": 0.0},
  "shots": [
    {"file": "gen01.mp4", "in": 0.6, "out": 1.8, "label": "хук"},
    {"file": "gen02.mp4", "in": 1.2, "dur": 0.5, "speed": 2.0},
    {"file": "gen03.mp4", "in": 0.4, "out": 2.9, "keep_audio": true}
  ]
}

Запуск:
  python3 montage.py plan.json
  python3 montage.py plan.json --dry-run      # только таблица и команда
  python3 montage.py plan.json -o другой.mp4
"""
import argparse
import json
import os
import shlex
import subprocess
import sys


def have_audio(path):
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=60)
        return "audio" in r.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def shot_bounds(shot, idx):
    start = float(shot.get("in", 0.0))
    if "out" in shot:
        end = float(shot["out"])
    elif "dur" in shot:
        end = start + float(shot["dur"])
    else:
        sys.exit(f"кадр {idx + 1}: нужен «out» или «dur»")
    if end <= start:
        sys.exit(f"кадр {idx + 1}: out ({end}) должен быть больше in ({start})")
    return start, end


def build(plan, output):
    fps = int(plan.get("fps", 30))
    w = int(plan.get("width", 1080))
    h = int(plan.get("height", 1920))
    shots = plan.get("shots") or sys.exit("в плане нет кадров («shots»)")
    music = plan.get("music") or {}

    inputs, filters, vlabels, alabels = [], [], [], []
    rows, total = [], 0.0

    for i, shot in enumerate(shots):
        path = shot["file"]
        if not os.path.exists(path):
            sys.exit(f"кадр {i + 1}: файл не найден: {path}")
        start, end = shot_bounds(shot, i)
        speed = float(shot.get("speed", 1.0))
        if speed <= 0:
            sys.exit(f"кадр {i + 1}: speed должен быть больше нуля")
        dur = (end - start) / speed
        keep = bool(shot.get("keep_audio", False)) and have_audio(path)

        inputs += ["-i", path]
        v = (f"[{i}:v]trim=start={start}:end={end},setpts=PTS-STARTPTS"
             f"{f',setpts=PTS/{speed}' if speed != 1.0 else ''},"
             f"scale={w}:{h}:force_original_aspect_ratio=increase,"
             f"crop={w}:{h},fps={fps},setsar=1,format=yuv420p[v{i}]")
        filters.append(v)
        vlabels.append(f"[v{i}]")

        if keep:
            a = f"[{i}:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS"
            if speed != 1.0:
                # atempo держит 0.5-2.0, цепочкой покрываем остальное
                left, chain = speed, []
                while left > 2.0:
                    chain.append(2.0)
                    left /= 2.0
                while left < 0.5:
                    chain.append(0.5)
                    left /= 0.5
                chain.append(left)
                a += "," + ",".join(f"atempo={c}" for c in chain)
            a += f",aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{i}]"
        else:
            a = (f"anullsrc=channel_layout=stereo:sample_rate=48000,"
                 f"atrim=duration={dur:.4f},asetpts=PTS-STARTPTS[a{i}]")
        filters.append(a)
        alabels.append(f"[a{i}]")

        rows.append((i + 1, os.path.basename(path), start, end, speed, dur, total,
                     shot.get("label", ""), keep))
        total += dur

    pairs = "".join(v + a for v, a in zip(vlabels, alabels))
    filters.append(f"{pairs}concat=n={len(shots)}:v=1:a=1[vcat][acat]")

    music_file = music.get("file")
    has_music = bool(music_file) and os.path.exists(music_file)
    if music_file and not has_music:
        print(f"! музыка не найдена, собираю без неё: {music_file}", file=sys.stderr)

    if has_music:
        mi = len(shots)
        inputs += ["-i", music_file]
        off = float(music.get("offset", 0.0))
        gain = float(music.get("gain_db", 0.0))
        fade = min(0.4, total / 4)
        filters.append(
            f"[{mi}:a]atrim=start={off}:end={off + total:.4f},asetpts=PTS-STARTPTS,"
            f"aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={gain}dB,afade=t=out:st={max(0.0, total - fade):.4f}:d={fade:.4f}[mus]")
        filters.append("[acat][mus]amix=inputs=2:duration=first:normalize=0[aout]")
        amap = "[aout]"
    else:
        amap = "[acat]"

    cmd = (["ffmpeg", "-hide_banner", "-y"] + inputs +
           ["-filter_complex", ";".join(filters),
            "-map", "[vcat]", "-map", amap,
            "-t", f"{total:.4f}",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
            output])
    return cmd, rows, total


def report(rows, total, fps):
    print(f"{'#':>3} {'файл':<24} {'in':>7} {'out':>7} {'x':>4} "
          f"{'длина':>7} {'на тайм.':>9}  метка")
    for n, name, start, end, speed, dur, at, label, keep in rows:
        mark = " (+звук)" if keep else ""
        print(f"{n:>3} {name[:24]:<24} {start:>7.2f} {end:>7.2f} {speed:>4g} "
              f"{dur:>7.2f} {at:>9.2f}  {label}{mark}")
    print(f"\nвсего {total:.2f}с, {len(rows)} кадров, {fps} fps")
    short = [r[0] for r in rows if r[5] < 0.3]
    if short:
        print(f"! кадры короче 0.3с (не прочитаются): {', '.join(map(str, short))}")
    lengths = [r[5] for r in rows]
    if len(lengths) > 3 and max(lengths) - min(lengths) < 0.3:
        print("! все кадры почти одной длины — ровная нарезка, см. references/ritm.md")


def main():
    p = argparse.ArgumentParser(description="Черновой монтаж из JSON-плана")
    p.add_argument("plan", help="файл плана (JSON)")
    p.add_argument("-o", "--output", help="переопределить выходной файл")
    p.add_argument("--dry-run", action="store_true", help="не рендерить, только показать")
    a = p.parse_args()

    with open(a.plan, encoding="utf-8") as f:
        plan = json.load(f)
    output = a.output or plan.get("output") or "chernovik.mp4"
    cmd, rows, total = build(plan, output)

    report(rows, total, int(plan.get("fps", 30)))
    if a.dry_run:
        print("\n" + " ".join(shlex.quote(c) for c in cmd))
        return
    print(f"\nрендер -> {output}")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"ffmpeg вернул {r.returncode}")
    print(f"готово: {output}\nТеперь посмотри целиком со звуком, потом на 2× без картинки.")


if __name__ == "__main__":
    main()
