#!/usr/bin/env python3
"""score.py — весь саундтрек кодом: музыка + SFX + микс. Ни одного сэмпла.

v2. Что изменилось против первой версии и почему:
  • дроп2 держал 86% энергии в низу — суб и кик били в один отсчёт и забивали
    всё остальное. Теперь суб короткий, кик и суб разведены, музыкальная шина
    сайдчейнится их общим триггером;
  • микс был моно (корреляция 0.999) — реверберация считалась одинаково в оба
    канала. Теперь у каналов разные сетки отражений, плюс диффузия на
    олл-пассах вместо голой гребёнки, которая звенела;
  • выше 6 кГц почти ничего не было — добавлен воздух и яркие слои;
  • у музыки не было ни одной мелодии. Теперь есть мотив из четырёх нот,
    который приходит на искре и возвращается на энд-карде.
"""
import json, math, os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfxlib

SR = 48000
DUR = 26.0
N = int(SR * DUR)
BPM = 120.0
BEAT = 60.0 / BPM

# ── карта голоса (зеркало src/timing.js) ───────────────────────────────────
VO_WORDS = [
    ("TODAY,", 0.12), ("THINKING", 0.70), ("GETS", 1.22), ("FASTER.", 1.62),
    ("Gemini", 2.74), ("three", 3.62), ("point", 3.92), ("five", 4.10),
    ("Do", 7.78), ("you", 7.96), ("have", 8.14), ("new", 8.34),
    ("ideas", 8.56), ("to", 8.84), ("explore?", 9.00),
    ("All", 16.15), ("answered.", 16.45), ("In", 17.35), ("seconds.", 17.62),
    ("Experience", 18.78), ("Gemini.", 19.30),
]
SLAMS = [0.12, 0.70, 1.22, 1.62]
DROP1, DROP2 = 3.62, 16.15
TYPE_START, TYPE_END = 9.58, 10.86
PROMPT = "Recommend me a movie for tonight"

rng = np.random.default_rng(7)
def noise(n): return rng.standard_normal(n)

# ── готовые сэмплы: если слот заполнен, он выигрывает у синтеза ────────────
SFXLIB = sfxlib.load(verbose=True)
if SFXLIB:
    print(f"сэмплов подключено: {len(SFXLIB)}/{len(sfxlib.SLOTS)}")

def S(slot, fallback):
    x = SFXLIB.get(slot)
    return x if x is not None else fallback

def WH(dur, f0, f1, p0, p1):
    """вуш: сэмпл едет по панораме, синтез уже стереофонический"""
    slot = 'whoosh_short' if dur < 0.6 else 'whoosh_long'
    x = SFXLIB.get(slot)
    if x is not None:
        return sfxlib.pan_sweep(x, p0, p1)
    return whoosh_st(dur, f0, f1, p0, p1)

# ── базовое ────────────────────────────────────────────────────────────────
def exp_env(n, tau): return np.exp(-np.arange(n) / (tau * SR))

def adsr(dur, a=0.005, d=0.1, s=0.6, r=0.2, n=None):
    n = n or int(dur * SR)
    out = np.zeros(n); ai, di, ri = int(a*SR), int(d*SR), int(r*SR)
    si = max(0, n - ai - di - ri); i = 0
    if ai: out[i:i+ai] = np.linspace(0, 1, ai); i += ai
    if di: out[i:i+di] = np.linspace(1, s, di); i += di
    if si: out[i:i+si] = s; i += si
    if ri: out[i:i+ri] = np.linspace(out[max(i-1, 0)], 0, min(ri, n-i))
    return out[:n]

def biquad(x, b, a):
    y = np.zeros_like(x); x1 = x2 = y1 = y2 = 0.0
    b0, b1, b2 = b; a0, a1, a2 = a
    b0, b1, b2, a1, a2 = b0/a0, b1/a0, b2/a0, a1/a0, a2/a0
    for i in range(len(x)):
        xi = x[i]; yi = b0*xi + b1*x1 + b2*x2 - a1*y1 - a2*y2
        x2, x1 = x1, xi; y2, y1 = y1, yi; y[i] = yi
    return y

