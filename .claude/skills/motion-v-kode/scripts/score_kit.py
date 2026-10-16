#!/usr/bin/env python3
"""score_kit.py — примитивы для саундтрека, написанного кодом.

Библиотека, а не готовый трек: аранжировка пишется под конкретный ролик,
а здесь лежит всё, что иначе придётся изобретать заново — генераторы,
фильтры, мастер-тракт, измеритель громкости и экспорт стемов.

    from score_kit import *
    S = Session(dur=26.0)
    S.place('music', sub_hit(), at=3.62, gain=1.1)
    S.place('sfx',   impact(),  at=3.62, gain=1.0)
    S.duck([('All', 16.15), ('answered.', 16.45)], db=-9)
    S.master(target_lufs=-14.0, ceiling_db=-1.0)
    S.write('out/score.wav', stems=True)
"""
import math
import wave
import numpy as np

SR = 48000
rng = np.random.default_rng(7)

# ── огибающие ──────────────────────────────────────────────────────────────
def exp_env(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))

def adsr(dur, a=0.005, d=0.1, s=0.6, r=0.2, n=None):
    n = n or int(dur * SR)
    out = np.zeros(n); ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    si = max(0, n - ai - di - ri); i = 0
    if ai: out[i:i+ai] = np.linspace(0, 1, ai); i += ai
    if di: out[i:i+di] = np.linspace(1, s, di); i += di
    if si: out[i:i+si] = s; i += si
    if ri: out[i:i+ri] = np.linspace(out[max(i-1, 0)], 0, min(ri, n - i))
    return out[:n]

# ── фильтры ────────────────────────────────────────────────────────────────
def biquad(x, b, a):
    """прямая форма I. Питоновский цикл — используй только на коротких кусках
    и в K-взвешивании; для длинных сигналов бери fft_lowpass."""
    y = np.zeros_like(x); x1 = x2 = y1 = y2 = 0.0
    b0, b1, b2 = b; a0, a1, a2 = a
    b0, b1, b2, a1, a2 = b0/a0, b1/a0, b2/a0, a1/a0, a2/a0
    for i in range(len(x)):
        xi = x[i]; yi = b0*xi + b1*x1 + b2*x2 - a1*y1 - a2*y2
        x2, x1 = x1, xi; y2, y1 = y1, yi; y[i] = yi
    return y

def fft_lowpass(x, fc):
    """ФНЧ 4-го порядка с нулевой фазой — быстрый, для длинных сигналов"""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1.0 / (1.0 + (f / max(fc, 20.0)) ** 4)
    return np.fft.irfft(X, len(x))

# ── генераторы ─────────────────────────────────────────────────────────────
def noise(n): return rng.standard_normal(n)

def sine(f, n, phase=0.0): return np.sin(2*np.pi*f*np.arange(n)/SR + phase)

def saw(f, n, parts=14):
    o = np.zeros(n); k = np.arange(n)/SR
    for h in range(1, parts+1):
        if f*h > SR*0.45: break
        o += np.sin(2*np.pi*f*h*k)/h
    return o*0.55

def sweep_sine(f0, f1, n, curve=2.0):
    k = np.arange(n)/SR; T = n/SR
    f = f0 + (f1-f0)*(k/T)**curve
    return np.sin(2*np.pi*np.cumsum(f)/SR)

def hz(semi, base=146.83):       # base = D3
    return base * 2**(semi/12)

# ── звуки ──────────────────────────────────────────────────────────────────
def sub_hit(f0=62, f1=30, dur=0.6, drive=1.6):
    n = int(dur*SR)
    s = sweep_sine(f0, f1, n, 0.55) * exp_env(n, dur*0.30)
    return np.tanh(s*drive)/np.tanh(drive)

def impact(dur=0.5, tone=180, bright=1.0):
    n = int(dur*SR)
    nz = fft_lowpass(noise(n)*exp_env(n, 0.045), 2600*bright)
    bod = sine(tone, n)*exp_env(n, 0.10)*0.6
    cn = int(0.008*SR)
    cl = np.pad(noise(cn)*np.linspace(1, 0, cn), (0, n-cn))
    return (nz*0.8 + bod + cl*0.5)*0.9

def suck(dur=0.28):
    """ставится ДО удара: нарастающий шум, который удар обрывает"""
    n = int(dur*SR)
    return fft_lowpass(noise(n)*np.linspace(0, 1, n)**2.2, 6000)*np.linspace(0.2, 1.0, n)*0.5

def whoosh(dur=0.5, bright=3000):
    n = int(dur*SR)
    return fft_lowpass(noise(n), bright)*np.sin(np.linspace(0, np.pi, n))**1.6*0.5

def tick(dur=0.05, f=2400):
    n = int(dur*SR)
    return (sine(f, n)*0.6 + noise(n)*0.4)*exp_env(n, 0.006)

def click(dur=0.12, f=1200):
    n = int(dur*SR)
    return (sine(f, n) + sine(f*1.5, n)*0.4)*exp_env(n, 0.018)*0.7

