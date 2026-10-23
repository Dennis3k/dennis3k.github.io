#!/usr/bin/env python3
"""sfx_prep.py — готовит присланные файлы под слоты.

Сырые файлы лежат в assets/sfx/_inbox и не трогаются. Отсюда они приводятся
к 48 кГц, обрезаются по длине и нормализуются, и кладутся рядом под именами
слотов. Скрипт можно гонять сколько угодно: он всегда пересобирает из сырья.

Почему обрезка нужна именно такая:
  • удар с 20-секундным хвостом наедет на три следующие сцены;
  • райзер и реверс-вуш ровняются по КОНЦУ — их кульминация должна прийтись
    на удар, поэтому берётся хвост нужной длины, а не начало;
  • вуш живёт вокруг своего пика, поэтому из длинного берётся окно у пика.
"""
import os, subprocess, sys
import numpy as np

SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, 'assets', 'sfx', '_inbox')
OUT = os.path.join(ROOT, 'assets', 'sfx')

def decode(path):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'],
                       capture_output=True)
    if r.returncode: raise RuntimeError(f'{path}: {r.stderr.decode()[:160]}')
    return np.frombuffer(r.stdout, dtype='<f4').astype(np.float64)

def trim_silence(x, db=-45.0):
    thr = 10**(db/20)*max(np.max(np.abs(x)), 1e-9)
    i = int(np.argmax(np.abs(x) > thr))
    return x[max(0, i - int(0.002*SR)):]

def fade_in(x, d):  n = min(int(d*SR), len(x)); x[:n] *= np.linspace(0, 1, n); return x
def fade_out(x, d): n = min(int(d*SR), len(x)); x[-n:] *= np.linspace(1, 0, n); return x

def head(x, dur, fo=0.4):
    """начало длиной dur с затуханием в конце — для ударов с длинным хвостом"""
    y = x[:int(dur*SR)].copy()
    return fade_out(y, min(fo, dur*0.5))

def tail(x, dur, fi=0.08):
    """хвост длиной dur — для райзеров и реверсов, которые ровняются по концу"""
    y = x[-int(dur*SR):].copy()
    return fade_in(y, fi)

def peak_window(x, before, after):
    """окно вокруг пика — для вушей, у которых интересна только середина"""
    p = int(np.argmax(np.abs(x)))
    a, b = max(0, p - int(before*SR)), min(len(x), p + int(after*SR))
    y = x[a:b].copy()
    return fade_out(fade_in(y, 0.02), 0.08)

def respeed(x, k):
    """смена скорости = смена высоты. Выше и короче — то, что нужно слэмам"""
    n = int(len(x)/k)
    return np.interp(np.linspace(0, len(x)-1, n), np.arange(len(x)), x)

def _spec(x, fn):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1/SR)
    return np.fft.irfft(X*fn(f), len(x))

def peak_eq(x, fc, db, q=1.0):
    """колокол в логарифмической шкале — разгрузить забитую полосу сэмпла"""
    g = 10**(db/20); sg = 1/(2*q)
    return _spec(x, lambda f: 1.0 + (g-1)*np.exp(-(np.log2(np.maximum(f, 1.0)/fc)**2)/(2*sg*sg)))

def shelf_hi_eq(x, fc, db):
    g = 10**(db/20)
    return _spec(x, lambda f: 1.0 + (g-1)/(1.0 + (fc/np.maximum(f, 1.0))**2))

def norm(x, peak=0.9):
    return x/max(np.max(np.abs(x)), 1e-9)*peak

def write(name, x):
    x = norm(x)
    path = os.path.join(OUT, name + '.wav')
    p = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1',
                        '-i', '-', '-c:a', 'pcm_s24le', path], input=x.astype('<f4').tobytes(),
                       capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode()[:160])
    print(f'  {name:<13} {len(x)/SR:5.2f} с')

def find(frag):
    for fn in sorted(os.listdir(INBOX)):
        if frag in fn: return os.path.join(INBOX, fn)
    return None

SRC = {
    'impact_big':  ('black_kumizhi',      lambda x: peak_eq(head(x, 2.60, 0.80), 250, -5.0, 0.9)),
    'impact_mid':  ('universfield',       lambda x: peak_eq(head(x, 2.00, 0.50), 240, -3.0, 0.9)),
    'impact_soft': ('universfield',       lambda x: norm(head(respeed(x, 1.35), 0.85, 0.30), 0.62)),
    'sub_drop':    ('djartmusic',         lambda x: head(x, 1.70, 0.45)),
    'riser_build': ('soundreality',       lambda x: tail(x, 3.30, 0.25)),
    'suck':        ('sdanezis',           lambda x: tail(x, 2.00, 0.12)),
    'whoosh_long': ('lordsonny',          lambda x: shelf_hi_eq(head(x, 2.20, 0.55), 7000, -3.5)),
    'whoosh_short':('dragon-studio',      lambda x: peak_window(x, 0.26, 0.46)),
    'crash_rev':   ('freesound_community',lambda x: tail(x, 2.40, 0.20)),
    # четыре удара хука выведены из одного: выше и короче — читается как другой удар
    'slam_1':      ('universfield',       lambda x: norm(head(respeed(x, 1.18), 1.15, 0.45), 0.90)),
    'slam_2':      ('universfield',       lambda x: norm(head(respeed(x, 1.46), 0.80, 0.30), 0.74)),
    'slam_3':      ('universfield',       lambda x: norm(head(respeed(x, 1.62), 0.72, 0.26), 0.70)),
    'slam_4':      ('universfield',       lambda x: norm(head(respeed(x, 1.34), 0.95, 0.38), 0.80)),
}

if __name__ == '__main__':
    if not os.path.isdir(INBOX): sys.exit(f'нет папки {INBOX}')
    print('готовлю слоты из', INBOX)
    cache = {}
    for slot, (frag, fn) in SRC.items():
        p = find(frag)
        if not p:
            print(f'  {slot:<13} — сырья нет, остаётся синтез'); continue
        if p not in cache: cache[p] = trim_silence(decode(p))
        write(slot, fn(cache[p].copy()))