def _spec(x, fn):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1/SR)
    return np.fft.irfft(X * fn(f), len(x))

def lp(x, fc, order=4): return _spec(x, lambda f: 1.0/(1.0 + (f/max(fc, 20.0))**order))
def hp(x, fc, order=4): return _spec(x, lambda f: 1.0 - 1.0/(1.0 + (f/max(fc, 20.0))**order))
def shelf_hi(x, fc, db):
    g = 10**(db/20)
    return _spec(x, lambda f: 1.0 + (g-1)/(1.0 + (max(fc, 20.0)/np.maximum(f, 1.0))**2))
def shelf_lo(x, fc, db):
    g = 10**(db/20)
    return _spec(x, lambda f: 1.0 + (g-1)/(1.0 + (np.maximum(f, 1.0)/max(fc, 20.0))**2))
def peak(x, fc, db, q=1.0):
    g = 10**(db/20); sg = 1/(2*max(q, 0.1))
    return _spec(x, lambda f: 1.0 + (g-1)*np.exp(-(np.log2(np.maximum(f, 1.0)/fc)**2)/(2*sg*sg)))
def tilt(x, fc, db):
    """наклон спектра: + сверху, − снизу, вокруг fc"""
    return shelf_hi(x, fc, db)

# ── генераторы ─────────────────────────────────────────────────────────────
def sine(f, n, ph=0.0): return np.sin(2*np.pi*f*np.arange(n)/SR + ph)

def saw(f, n, parts=16):
    o = np.zeros(n); k = np.arange(n)/SR
    for h in range(1, parts+1):
        if f*h > SR*0.45: break
        o += np.sin(2*np.pi*f*h*k)/h
    return o*0.55

def sweep(f0, f1, n, curve=2.0):
    k = np.arange(n)/SR; T = max(n/SR, 1e-9)
    return np.sin(2*np.pi*np.cumsum(f0 + (f1-f0)*(k/T)**curve)/SR)

def hz(semi, base=146.83): return base * 2**(semi/12)   # base = D3

# ── мотив: четыре ноты, которые помнишь после ролика ───────────────────────
HOOK = [7, 12, 10, 14]          # A  D  C  E  — вопрос без ответа
HOOK_END = [7, 12, 14, 16]      # A  D  E  F# — тот же ход, но разрешается в мажор

def bell(f, dur=2.4, bright=1.0):
    n = int(dur*SR); o = np.zeros(n)
    for h, g, dec in ((1, 1.0, 1.0), (2.01, .5, .6), (3.02, .3, .4),
                      (4.4, .18, .25), (6.8, .12, .18), (9.2, .07*bright, .12)):
        o += sine(f*h, n)*exp_env(n, dur*0.33*dec)*g
    return o*0.35

def pluck(semi, dur=0.35, base=146.83, bright=3200):
    n = int(dur*SR); f = hz(semi, base)
    o = saw(f, n, 10)*0.6 + sine(f*2, n)*0.3
    return hp(lp(o, bright), 140)*exp_env(n, dur*0.18)*0.8

def pad(semis, dur, base=146.83, detune=0.14, cut=1100, hpf=130):
    n = int(dur*SR); o = np.zeros(n)
    for s in semis:
        f = hz(s, base)
        o += saw(f*(1-detune/100), n) + saw(f*(1+detune/100), n)
    return hp(lp(o/max(1, len(semis)*2), cut), hpf)*adsr(dur, .25, .3, .85, .6, n)

def stab(semis, dur=1.1, base=146.83, cut=7000):
    """широкий яркий аккорд: это он должен нести дроп, а не суб"""
    n = int(dur*SR); o = np.zeros(n)
    for s in semis:
        f = hz(s, base)
        o += saw(f, n)*0.7 + saw(f*1.005, n)*0.7 + sine(f*2, n)*0.3 + sine(f*4, n)*0.08
    o = hp(lp(o/(len(semis)*1.6), cut), 150)
    return o*exp_env(n, dur*0.26)

