#!/usr/bin/env python3
"""audio_report.py — спектральный баланс по-слуховому (A-взвешивание) + ширина.

Доля энергии в полосе без взвешивания врёт: спектр мощности всегда
перевешен в низ, и «90% в басу» может звучать нормально, а может мутью.
A-взвешивание приближает чувствительность уха и даёт сравнимые числа.
"""
import sys, wave
import numpy as np
SR = 48000
BANDS = [(20, 120, "низ"), (120, 500, "нижсер"), (500, 2000, "сер"),
         (2000, 6000, "верхсер"), (6000, 20000, "верх")]

def read24(p):
    with wave.open(p) as f: raw = f.readframes(f.getnframes())
    b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
    v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
    return np.where(v & 0x800000, v - 0x1000000, v).reshape(-1, 2).T / 8388607.0

def a_weight(f):
    f = np.maximum(f, 1.0); f2 = f*f
    ra = (12194**2 * f2**2) / ((f2 + 20.6**2) * np.sqrt((f2 + 107.7**2)*(f2 + 737.9**2)) * (f2 + 12194**2))
    return ra * 10**(2.0/20)

def bands_of(x):
    X = np.abs(np.fft.rfft(x*np.hanning(len(x))))**2
    f = np.fft.rfftfreq(len(x), 1/SR)
    X = X * a_weight(f)**2
    t = X.sum() + 1e-20
    return [100*X[(f >= lo) & (f < hi)].sum()/t for lo, hi, _ in BANDS]

def hp(x, fc):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1/SR)
    return np.fft.irfft(X*(1 - 1/(1 + (f/fc)**4)), len(x))

def report(path, secs):
    m = read24(path); mono = m.mean(0)
    w = float(np.corrcoef(hp(m[0], 300), hp(m[1], 300))[0, 1])
    print(f"\n=== {path}   ширина (корр. >300 Гц): {w:.3f}   [1.0 = моно, 0.6–0.85 — норма]")
    print(f"{'секция':<12}{'RMS':>7}" + "".join(f"{n:>8}" for _, _, n in BANDS))
    for name, a, b in secs:
        x = mono[int(a*SR):int(b*SR)]
        if len(x) < 2048: continue
        r = 20*np.log10(np.sqrt(np.mean(x**2)) + 1e-12)
        print(f"{name:<12}{r:>7.1f}" + "".join(f"{v:>7.1f}%" for v in bands_of(x)))
    print(f"{'ЦЕЛЬ':<12}{'':>7}" + "".join(f"{v:>8}" for v in ("10–25%", "18–30%", "22–35%", "15–28%", "5–15%")))

SECS = [("интро", 0, 2.5), ("искра", 2.5, 3.5), ("дроп1", 3.5, 5.5), ("приложение", 5.5, 12),
        ("билд", 12.75, 16), ("ДРОП2", 16, 18.5), ("финал", 21, 24), ("энд-кард", 24, 26)]
for p in (sys.argv[1:] or ['out/score.wav']):
    report(p, SECS)
