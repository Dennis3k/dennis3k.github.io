#!/usr/bin/env python3
"""score.py — the whole soundtrack written in code: original score + SFX.

Nothing sampled. 120 BPM, one beat = 0.5 s = 15 frames at 30 fps.
Every hit is placed from the same timing map the picture uses, so when the
ElevenLabs voice lands, the duck envelope and the hits are already in place.
"""
import json, math, struct, sys, wave
import numpy as np

SR = 48000
DUR = 26.0
N = int(SR * DUR)
BPM = 120.0
BEAT = 60.0 / BPM

# ── the timing map (mirror of src/timing.js) ────────────────────────────────
VO_WORDS = [
    ("TODAY,", 0.12), ("THINKING", 0.70), ("GETS", 1.22), ("FASTER.", 1.62),
    ("Gemini", 2.74), ("three", 3.62), ("point", 3.92), ("five", 4.10),
    ("Do", 7.78), ("you", 7.96), ("have", 8.14), ("new", 8.34),
    ("ideas", 8.56), ("to", 8.84), ("explore?", 9.00),
    ("All", 16.15), ("answered.", 16.45), ("In", 17.35), ("seconds.", 17.62),
    ("Experience", 18.78), ("Gemini.", 19.30),
]
SLAMS = [0.12, 0.70, 1.22, 1.62]
DROP1, DROP2 = 3.62, 16.45
TYPE_START, TYPE_END = 9.58, 10.86
PROMPT = "Recommend me a movie for tonight"

t = np.arange(N) / SR

def env_adsr(dur, a=0.005, d=0.1, s=0.6, r=0.2, n=None):
    n = n or int(dur * SR)
    out = np.zeros(n)
    ai, di = int(a * SR), int(d * SR)
    ri = int(r * SR)
    si = max(0, n - ai - di - ri)
    i = 0
    if ai: out[i:i+ai] = np.linspace(0, 1, ai); i += ai
    if di: out[i:i+di] = np.linspace(1, s, di); i += di
    if si: out[i:i+si] = s; i += si
    if ri: out[i:i+ri] = np.linspace(out[max(i-1,0)], 0, min(ri, n - i))
    return out[:n]

def exp_env(n, tau):
    return np.exp(-np.arange(n) / (tau * SR))

def biquad(x, b, a):
    y = np.zeros_like(x)
    x1 = x2 = y1 = y2 = 0.0
    b0, b1, b2 = b; a0, a1, a2 = a
    b0, b1, b2, a1, a2 = b0/a0, b1/a0, b2/a0, a1/a0, a2/a0
    for i in range(len(x)):
        xi = x[i]
        yi = b0*xi + b1*x1 + b2*x2 - a1*y1 - a2*y2
        x2, x1 = x1, xi
        y2, y1 = y1, yi
        y[i] = yi
    return y

def _lp_coef(fc, q=0.707):
    w = 2*math.pi*fc/SR; c, s = math.cos(w), math.sin(w); al = s/(2*q)
    b = [(1-c)/2, 1-c, (1-c)/2]; a = [1+al, -2*c, 1-al]
    return b, a
def _hp_coef(fc, q=0.707):
    w = 2*math.pi*fc/SR; c, s = math.cos(w), math.sin(w); al = s/(2*q)
    b = [(1+c)/2, -(1+c), (1+c)/2]; a = [1+al, -2*c, 1-al]
    return b, a

def lowpass(x, fc, q=0.707): return biquad(x, *_lp_coef(max(20, min(fc, SR*0.45)), q))
def highpass(x, fc, q=0.707): return biquad(x, *_hp_coef(max(20, min(fc, SR*0.45)), q))