def bass(semi, dur, base=73.42):
    """своя линия в басу: статичный корень — главная причина, почему трек стоит"""
    n = int(dur*SR); f = hz(semi, base)
    o = sine(f, n) + 0.35*sine(f*2, n) + 0.12*saw(f, n, 6)
    return lp(o, 420)*adsr(dur, .008, .08, .75, .12, n)*0.9

def sub_hit(f0=64, f1=34, dur=0.42, drive=1.5):
    """короче, чем в v1: длинный суб — это и есть мутный дроп"""
    n = int(dur*SR)
    s = sweep(f0, f1, n, 0.5)*exp_env(n, dur*0.26)
    return np.tanh(s*drive)/np.tanh(drive)

def kick(dur=0.38):
    n = int(dur*SR); cn = int(0.004*SR)
    s = sweep(150, 48, n, 0.32)*exp_env(n, 0.075)
    s += np.pad(noise(cn)*np.linspace(1, 0, cn), (0, n-cn))*0.35
    return np.tanh(s*1.4)*0.9

def hat(dur=0.09, bright=11000, open_=False):
    n = int(dur*SR); s = noise(n)
    s = hp(s, bright*0.55)
    return s*exp_env(n, 0.03 if open_ else 0.012)*0.42

def crash(dur=2.2, rev=False):
    n = int(dur*SR); s = hp(noise(n), 2200)
    e = exp_env(n, dur*0.22) if not rev else np.linspace(0, 1, n)**2.6
    o = s*e*0.38
    return o[::-1].copy() if rev else o

def shimmer(semis, dur, base=146.83):
    """воздух: верхние октавы аккорда с медленным биением"""
    n = int(dur*SR); o = np.zeros(n)
    for s in semis:
        for oct_ in (3, 4, 5):
            f = hz(s, base)*2**oct_
            if f > SR*0.45: continue
            o += sine(f, n, rng.random()*6.28)*(1 + 0.12*np.sin(2*np.pi*rng.uniform(.2, .6)*np.arange(n)/SR))
    return hp(o/(len(semis)*3), 2600)*adsr(dur, .5, .4, .8, .8, n)*0.13

# ── SFX ────────────────────────────────────────────────────────────────────
def impact(dur=0.55, tone=180, bright=1.0, body=1.0):
    n = int(dur*SR)
    nz = lp(noise(n)*exp_env(n, 0.045), 3200*bright)
    nz += hp(noise(n)*exp_env(n, 0.015), 6000)*0.45*bright   # верхний щелчок — он и читается как удар
    bod = sine(tone, n)*exp_env(n, 0.10)*0.6*body
    cn = int(0.006*SR)
    cl = np.pad(noise(cn)*np.linspace(1, 0, cn), (0, n-cn))
    return (nz*0.8 + bod + cl*0.5)*0.9

def suck(dur=0.30):
    n = int(dur*SR)
    s = lp(noise(n)*np.linspace(0, 1, n)**2.2, 7000)*np.linspace(0.2, 1.0, n)
    s += sweep(300, 2600, n, 2.0)*np.linspace(0, .35, n)
    return s*0.5

def whoosh_st(dur=0.5, f0=300, f1=4500, pan0=-0.9, pan1=0.9):
    """вуш с настоящим движением: фильтр едет по частоте, звук — по панораме.
    статичный отфильтрованный шум в v1 читался как «пшш», а не как движение."""
    n = int(dur*SR)
    s = noise(n)
    a, b = lp(s, f0), lp(s, f1)
    k = np.sin(np.linspace(0, np.pi, n))**0.8
    o = a*(1-k) + b*k
    o += sweep(f0*0.5, f1*0.5, n, 1.6)*k*0.12
    o *= np.sin(np.linspace(0, np.pi, n))**1.5*0.5
    pan = np.linspace(pan0, pan1, n)
    th = (pan + 1)*np.pi/4
    return np.vstack([o*np.cos(th), o*np.sin(th)])

def tick(dur=0.05, f=2400, bright=1.0):
    n = int(dur*SR)
    return (sine(f, n)*0.55 + hp(noise(n), 3000)*0.45*bright)*exp_env(n, 0.006)

def click(dur=0.12, f=1200):
    n = int(dur*SR)
    return (sine(f, n) + sine(f*1.5, n)*0.4)*exp_env(n, 0.018)*0.7

