#!/usr/bin/env python3
"""Проверка дрожания камеры в готовой генерации.

  python3 drozhanie.py clip.mp4

Считает глобальный сдвиг между соседними кадрами (фазовая корреляция) и
печатает: средний сдвиг по секундам, высокочастотную составляющую (дрожание)
в пикселях при ширине 240 и пересчёт на 1080, кадры с самой низкой
корреляцией (резкая смена содержимого, скачок). Порог для плавного пролёта:
дрожание меньше 1 px при 1080. Требует opencv-python-headless (pip install).
"""
import sys
import cv2
import numpy as np

c = cv2.VideoCapture(sys.argv[1])
fps = c.get(cv2.CAP_PROP_FPS) or 30
prev, rows, i = None, [], 0
while True:
    ok, fr = c.read()
    if not ok:
        break
    g = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (240, 426))
    if prev is not None:
        (dx, dy), r = cv2.phaseCorrelate(np.float32(prev), np.float32(g))
        rows.append((i / fps, dx, dy, r))
    prev, i = g, i + 1
a = np.array(rows)


def jit(v):
    s = np.convolve(v, np.ones(9) / 9, "same")
    return np.std((v - s)[5:-5])


k = 1080 / 240
print(f"кадров {i}, {fps:.0f} к/с")
print(f"дрожание: dx {jit(a[:,1])*k:.2f} px, dy {jit(a[:,2])*k:.2f} px (при 1080)")
print("кадры с самой низкой корреляцией (скачки):",
      [(round(a[j, 0], 2), round(a[j, 3], 2)) for j in np.argsort(a[:, 3])[:5]])
for s in range(int(a[-1, 0]) + 1):
    m = (a[:, 0] >= s) & (a[:, 0] < s + 1)
    print(f"{s} c: dx {a[m,1].mean():+.2f} dy {a[m,2].mean():+.2f}")