def fft_lowpass(x, fc):
    """fast, zero-phase — used for long sweeps where a biquad loop is too slow"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1/SR)
    X *= 1.0 / (1.0 + (f / max(fc, 20.0))**4)
    return np.fft.irfft(X, len(x))

def place(buf, sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    off = 0
    if i < 0: off = -i; i = 0
    if i >= N or off >= len(sig): return
    s = sig[off:off + (N - i)] * gain
    j = i + len(s)
    th = (pan + 1) * math.pi / 4          # equal-power pan
    buf[0][i:j] += s * math.cos(th) * 1.0
    buf[1][i:j] += s * math.sin(th) * 1.0

rng = np.random.default_rng(7)
def noise(n): return rng.standard_normal(n)

def sine(f, n, phase=0.0):
    return np.sin(2*np.pi*f*np.arange(n)/SR + phase)

def saw(f, n, parts=14):
    o = np.zeros(n); k = np.arange(n)/SR
    for h in range(1, parts+1):
        if f*h > SR*0.45: break
        o += np.sin(2*np.pi*f*h*k) / h
    return o * 0.55

def sweep_sine(f0, f1, n, curve=2.0):
    k = np.arange(n)/SR
    T = n/SR
    f = f0 + (f1-f0)*(k/T)**curve
    ph = 2*np.pi*np.cumsum(f)/SR
    return np.sin(ph)

# ── note helpers ───────────────────────────────────────────────────────────
def hz(semi, base=146.83):   # D3
    return base * 2**(semi/12)

Dm = [0, 3, 7, 12]        # D F A D
Dsus = [0, 5, 7, 12]
Dadd9 = [0, 4, 7, 14]     # D major add9 — the lift
Bb = [-2, 2, 5, 10]

# ── buffers ────────────────────────────────────────────────────────────────
music = [np.zeros(N), np.zeros(N)]
sfx   = [np.zeros(N), np.zeros(N)]

def sub_hit(f0=58, f1=32, dur=0.55, drive=1.6):
    n = int(dur*SR)
    s = sweep_sine(f0, f1, n, curve=0.55) * exp_env(n, dur*0.30)
    s = np.tanh(s*drive)/np.tanh(drive)
    return s

def impact(dur=0.5, tone=180, bright=1.0):
    n = int(dur*SR)
    nz = noise(n) * exp_env(n, 0.045)
    nz = fft_lowpass(nz, 2600*bright)
    bod = sine(tone, n) * exp_env(n, 0.10) * 0.6
    cl = noise(int(0.008*SR)); cl = np.pad(cl*np.linspace(1,0,len(cl)), (0, n-len(cl)))
    return (nz*0.8 + bod + cl*0.5) * 0.9

def suck(dur=0.28, f0=200, f1=4000):
    n = int(dur*SR)
    s = noise(n) * np.linspace(0, 1, n)**2.2
    s = fft_lowpass(s, 6000)
    s *= np.linspace(0.2, 1.0, n)
    return s*0.5

def whoosh(dur=0.5, pan_from=-0.8, pan_to=0.8, bright=3000):
    n = int(dur*SR)
    s = noise(n)
    s = fft_lowpass(s, bright)
    e = np.sin(np.linspace(0, np.pi, n))**1.6
    return s*e*0.5

def tick(dur=0.05, f=2400):
    n = int(dur*SR)
    return (sine(f, n)*0.6 + noise(n)*0.4) * exp_env(n, 0.006)

def click(dur=0.12, f=1200):
    n = int(dur*SR)
    return (sine(f, n) + sine(f*1.5, n)*0.4) * exp_env(n, 0.018) * 0.7

def bell(f, dur=2.4):
    n = int(dur*SR)
    o = np.zeros(n)
    for h, g, dec in ((1,1.0,1.0), (2.01,0.5,0.6), (3.02,0.3,0.4), (4.4,0.18,0.25), (6.8,0.1,0.18)):
        o += sine(f*h, n) * exp_env(n, dur*0.33*dec) * g
    return o*0.35

def pad(semis, dur, base=146.83, detune=0.12, cut=900):
    n = int(dur*SR)
    o = np.zeros(n)
    for s in semis:
        f = hz(s, base)
        o += saw(f*(1-detune/100), n) + saw(f*(1+detune/100), n)
    o /= max(1, len(semis)*2)
    o = fft_lowpass(o, cut)
    return o * env_adsr(dur, a=0.25, d=0.3, s=0.85, r=0.6, n=n)

def stab(semis, dur=0.9, base=146.83, cut=4200):
    n = int(dur*SR)
    o = np.zeros(n)
    for s in semis:
        f = hz(s, base)
        o += saw(f, n)*0.7 + saw(f*1.004, n)*0.7 + sine(f*2, n)*0.25
    o /= len(semis)*1.6
    o = fft_lowpass(o, cut)
    return o * exp_env(n, dur*0.22)

def pluck(semi, dur=0.35, base=146.83):
    n = int(dur*SR)
    f = hz(semi, base)
    o = (saw(f, n, 10)*0.6 + sine(f*2, n)*0.3)
    o = fft_lowpass(o, 3200)
    return o * exp_env(n, dur*0.18) * 0.8

def riser(dur, f0=120, f1=5200, gain=0.4):
    n = int(dur*SR)
    s = noise(n)
    # moving lowpass approximated by crossfading two static filters
    lo = fft_lowpass(s, f0*4)
    hi = fft_lowpass(s, f1)
    k = (np.linspace(0, 1, n))**1.8
    o = lo*(1-k) + hi*k
    o *= k**1.2
    o += sweep_sine(f0, f1*0.35, n, 2.4) * k * 0.25
    return o*gain

def kick(dur=0.42):
    n = int(dur*SR)
    s = sweep_sine(140, 46, n, 0.35) * exp_env(n, 0.09)
    cn = int(0.004*SR)
    s += np.pad(noise(cn)*np.linspace(1, 0, cn), (0, n-cn)) * 0.35
    return np.tanh(s*1.4)*0.9

def hat(dur=0.09, bright=9000):
    n = int(dur*SR)
    s = noise(n)
    s = s - fft_lowpass(s, bright*0.5)
    return s * exp_env(n, 0.012) * 0.35

# ── arrangement ────────────────────────────────────────────────────────────
# 1. tense intro under the slams
place(music, pad([0-12, 7-12, 15-12], 3.6, cut=520)*0.55, 0.0, 0.9)
place(music, riser(2.4, 100, 3400, 0.30), 0.0, 1.0)
for i, s in enumerate(SLAMS):
    g = 1.0 if i < 3 else 1.35
    place(sfx, suck(0.26), s-0.26, 0.55*g, pan=0.0)
    place(sfx, impact(0.6, 150+i*20, 0.8+0.15*i), s, 0.85*g)
    place(music, sub_hit(62, 30, 0.6), s, 0.95*g)
    place(sfx, whoosh(0.35), s-0.18, 0.35)

# 2. collapse into the sparkle
place(sfx, whoosh(0.55, bright=4200), 2.42, 0.55)
place(sfx, click(0.22, 900), 2.74, 0.35)
place(music, bell(hz(12), 2.2), 2.80, 0.30)

# 3. DROP 1 on "three"
place(sfx, suck(0.34), DROP1-0.34, 0.7)
place(music, sub_hit(70, 28, 0.9, 1.9), DROP1, 1.15)
place(music, stab(Dm, 1.3), DROP1, 0.75)
place(sfx, impact(0.7, 120, 1.2), DROP1, 1.0)
place(music, pad([0, 7, 12, 16], 2.6, cut=1500), DROP1+0.05, 0.4)
place(music, bell(hz(19), 2.0), DROP1+0.02, 0.22)
# beat-synced hats through the drop
tb = DROP1
while tb < 5.5:
    place(music, hat(), tb, 0.5 if int((tb-DROP1)/ (BEAT/2)) % 2 else 0.8)
    tb += BEAT/2
# fly-past to white
place(sfx, whoosh(0.75, bright=6000), 4.85, 0.75)

# 4. lighter tension under the app (5.5 → 12.0)
place(music, pad([0-12, 3-12, 7-12, 10-12], 6.8, cut=820), 5.5, 0.42)
arp = [0, 7, 10, 7, 12, 7, 10, 3]
k = 0
tb = 5.5
while tb < 12.0:
    place(music, pluck(arp[k % len(arp)], 0.42), tb, 0.22, pan=-0.25 + 0.5*((k % 4)/3))
    k += 1; tb += BEAT/2
tb = 5.5
while tb < 12.0:
    place(music, kick(), tb, 0.55)
    tb += BEAT
# phone rise + dive
place(sfx, whoosh(0.6, bright=2600), 5.52, 0.45)
place(sfx, whoosh(0.7, bright=7000), 6.95, 0.7)
place(sfx, impact(0.4, 220, 1.4), 7.50, 0.5)

# 5. typed letters — one tick per character, on the picture's own schedule
chars = len(PROMPT)
for i, ch in enumerate(PROMPT):
    if ch == ' ': continue
    p = (i + 1) / chars
    at = TYPE_START + (TYPE_END - TYPE_START) * (p ** (1/0.94))
    place(sfx, tick(0.045, 2100 + (i % 5) * 180), at, 0.22, pan=-0.3 + 0.6*(i/chars))

# 6. text flies into the bar, orb, tap
place(sfx, whoosh(0.5, bright=5200), 11.02, 0.6)
place(sfx, click(0.14, 1500), 11.52, 0.45)
place(sfx, click(0.10, 1800), 12.36, 0.4)
place(sfx, click(0.16, 900), 12.50, 0.7)
place(sfx, impact(0.5, 160, 1.5), 12.52, 0.55)
place(sfx, whoosh(0.8, bright=8000), 12.55, 0.8)

# 7. the build (12.75 → 16.1)
place(music, riser(3.3, 180, 6200, 0.42), 12.78, 1.0)
place(music, pad([0, 7, 12], 3.2, cut=1100), 12.80, 0.30)
tb, step = 12.9, BEAT
while tb < 16.05:                       # accelerating ticks
    place(music, hat(0.07), tb, 0.5)
    step = max(BEAT/8, step*0.88)
    tb += step
for i in range(3):
    place(sfx, whoosh(0.45), 12.95 + i*0.42, 0.3)

# 8. DROP 2 — the biggest
place(sfx, suck(0.42), 16.15-0.42, 0.85)
place(music, sub_hit(74, 26, 1.1, 2.1), VO_WORDS[15][1], 1.25)
place(sfx, impact(0.8, 110, 1.3), VO_WORDS[15][1], 1.0)
place(music, stab(Dadd9, 1.6), VO_WORDS[16][1], 0.85)
place(music, sub_hit(70, 28, 0.9, 2.0), VO_WORDS[16][1], 1.1)
place(sfx, impact(0.7, 130, 1.2), VO_WORDS[16][1], 0.95)
place(music, pad([0, 4, 7, 14], 5.2, cut=2100), 16.5, 0.42)
place(music, bell(hz(16), 2.6), 16.5, 0.22)
for w in (VO_WORDS[17][1], VO_WORDS[18][1]):
    place(sfx, impact(0.45, 190, 1.1), w, 0.5)
    place(music, sub_hit(60, 34, 0.5), w, 0.55)
tb = 16.15
while tb < 21.0:
    place(music, kick(), tb, 0.75); tb += BEAT
tb = 16.15 + BEAT/2
while tb < 21.0:
    place(music, hat(), tb, 0.45); tb += BEAT/2
k = 0; tb = 16.5
while tb < 21.0:
    place(music, pluck([0, 4, 7, 11, 7, 4][k % 6], 0.40), tb, 0.18, pan=-0.3 + 0.6*((k % 3)/2))
    k += 1; tb += BEAT/2

# 9. experience / devices rise
place(sfx, whoosh(0.7, bright=3400), 18.80, 0.5)
place(sfx, whoosh(0.7, bright=5200), 18.96, 0.45)
place(music, bell(hz(12), 2.2), 19.30, 0.25)

# 10. the orb and the G
place(music, pad([0-12, 7-12, 12-12], 3.0, cut=900), 21.0, 0.38)
place(sfx, whoosh(1.3, bright=4200), 21.05, 0.45)
place(sfx, whoosh(0.9, bright=9000), 21.90, 0.5)
place(music, sub_hit(66, 30, 0.9, 1.8), 22.30, 1.0)
place(sfx, impact(0.7, 140, 1.4), 22.30, 0.85)
place(music, stab(Dadd9, 2.0, cut=5200), 22.30, 0.7)
place(music, bell(hz(24), 2.8), 22.34, 0.28)
place(sfx, tick(0.09, 3200), 22.95, 0.35)   # the twinkle

# 11. the last chord rings under the end card
place(music, pad([0, 4, 7, 11, 16], 3.4, cut=2600), 23.95, 0.46)
place(music, bell(hz(16), 3.2), 24.0, 0.25)
place(music, bell(hz(23), 3.0), 24.12, 0.16)
place(sfx, whoosh(0.6, bright=3000), 23.92, 0.35)

# ── space: one short plate on the music bus ───────────────────────────────
def plate(x, mix=0.22, dec=1.6):
    taps = [(0.0231, 0.80), (0.0411, 0.72), (0.0601, 0.64), (0.0893, 0.55),
            (0.1237, 0.46), (0.1699, 0.36), (0.2311, 0.26), (0.3137, 0.18)]
    out = np.zeros_like(x)
    for d, g in taps:
        i = int(d*SR)
        out[i:] += x[:len(x)-i] * g
    out = fft_lowpass(out, 5200)
    tail = np.exp(-np.arange(len(x))/(dec*SR))
    return x*(1-mix) + out*mix*0.5

for c in (0, 1):
    music[c] = plate(music[c], 0.24)
    sfx[c] = plate(sfx[c], 0.12)

# ── duck: the music and SFX leave room for the voice ───────────────────────
duck = np.ones(N)
for w, at in VO_WORDS:
    dur = 0.06*len(w) + 0.20
    a, b = at - 0.09, at + dur
    i0, i1 = max(0, int(a*SR)), min(N, int(b*SR))
    atk = int(0.035*SR); rel = int(0.22*SR)
    seg = np.ones(i1-i0) * 10**(-9/20)          # −9 dB under every spoken word
    if len(seg) > atk: seg[:atk] = np.linspace(1, seg[0], atk)
    duck[i0:i1] = np.minimum(duck[i0:i1], seg)
    j0, j1 = i1, min(N, i1+rel)
    duck[j0:j1] = np.maximum(duck[j0:j1], np.linspace(10**(-9/20), 1, j1-j0))
# smooth the envelope so it never clicks
kern = np.hanning(int(0.03*SR)); kern /= kern.sum()
duck = np.convolve(duck, kern, mode='same')
duck[:len(kern)] = duck[len(kern)]
duck[-len(kern):] = duck[-len(kern)]

DUCK_ON = "--no-duck" not in sys.argv
d = duck if DUCK_ON else np.ones(N)
fade = np.ones(N)
fade[:int(0.02*SR)] = np.linspace(0, 1, int(0.02*SR))
fo = int(0.45*SR); fade[-fo:] = np.linspace(1, 0, fo)
stem_music = np.vstack([music[0], music[1]]) * d * 0.85 * fade
stem_sfx = np.vstack([sfx[0], sfx[1]]) * (0.55 + 0.45*d) * fade
mix = stem_music + stem_sfx

# ── loudness: BS.1770 K-weighting, then normalise to −14 LUFS ──────────────
def k_weight(x):
    # stage 1: high shelf, stage 2: high pass (48 kHz coefficients)
    b1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
    a1 = [1.0, -1.69065929318241, 0.73248077421585]
    b2 = [1.0, -2.0, 1.0]
    a2 = [1.0, -1.99004745483398, 0.99007225036621]
    y = biquad(x, b1, a1)
    return biquad(y, b2, a2)

def lufs(stereo):
    ks = [k_weight(stereo[c]) for c in range(2)]
    blk = int(0.400*SR); hop = int(0.100*SR)
    loud = []
    for i in range(0, len(ks[0])-blk, hop):
        z = sum(np.mean(k[i:i+blk]**2) for k in ks)
        if z <= 0: continue
        loud.append(-0.691 + 10*np.log10(z))
    loud = np.array(loud)
    gated = loud[loud > -70]
    if len(gated) == 0: return -70.0
    rel = gated.mean() - 10
    g2 = gated[gated > rel]
    return float(g2.mean() if len(g2) else gated.mean())

def limiter(x, ceiling, look=0.006, rel=0.090):
    """block-wise lookahead limiter; returns a GAIN CURVE, not audio, so the
    stems can be given the exact same curve and still sum to the master"""
    B = 64
    n = x.shape[1]
    pad = (-n) % B
    xb = np.pad(np.abs(x).max(axis=0), (0, pad)).reshape(-1, B).max(axis=1)
    w = max(2, int(look*SR/B))
    sl = np.lib.stride_tricks.sliding_window_view(np.pad(xb, (w, w), mode='edge'), 2*w+1).max(axis=1)[:len(xb)]
    g = np.minimum(1.0, ceiling/np.maximum(sl, 1e-9))
    # release smoothing: gain may fall instantly, recovers slowly
    a = math.exp(-B/(rel*SR))
    out = np.empty_like(g); cur = 1.0
    for i in range(len(g)):
        cur = g[i] if g[i] < cur else a*cur + (1-a)*g[i]
        out[i] = cur
    return np.interp(np.arange(n), np.arange(len(out))*B + B/2, out)

def compress(x, thr_db=-20.0, ratio=3.0, atk=0.012, rel=0.180, makeup_db=0.0):
    """bus glue so the drops stay loud without the limiter doing all the work"""
    B = 64
    n = x.shape[1]
    pad = (-n) % B
    env = np.pad(np.abs(x).max(axis=0), (0, pad)).reshape(-1, B).max(axis=1)
    db = 20*np.log10(np.maximum(env, 1e-9))
    over = np.maximum(0.0, db - thr_db)
    gr = -over*(1 - 1/ratio)
    aa = math.exp(-B/(atk*SR)); ar = math.exp(-B/(rel*SR))
    sm = np.empty_like(gr); cur = 0.0
    for i in range(len(gr)):
        c = aa if gr[i] < cur else ar
        cur = c*cur + (1-c)*gr[i]
        sm[i] = cur
    g = 10**((sm + makeup_db)/20)
    return np.interp(np.arange(n), np.arange(len(g))*B + B/2, g)

ceiling = 10**(-1.0/20)
cur = lufs(mix)
G = np.ones(N)                                  # the whole master chain as one gain curve
g = compress(mix, thr_db=-22.0, ratio=3.2, makeup_db=3.0); G *= g; mix = mix*g
for _ in range(4):
    k = 10**((-14.0 - lufs(mix))/20); G *= k; mix = mix*k
    g = limiter(mix, ceiling); G *= g; mix = mix*g

def tp(x):
    up = np.fft.irfft(np.pad(np.fft.rfft(x), (0, len(x)*3//2)), len(x)*4)*4
    return np.max(np.abs(up))
pk = max(tp(mix[0]), tp(mix[1]))
if pk > ceiling:
    k = ceiling/pk; G *= k; mix = mix*k

print(f"LUFS before {cur:.2f} -> {lufs(mix):.2f}   true peak {20*np.log10(max(tp(mix[0]),tp(mix[1]))):.2f} dBTP")

def write24(path, stereo):
    o = (np.clip(stereo.T, -1, 1) * 8388607).astype('<i4')
    raw = o.tobytes()
    b = bytearray()
    for i in range(0, len(raw), 4):
        b += raw[i:i+3]
    with wave.open(path, 'wb') as f:
        f.setnchannels(2); f.setsampwidth(3); f.setframerate(SR)
        f.writeframes(bytes(b))
    print('wrote', path)

mus, sfxs = stem_music*G, stem_sfx*G
write24('out/score.wav', mix)
write24('out/stem_music.wav', mus)
write24('out/stem_sfx.wav', sfxs)
null = np.max(np.abs((mus + sfxs) - mix))
print(f"stems null against the mix at {20*np.log10(max(null,1e-12)):.1f} dBFS")

json.dump({"duck_db": -9, "bpm": BPM, "words": VO_WORDS}, open('out/score_meta.json', 'w'), indent=1)