def riser(dur, f0=140, f1=6000, gain=0.42, note=None):
    """шум + тональный свип в тонику: чистый шум не создаёт напряжения"""
    n = int(dur*SR); s = noise(n)
    lo, hi = lp(s, f0*4), hp(lp(s, f1), 400)
    k = np.linspace(0, 1, n)**1.8
    o = lo*(1-k) + hi*k
    o = o*k**1.2
    if note is not None:
        f = hz(note)
        o += sweep(f*0.5, f*2, n, 2.2)*k*0.22
    return o*gain

# ── шины ───────────────────────────────────────────────────────────────────
music = np.zeros((2, N))
sfx = np.zeros((2, N))
low = np.zeros((2, N))        # кик и суб — отдельно, в моно, не в реверберации
trig = np.zeros(N)            # триггер сайдчейна

def place(bus, sig, at, gain=1.0, pan=0.0, width=0.0):
    """width>0 — лёгкий Haas: канал задерживается на несколько мс и даёт ширину,
    не ломая моно-совместимость."""
    i = int(at*SR); off = 0
    if i < 0: off, i = -i, 0
    if i >= N: return
    if sig.ndim == 2:
        s = sig[:, off:off + (N-i)]*gain
        if s.shape[1] <= 0: return
        bus[:, i:i+s.shape[1]] += s
        return
    s = sig[off:off + (N-i)]*gain
    if len(s) <= 0: return
    th = (pan + 1)*np.pi/4
    L, R = s*math.cos(th), s*math.sin(th)
    if width > 0:
        d = int(width*0.001*SR)
        if d > 0 and len(s) > d:
            R = np.concatenate([np.zeros(d), R[:-d]])
    bus[0, i:i+len(L)] += L
    bus[1, i:i+len(R)] += R

def place_low(sig, at, gain=1.0):
    i = int(at*SR)
    if i < 0 or i >= N: return
    s = sig[:N-i]*gain
    low[0, i:i+len(s)] += s
    low[1, i:i+len(s)] += s
    trig[i:i+len(s)] = np.maximum(trig[i:i+len(s)], np.abs(s)/(np.max(np.abs(s)) + 1e-9))

# ═══ аранжировка ═══════════════════════════════════════════════════════════
Dm, Dsus, Dadd9, Dmaj = [0, 3, 7, 12], [0, 5, 7, 12], [0, 4, 7, 14], [0, 4, 7, 11]

# 1. интро под слэмы — дрон тише, чем был: слэмы должны пробивать
place(music, pad([-12, -5, 3], 3.4, cut=600, hpf=90), 0.0, 0.42, width=14)
place(music, riser(2.3, 110, 2900, 0.26, note=0), 0.0, 1.0)
place(music, shimmer([0, 7], 2.4), 0.1, 0.32, width=18)
for i, s in enumerate(SLAMS):
    g = 1.0 if i < 3 else 1.3
    place(sfx, S('suck', suck(0.28)), s-0.28, 0.55*g)
    place(sfx, S(f'slam_{i+1}', impact(0.6, 150+i*18, 0.9+0.12*i)), s, 0.85*g, pan=(-0.12, 0.12, -0.08, 0)[i], width=6)
    place_low(S('sub_drop', sub_hit(60, 32, 0.40)), s, 0.72*g)
    place(sfx, WH(0.34, 400, 3000, -0.6, 0.6), s-0.20, 0.30)
place(music, S('crash', crash(1.6)), SLAMS[3], 0.18)

# 2. схлопывание в искру — здесь впервые звучит мотив
place(sfx, WH(0.55, 500, 5200, 0.7, -0.7), 2.42, 0.55)
place(sfx, S('click_ui', click(0.22, 900)), 2.74, 0.32)
for j, sm in enumerate(HOOK):
    place(music, bell(hz(sm+12), 1.8), 2.80 + j*0.16, 0.26 - j*0.02, pan=-0.35 + j*0.23, width=10)

