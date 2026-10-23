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

def cut_keys(path, times, dur=0.17):
    """Из записи набора вынимаются отдельные нажатия. Целиком её использовать
    нельзя: там 55 ударов за 22 с в своём ритме, а печать в ролике идёт по
    карте тайминга."""
    x = decode(path)
    for i, t in enumerate(times, 1):
        a = max(0, int((t - 0.02)*SR))
        y = x[a:a + int(dur*SR)].copy()
        y = fade_out(fade_in(y, 0.002), 0.06)
        write(f'key_{i}', y)

def prep_bed(path, out_name='music_bed.wav'):
    """Фоновый трек режется на два куска так, чтобы его собственный дроп
    дважды пришёлся на дропы ролика — на 3.62 и на 16.15. Шов на 12.75
    прикрыт вушем и белой вспышкой, и просадка энергии там по монтажу нужна."""
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ar', str(SR), '-ac', '2', '-f', 'f32le', '-'],
                       capture_output=True)
    st = np.frombuffer(r.stdout, dtype='<f4').astype(np.float64).reshape(-1, 2).T
    TRACK_DROP = 10.293        # измерено по спектральному потоку
    FILM = 26.0
    n = int(FILM*SR)
    out = np.zeros((2, n))
    k = int(0.07*SR)                      # перекрытие на шве
    def grab(film_a, film_b, drop_at, fi=0, fo=0):
        """кусок трека, посаженный так, чтобы его дроп попал на drop_at"""
        off = drop_at - TRACK_DROP
        a, b = int(film_a*SR), int(film_b*SR)
        sa = max(0, int((film_a - off)*SR))
        seg = st[:, sa:sa + (b - a)].copy()
        if seg.shape[1] < b - a:
            seg = np.pad(seg, ((0, 0), (0, b - a - seg.shape[1])))
        if fi: seg[:, :fi] *= np.linspace(0, 1, fi)[None, :]
        if fo: seg[:, -fo:] *= np.linspace(1, 0, fo)[None, :]
        return a, seg
    c = int(12.75*SR)
    # куски перекрываются на 70 мс и складываются — настоящий кроссфейд,
    # а не две встречные затухалки, между которыми была бы дыра
    a1, s1 = grab(0.0, 12.75 + 0.07, 3.62, fo=k)
    a2, s2 = grab(12.75 - 0.07, FILM, 16.15, fi=k)
    out[:, a1:a1+s1.shape[1]] += s1[:, :n-a1]
    out[:, a2:a2+s2.shape[1]] += s2[:, :n-a2]
    # энд-кард: трек уводится, разрешение даёт синтезированный аккорд
    f0, f1 = int(23.9*SR), int(25.6*SR)
    out[:, f0:f1] *= np.linspace(1, 0, f1-f0)[None, :]
    out[:, f1:] = 0
    out[:, :int(0.05*SR)] *= np.linspace(0, 1, int(0.05*SR))
    out = out/max(np.max(np.abs(out)), 1e-9)*0.9
    path_out = os.path.join(OUT, out_name)
    p = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '2',
                        '-i', '-', '-c:a', 'pcm_s24le', path_out],
                       input=out.T.astype('<f4').tobytes(), capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode()[:160])
    print(f'  music_bed     {out.shape[1]/SR:5.2f} с  (дроп трека посажен на 3.62 и 16.15)')

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
    kp = find('typing')
    if kp: cut_keys(kp, [0.97, 1.57, 2.13, 2.67, 3.06, 3.67])
    bp = find('Glass_Horizon')
    if bp: prep_bed(bp)