def bell(f, dur=2.4):
    n = int(dur*SR); o = np.zeros(n)
    for h, g, dec in ((1, 1.0, 1.0), (2.01, .5, .6), (3.02, .3, .4), (4.4, .18, .25), (6.8, .1, .18)):
        o += sine(f*h, n)*exp_env(n, dur*0.33*dec)*g
    return o*0.35

def pad(semis, dur, base=146.83, detune=0.12, cut=900):
    n = int(dur*SR); o = np.zeros(n)
    for s in semis:
        f = hz(s, base)
        o += saw(f*(1-detune/100), n) + saw(f*(1+detune/100), n)
    return fft_lowpass(o/max(1, len(semis)*2), cut)*adsr(dur, 0.25, 0.3, 0.85, 0.6, n)

def stab(semis, dur=0.9, base=146.83, cut=4200):
    n = int(dur*SR); o = np.zeros(n)
    for s in semis:
        f = hz(s, base)
        o += saw(f, n)*0.7 + saw(f*1.004, n)*0.7 + sine(f*2, n)*0.25
    return fft_lowpass(o/(len(semis)*1.6), cut)*exp_env(n, dur*0.22)

def pluck(semi, dur=0.35, base=146.83):
    n = int(dur*SR); f = hz(semi, base)
    return fft_lowpass(saw(f, n, 10)*0.6 + sine(f*2, n)*0.3, 3200)*exp_env(n, dur*0.18)*0.8

def kick(dur=0.42):
    n = int(dur*SR); cn = int(0.004*SR)
    s = sweep_sine(140, 46, n, 0.35)*exp_env(n, 0.09)
    s += np.pad(noise(cn)*np.linspace(1, 0, cn), (0, n-cn))*0.35
    return np.tanh(s*1.4)*0.9

def hat(dur=0.09, bright=9000):
    n = int(dur*SR); s = noise(n)
    return (s - fft_lowpass(s, bright*0.5))*exp_env(n, 0.012)*0.35

def riser(dur, f0=120, f1=5200, gain=0.4):
    n = int(dur*SR); s = noise(n)
    lo, hi = fft_lowpass(s, f0*4), fft_lowpass(s, f1)
    k = np.linspace(0, 1, n)**1.8
    o = lo*(1-k) + hi*k
    return (o*k**1.2 + sweep_sine(f0, f1*0.35, n, 2.4)*k*0.25)*gain

def plate(x, mix=0.22):
    """короткая пластина из гребёнки задержек — дешевле свёртки и достаточно"""
    taps = [(.0231, .80), (.0411, .72), (.0601, .64), (.0893, .55),
            (.1237, .46), (.1699, .36), (.2311, .26), (.3137, .18)]
    out = np.zeros_like(x)
    for d, g in taps:
        i = int(d*SR); out[i:] += x[:len(x)-i]*g
    return x*(1-mix) + fft_lowpass(out, 5200)*mix*0.5

# ── динамика: обе функции возвращают КРИВУЮ УСИЛЕНИЯ, не звук ─────────────
def compress(x, thr_db=-22.0, ratio=3.2, atk=0.012, rel=0.180, makeup_db=3.0, B=64):
    n = x.shape[1]; pad_n = (-n) % B
    env = np.pad(np.abs(x).max(axis=0), (0, pad_n)).reshape(-1, B).max(axis=1)
    gr = -np.maximum(0.0, 20*np.log10(np.maximum(env, 1e-9)) - thr_db)*(1 - 1/ratio)
    aa, ar = math.exp(-B/(atk*SR)), math.exp(-B/(rel*SR))
    sm = np.empty_like(gr); cur = 0.0
    for i in range(len(gr)):
        c = aa if gr[i] < cur else ar
        cur = c*cur + (1-c)*gr[i]; sm[i] = cur
    g = 10**((sm + makeup_db)/20)
    return np.interp(np.arange(n), np.arange(len(g))*B + B/2, g)

def limiter(x, ceiling, look=0.006, rel=0.090, B=64):
    n = x.shape[1]; pad_n = (-n) % B
    xb = np.pad(np.abs(x).max(axis=0), (0, pad_n)).reshape(-1, B).max(axis=1)
    w = max(2, int(look*SR/B))
    sl = np.lib.stride_tricks.sliding_window_view(np.pad(xb, (w, w), mode='edge'), 2*w+1).max(axis=1)[:len(xb)]
    g = np.minimum(1.0, ceiling/np.maximum(sl, 1e-9))
    a = math.exp(-B/(rel*SR))
    out = np.empty_like(g); cur = 1.0
    for i in range(len(g)):
        cur = g[i] if g[i] < cur else a*cur + (1-a)*g[i]
        out[i] = cur
    return np.interp(np.arange(n), np.arange(len(out))*B + B/2, out)

# ── измерения ──────────────────────────────────────────────────────────────
def lufs(stereo):
    """BS.1770: предфильтр + RLB, блоки 400 мс, гейтинг −70 и −10 отн."""
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, -1.99004745483398, 0.99007225036621]
    ks = [biquad(biquad(stereo[c], b1, a1), b2, a2) for c in range(2)]
    blk, hop = int(0.400*SR), int(0.100*SR)
    loud = []
    for i in range(0, len(ks[0])-blk, hop):
        z = sum(np.mean(k[i:i+blk]**2) for k in ks)
        if z > 0: loud.append(-0.691 + 10*np.log10(z))
    loud = np.array(loud); gated = loud[loud > -70]
    if not len(gated): return -70.0
    g2 = gated[gated > gated.mean() - 10]
    return float(g2.mean() if len(g2) else gated.mean())