# 3. дроп 1 — несёт широкий яркий аккорд, суб только подпирает
place(sfx, S('suck', suck(0.34)), DROP1-0.34, 0.7)
place_low(S('sub_drop', sub_hit(70, 32, 0.46, 1.8)), DROP1, 0.70)
place(music, stab(Dm, 1.4), DROP1, 0.80, width=16)
place(sfx, S('impact_mid', impact(0.7, 130, 1.25)), DROP1, 0.95, width=8)
place(music, S('crash', crash(2.0)), DROP1, 0.30, pan=0.15)
place(music, pad([0, 7, 12, 16], 2.4, cut=2000), DROP1+0.05, 0.40, width=20)
place(music, shimmer([0, 7, 12], 2.2), DROP1+0.05, 0.9, width=22)
for j, sm in enumerate(HOOK):
    place(music, bell(hz(sm+12), 1.4, 1.3), DROP1+0.10 + j*0.14, 0.17, pan=0.4 - j*0.26)
tb = DROP1
while tb < 5.5:
    k = int(round((tb-DROP1)/(BEAT/2)))
    place(music, hat(open_=(k % 4 == 3)), tb, 0.55 if k % 2 else 0.85, pan=-0.3 if k % 2 else 0.3)
    tb += BEAT/2
for j, sm in enumerate([0, 0, -2, 3]):
    place_low(bass(sm, 0.46), DROP1 + j*BEAT, 0.34)
place(sfx, WH(0.75, 600, 7000, -0.8, 0.8), 4.85, 0.75)

