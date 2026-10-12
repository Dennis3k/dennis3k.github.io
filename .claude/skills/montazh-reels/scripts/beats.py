#!/usr/bin/env python3
"""Сетка битов и скелет монтажного плана.

Примеры:
  python3 beats.py --bpm 120 --duration 30
  python3 beats.py --bpm 128 --offset 0.35 --duration 24 --step 2 --lead-frames 2
  python3 beats.py --bpm 120 --duration 30 --plan gen01.mp4 gen02.mp4 gen03.mp4 > plan.json
"""
import argparse
import json
import sys

# Лестница длин в битах: хук -> завязка -> развитие (повторяется) -> посадка
HOOK = [1, 1, 1]
SETUP = [4]
DEVELOPMENT = [2, 2, 2, 2, 4]
LANDING = [4]

BLOCK_LABELS = {"hook": "хук", "setup": "завязка", "dev": "развитие", "landing": "посадка"}


def beats_word(n):
    if n % 10 == 1 and n % 100 != 11:
        return "бит"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "бита"
    return "битов"


def ladder(total_beats):
    """Последовательность длин кадров в битах под заданное число битов."""
    steps = [("hook", b) for b in HOOK] + [("setup", b) for b in SETUP]
    used = sum(b for _, b in steps)
    reserve = sum(LANDING)
    i = 0
    while used + DEVELOPMENT[i % len(DEVELOPMENT)] + reserve <= total_beats:
        b = DEVELOPMENT[i % len(DEVELOPMENT)]
        steps.append(("dev", b))
        used += b
        i += 1
    steps += [("landing", b) for b in LANDING]
    return steps


def grid(bpm, offset, duration, step):
    beat = 60.0 / bpm
    out = []
    n = 0
    while offset + n * beat <= duration + 1e-9:
        out.append((n, offset + n * beat, n % step == 0))
        n += 1
    return out, beat


def main():
    p = argparse.ArgumentParser(description="Сетка битов и скелет монтажного плана")
    p.add_argument("--bpm", type=float, required=True, help="темп трека")
    p.add_argument("--offset", type=float, default=0.0, help="время первого бита в секундах")
    p.add_argument("--duration", type=float, default=30.0, help="длина ролика в секундах")
    p.add_argument("--step", type=int, default=2, help="склейка каждые N битов (для сетки)")
    p.add_argument("--fps", type=int, default=30, help="кадров в секунду")
    p.add_argument("--lead-frames", type=int, default=2,
                   help="предбитовое опережение склейки в кадрах")
    p.add_argument("--plan", nargs="+", metavar="FILE",
                   help="выдать JSON-скелет плана для montage.py по этим файлам")
    p.add_argument("--music", help="файл музыки для плана")
    a = p.parse_args()

    beat = 60.0 / a.bpm
    lead = a.lead_frames / a.fps

    if a.plan:
        steps = ladder(int(a.duration / beat))
        shots = []
        t = 0.0
        for i, (block, beats) in enumerate(steps):
            dur = round(beats * beat, 3)
            shots.append({
                "file": a.plan[i % len(a.plan)],
                "in": 0.5,
                "out": round(0.5 + dur, 3),
                "speed": 1.0,
                "keep_audio": False,
                "label": f"{BLOCK_LABELS[block]} / {beats} {beats_word(beats)} / начало {round(t, 2)}с",
            })
            t += dur
        plan = {
            "fps": a.fps,
            "width": 1080,
            "height": 1920,
            "output": "chernovik.mp4",
            "music": {"file": a.music or "music.mp3", "offset": 0.0, "gain_db": 0.0},
            "shots": shots,
        }
        json.dump(plan, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        print(f"\n# план на {round(t, 2)}с, {len(shots)} кадров; "
              f"in/out подогнать руками под годные интервалы генераций", file=sys.stderr)
        return

    g, beat = grid(a.bpm, a.offset, a.duration, a.step)
    print(f"BPM {a.bpm:g} | бит {beat:.3f}с | такт {4 * beat:.3f}с | "
          f"опережение {a.lead_frames} кадра = {lead:.3f}с")
    print(f"{'бит':>4} {'такт':>8} {'время':>8} {'склейка':>9} {'в CapCut':>9}")
    for n, t, is_cut in g:
        bar = f"{n // 4 + 1}.{n % 4 + 1}"
        cut = f"{t:.3f}" if is_cut else ""
        cc = f"{max(0.0, t - lead):.3f}" if is_cut else ""
        print(f"{n:>4} {bar:>8} {t:>8.3f} {cut:>9} {cc:>9}")
    print("\nСклейка ставится по колонке «в CapCut» (на 1-2 кадра раньше бита).")
    print("Исключение: дроп и главный акцент — ровно по колонке «время».")


if __name__ == "__main__":
    main()