def true_peak(x):
    up = np.fft.irfft(np.pad(np.fft.rfft(x), (0, len(x)*3//2)), len(x)*4)*4
    return float(np.max(np.abs(up)))

# ── сессия ─────────────────────────────────────────────────────────────────
class Session:
    """две шины (music / sfx), общий мастер-тракт, стемы, сходящиеся в микс"""

    def __init__(self, dur, sr=SR):
        self.dur = dur; self.N = int(dur*sr)
        self.bus = {'music': [np.zeros(self.N), np.zeros(self.N)],
                    'sfx':   [np.zeros(self.N), np.zeros(self.N)]}
        self.duck_env = np.ones(self.N)
        self.G = None; self.mix = None; self.stems = {}

    def place(self, bus, sig, at, gain=1.0, pan=0.0):
        """ставит звук на таймкод; отрицательный at (присос перед ударом) обрезается"""
        b = self.bus[bus]
        i = int(at*SR); off = 0
        if i < 0: off, i = -i, 0
        if i >= self.N or off >= len(sig): return
        s = sig[off:off + (self.N - i)]*gain
        th = (pan + 1)*math.pi/4
        b[0][i:i+len(s)] += s*math.cos(th)
        b[1][i:i+len(s)] += s*math.sin(th)

    def duck(self, words, db=-9.0, atk=0.035, rel=0.220):
        """words: [(слово, таймкод)] — та же карта, что у картинки"""
        g = 10**(db/20)
        for w, at in words:
            dur = 0.06*len(w) + 0.20
            i0, i1 = max(0, int((at-0.09)*SR)), min(self.N, int((at+dur)*SR))
            ai, ri = int(atk*SR), int(rel*SR)
            seg = np.full(max(0, i1-i0), g)
            if len(seg) > ai: seg[:ai] = np.linspace(1, g, ai)
            self.duck_env[i0:i1] = np.minimum(self.duck_env[i0:i1], seg)
            j1 = min(self.N, i1+ri)
            self.duck_env[i1:j1] = np.maximum(self.duck_env[i1:j1], np.linspace(g, 1, j1-i1))
        k = np.hanning(int(0.03*SR)); k /= k.sum()
        self.duck_env = np.convolve(self.duck_env, k, mode='same')
        self.duck_env[:len(k)] = self.duck_env[len(k)]
        self.duck_env[-len(k):] = self.duck_env[-len(k)]

    def master(self, target_lufs=-14.0, ceiling_db=-1.0, reverb=True, fade_out=0.45):
        if reverb:
            for name, mix in (('music', 0.24), ('sfx', 0.12)):
                for c in (0, 1):
                    self.bus[name][c] = plate(self.bus[name][c], mix)
        fade = np.ones(self.N)
        fade[:int(0.02*SR)] = np.linspace(0, 1, int(0.02*SR))
        fo = int(fade_out*SR); fade[-fo:] = np.linspace(1, 0, fo)
        d = self.duck_env
        sm = np.vstack(self.bus['music'])*d*0.85*fade
        ss = np.vstack(self.bus['sfx'])*(0.55 + 0.45*d)*fade
        mix = sm + ss
        ceiling = 10**(ceiling_db/20)
        G = np.ones(self.N)
        g = compress(mix); G *= g; mix = mix*g
        for _ in range(4):                       # нормализация одна не доводит:
            k = 10**((target_lufs - lufs(mix))/20)  # лимитер съедает громкость обратно
            G *= k; mix = mix*k
            g = limiter(mix, ceiling); G *= g; mix = mix*g
        pk = max(true_peak(mix[0]), true_peak(mix[1]))
        if pk > ceiling: k = ceiling/pk; G *= k; mix = mix*k
        self.G, self.mix = G, mix
        self.stems = {'music': sm*G, 'sfx': ss*G}
        return {'lufs': lufs(mix),
                'dbtp': 20*np.log10(max(true_peak(mix[0]), true_peak(mix[1]))),
                'stem_null_db': 20*np.log10(max(np.max(np.abs(sum(self.stems.values()) - mix)), 1e-12))}

    def write(self, path, stems=False):
        write24(path, self.mix)
        if stems:
            base = path.rsplit('.', 1)[0]
            for k, v in self.stems.items():
                write24(f'{base}_stem_{k}.wav', v)

def write24(path, stereo):
    o = (np.clip(stereo.T, -1, 1)*8388607).astype('<i4').tobytes()
    b = bytearray()
    for i in range(0, len(o), 4):
        b += o[i:i+3]
    with wave.open(path, 'wb') as f:
        f.setnchannels(2); f.setsampwidth(3); f.setframerate(SR)
        f.writeframes(bytes(b))
    print('wrote', path)