# 4. приложение — басовая линия движется, арпеджио раскинуто по панораме
place(music, pad([-12, -9, -5, -2], 6.4, cut=900, hpf=100), 5.5, 0.52, width=24)
place(music, shimmer([0, 3, 7], 6.4), 5.6, 0.55, width=26)
arp = [0, 7, 10, 7, 12, 7, 10, 3]
bassline = [0, 0, -4, -4, -2, -2, 3, 3]
k = 0; tb = 5.5
while tb < 12.0:
    place(music, pluck(arp[k % 8], 0.42), tb, 0.24, pan=-0.55 + 0.37*(k % 4))
    if k % 2 == 0:
        place_low(bass(bassline[(k//2) % 8], 0.44), tb, 0.28)
        place_low(kick(), tb, 0.30)
    place(music, hat(dur=0.07), tb + BEAT/4, 0.18, pan=0.4 if k % 2 else -0.4)
    k += 1; tb += BEAT/2
place(sfx, WH(0.6, 300, 2400, -0.7, 0.2), 5.52, 0.45)
place(sfx, WH(0.7, 700, 8000, 0.3, -0.9), 6.95, 0.70)
place(sfx, S('impact_soft', impact(0.4, 220, 1.5, body=0.5)), 7.50, 0.50)

# 5. набор текста — тики с разбросом по высоте и панораме, иначе это пулемёт
for i, ch in enumerate(PROMPT):
    if ch == ' ': continue
    p = (i+1)/len(PROMPT)
    at = TYPE_START + (TYPE_END-TYPE_START)*(p**(1/0.94))
    f = 1900 + (hash(ch) % 7)*150
    place(sfx, S('tick_type', tick(0.045, f, 1.0)), at, 0.17 + 0.05*((i % 3) == 0), pan=-0.45 + 0.9*p)

# 6. отправка
place(sfx, WH(0.5, 600, 5600, -0.5, 0.5), 11.02, 0.60)
place(sfx, S('click_ui', click(0.14, 1500)), 11.52, 0.45)
place(sfx, S('click_ui', click(0.10, 1800)), 12.36, 0.40)
place(sfx, S('tap', click(0.16, 900)), 12.50, 0.70)
place(sfx, S('impact_soft', impact(0.5, 160, 1.6, body=0.6)), 12.52, 0.55, width=5)
place(sfx, WH(0.8, 900, 9000, 0.0, 0.0), 12.55, 0.80)

# 7. билд — и тишина перед дропом: без паузы дроп не читается как дроп
place(music, S('riser_build', riser(3.05, 190, 7000, 0.44, note=0)), 12.78, 1.0)
place(music, pad([0, 7, 12], 3.0, cut=1300), 12.80, 0.26, width=18)
place(music, S('crash_rev', crash(1.9, rev=True)), 15.0, 0.42)
tb, step = 12.9, BEAT
while tb < 15.92:
    place(music, hat(0.07), tb, 0.48, pan=-0.35 if int(tb*7) % 2 else 0.35)
    step = max(BEAT/8, step*0.88); tb += step
for j in range(3):
    place(sfx, WH(0.45, 400, 3600, -0.8 + j*0.5, 0.8 - j*0.4), 12.95 + j*0.42, 0.28)
place_low(bass(0, 0.9), 15.1, 0.26)
# 15.92–16.15 — дыра: ничего не играет

# 8. дроп 2 — самый большой. Ширина и верх, а не один низ
place(sfx, S('suck', suck(0.42)), DROP2-0.42, 0.85)
place_low(S('sub_drop', sub_hit(72, 30, 0.48, 2.0)), DROP2, 0.60)
place(music, stab(Dadd9, 1.5, cut=8000), DROP2, 0.92, width=20)
place(sfx, S('impact_big', impact(0.8, 115, 1.4)), DROP2, 1.0, width=10)
place(music, S('crash', crash(2.4)), DROP2, 0.62, pan=-0.2)
place(music, shimmer([0, 4, 7, 11], 3.0), DROP2, 1.6, width=26)
place(music, stab(Dadd9, 1.3, cut=8000), 16.45, 0.70, width=22)
place_low(S('sub_drop', sub_hit(66, 32, 0.40)), 16.45, 0.52)
place(sfx, S('impact_mid', impact(0.7, 135, 1.3)), 16.45, 0.90, width=8)
place(music, pad([0, 4, 7, 14], 5.0, cut=2600), 16.5, 0.40, width=24)
for j, sm in enumerate(HOOK):
    place(music, bell(hz(sm+12), 2.0, 1.4), 16.55 + j*0.25, 0.26, pan=-0.45 + j*0.3, width=12)
for w in (17.35, 17.62):
    place(sfx, S('impact_soft', impact(0.45, 195, 1.2, body=0.6)), w, 0.48, width=6)
    place_low(S('sub_drop', sub_hit(58, 36, 0.30)), w, 0.30)
k = 0; tb = DROP2
bl2 = [0, 0, 4, 4, -2, -2, 3, 3]
while tb < 21.0:
    place_low(kick(), tb, 0.40)
    place_low(bass(bl2[k % 8], 0.46), tb, 0.30)
    place(music, hat(), tb + BEAT/2, 0.55, pan=0.35 if k % 2 else -0.35)
    place(music, hat(0.07), tb + BEAT/4, 0.22, pan=-0.5)
    k += 1; tb += BEAT
k = 0; tb = 16.5
while tb < 21.0:
    place(music, pluck([0, 4, 7, 11, 7, 4][k % 6], 0.40), tb, 0.20, pan=-0.5 + 0.33*(k % 4))
    k += 1; tb += BEAT/2

# 9. experience
place(sfx, WH(0.7, 400, 3800, -0.8, 0.4), 18.80, 0.50)
place(sfx, WH(0.7, 700, 5800, 0.6, -0.5), 18.96, 0.45)
for j, sm in enumerate(HOOK):
    place(music, bell(hz(sm+12), 1.6), 19.30 + j*0.13, 0.20, pan=0.4 - j*0.27)

# 10. орб и логотип
place(music, pad([-12, -5, 0], 2.8, cut=1200), 21.0, 0.36, width=22)
place(music, shimmer([0, 7, 12], 3.0), 21.0, 0.52, width=28)
place(sfx, WH(1.3, 300, 4600, -0.9, 0.9), 21.05, 0.45)
place(sfx, WH(0.9, 800, 10000, 0.8, -0.8), 21.90, 0.50)
place_low(S('sub_drop', sub_hit(68, 32, 0.44, 1.7)), 22.30, 0.58)
place(sfx, S('impact_mid', impact(0.7, 145, 1.5)), 22.30, 0.85, width=10)
place(music, stab(Dadd9, 1.8, cut=9000), 22.30, 0.72, width=20)
place(music, S('crash', crash(2.2)), 22.30, 0.32, pan=0.2)
place(music, bell(hz(24), 2.6, 1.5), 22.34, 0.26)
place(sfx, S('twinkle', tick(0.09, 3400)), 22.95, 0.30, pan=0.5)

# 11. энд-кард — мотив разрешается в мажор, хвост не обрезается
place(music, pad([0, 4, 7, 11, 16], 3.2, cut=3000), 23.95, 0.46, width=26)
place(music, shimmer([0, 4, 7, 11], 3.0), 23.95, 2.4, width=30)
place_low(bass(0, 2.2), 23.95, 0.26)
for j, sm in enumerate(HOOK_END):
    place(music, bell(hz(sm+12), 2.6, 1.8), 24.0 + j*0.19, 0.30 - j*0.03, pan=-0.4 + j*0.27, width=12)
    place(music, bell(hz(sm+24), 1.8, 1.8), 24.0 + j*0.19, 0.09, pan=0.4 - j*0.27)
place(sfx, WH(0.6, 400, 3200, -0.5, 0.5), 23.92, 0.33)
place(music, S('crash', crash(2.6)), 23.98, 0.26, pan=0.25)

# ═══ пространство ══════════════════════════════════════════════════════════
def diffuse(x, seed):
    """олл-пассы: размывают гребёнку, из-за которой v1 звенела на колоколах"""
    r = np.random.default_rng(seed)
    y = x.copy()
    for d_ms, g in ((4.7, .7), (11.3, .62), (23.9, .55), (41.1, .48)):
        d = int(d_ms*0.001*SR*r.uniform(0.9, 1.1))
        z = np.zeros_like(y)
        z[d:] = y[:-d]
        y = -g*y + z + g*np.concatenate([np.zeros(d), (-g*y + z)[:-d]])
    return y

def plate(x, seed, mix=0.24, dec=1.7):
    taps = np.random.default_rng(seed).uniform(0.019, 0.33, 9)
    out = np.zeros_like(x)
    for d in sorted(taps):
        i = int(d*SR)
        out[i:] += x[:len(x)-i]*math.exp(-d/dec)*0.7
    out = lp(diffuse(out, seed), 6000)
    return x*(1-mix) + out*mix*0.55

# у каналов РАЗНЫЕ сетки отражений — отсюда берётся ширина
for c, seed in ((0, 101), (1, 202)):
    music[c] = plate(music[c], seed, 0.26)
    sfx[c] = plate(sfx[c], seed + 7, 0.13)

# ── сайдчейн: музыка расступается под киком и субом ────────────────────────
def follower(t, atk=0.004, rel=0.16):
    B = 64; n = len(t); pad_n = (-n) % B
    e = np.pad(t, (0, pad_n)).reshape(-1, B).max(axis=1)
    aa, ar = math.exp(-B/(atk*SR)), math.exp(-B/(rel*SR))
    out = np.empty_like(e); cur = 0.0
    for i in range(len(e)):
        c = aa if e[i] > cur else ar
        cur = c*cur + (1-c)*e[i]; out[i] = cur
    return np.interp(np.arange(n), np.arange(len(out))*B + B/2, out)

duck_low = 1.0 - 0.55*np.clip(follower(trig), 0, 1)
music *= duck_low
sfx *= (0.75 + 0.25*duck_low)

# ── тон-коррекция шин ──────────────────────────────────────────────────────
for c in (0, 1):
    # v1 держал ~50% энергии в 2–6 кГц — это кричит. Дип там, тело снизу, воздух сверху.
    music[c] = shelf_hi(shelf_lo(peak(hp(music[c], 85), 3000, -3.0, 1.5), 260, 2.5), 8000, 3.0)
    sfx[c] = shelf_hi(peak(hp(sfx[c], 110), 3300, -1.8, 1.5), 9500, 2.0)
    low[c] = lp(low[c], 220)                              # низ — только низ

# ── дак под голос ──────────────────────────────────────────────────────────
duck = np.ones(N)
for w, at in VO_WORDS:
    dur = 0.06*len(w) + 0.20
    i0, i1 = max(0, int((at-0.09)*SR)), min(N, int((at+dur)*SR))
    ai, ri = int(0.035*SR), int(0.22*SR)
    g = 10**(-9/20)
    seg = np.full(max(0, i1-i0), g)
    if len(seg) > ai: seg[:ai] = np.linspace(1, g, ai)
    duck[i0:i1] = np.minimum(duck[i0:i1], seg)
    j1 = min(N, i1+ri)
    duck[i1:j1] = np.maximum(duck[i1:j1], np.linspace(g, 1, j1-i1))
kern = np.hanning(int(0.03*SR)); kern /= kern.sum()
duck = np.convolve(duck, kern, mode='same')
duck[:len(kern)] = duck[len(kern)]; duck[-len(kern):] = duck[-len(kern)]
DUCK_ON = "--no-duck" not in sys.argv
d = duck if DUCK_ON else np.ones(N)

fade = np.ones(N)
fade[:int(0.02*SR)] = np.linspace(0, 1, int(0.02*SR))
fo = int(0.30*SR); fade[-fo:] = np.linspace(1, 0, fo)**0.6   # мягче, чтобы не рубить хвост

stem_music = (music + low*0.0)*d*0.85*fade
stem_low = low*(0.55 + 0.45*d)*fade*0.50
stem_sfx = sfx*(0.6 + 0.4*d)*fade
mix = stem_music + stem_low + stem_sfx

# ── мастер ─────────────────────────────────────────────────────────────────
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

def lufs(st):
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    b2 = [1.0, -2.0, 1.0]; a2 = [1.0, -1.99004745483398, 0.99007225036621]
    ks = [biquad(biquad(st[c], b1, a1), b2, a2) for c in range(2)]
    blk, hop = int(0.400*SR), int(0.100*SR); loud = []
    for i in range(0, len(ks[0])-blk, hop):
        z = sum(np.mean(k[i:i+blk]**2) for k in ks)
        if z > 0: loud.append(-0.691 + 10*np.log10(z))
    loud = np.array(loud); gated = loud[loud > -70]
    if not len(gated): return -70.0
    g2 = gated[gated > gated.mean()-10]
    return float(g2.mean() if len(g2) else gated.mean())

def tp(x):
    up = np.fft.irfft(np.pad(np.fft.rfft(x), (0, len(x)*3//2)), len(x)*4)*4
    return float(np.max(np.abs(up)))

ceiling = 10**(-1.0/20)
before = lufs(mix)
G = np.ones(N)
g = compress(mix, thr_db=-26.0, ratio=4.5, makeup_db=4.0); G *= g; mix = mix*g
for _ in range(7):
    k = 10**((-14.0 - lufs(mix))/20); G *= k; mix = mix*k
    g = limiter(mix, ceiling); G *= g; mix = mix*g
pk = max(tp(mix[0]), tp(mix[1]))
if pk > ceiling: k = ceiling/pk; G *= k; mix = mix*k

mus, lows, sfxs = stem_music*G, stem_low*G, stem_sfx*G
null = np.max(np.abs((mus + lows + sfxs) - mix))
corr = float(np.corrcoef(mix[0], mix[1])[0, 1])
print(f"LUFS {before:.2f} -> {lufs(mix):.2f}   TP {20*np.log10(max(tp(mix[0]),tp(mix[1]))):.2f} dBTP")
print(f"корреляция L/R {corr:.3f}   стемы нулятся на {20*np.log10(max(null,1e-12)):.1f} dBFS")

def write24(path, st):
    o = (np.clip(st.T, -1, 1)*8388607).astype('<i4').tobytes()
    b = bytearray()
    for i in range(0, len(o), 4): b += o[i:i+3]
    with wave.open(path, 'wb') as f:
        f.setnchannels(2); f.setsampwidth(3); f.setframerate(SR)
        f.writeframes(bytes(b))
    print('wrote', path)

write24('out/score.wav', mix)
write24('out/stem_music.wav', mus)
write24('out/stem_low.wav', lows)
write24('out/stem_sfx.wav', sfxs)
json.dump({"duck_db": -9, "bpm": BPM, "hook": HOOK, "words": VO_WORDS},
          open('out/score_meta.json', 'w'), indent=1)
