#!/usr/bin/env python3
"""Синтез звуковых акцентов: без библиотеки сэмплов, всё считается numpy.

Звуки намеренно простые и короткие — их задача подчеркнуть появление оверлея,
а не звучать сами по себе. Каждая функция возвращает моно-массив float32.
"""
import numpy as np

SR = 48000


def _env(n, attack=0.005, decay=None, power=2.2):
    """Огибающая: быстрый вход, экспоненциальный спад."""
    a = max(1, int(attack * SR))
    e = np.ones(n, dtype=np.float32)
    e[:a] = np.linspace(0, 1, a, dtype=np.float32)
    rest = n - a
    if rest > 0:
        t = np.linspace(0, 1, rest, dtype=np.float32)
        e[a:] = (1 - t) ** power
    return e


def _noise(n):
    return np.random.default_rng(7).standard_normal(n).astype(np.float32)


def _onepole(x, cutoff):
    """Фильтр низких частот с плавающей частотой среза (cutoff — массив Гц)."""
    a = np.exp(-2 * np.pi * np.asarray(cutoff, dtype=np.float32) / SR)
    y = np.empty_like(x)
    prev = np.float32(0)
    for i in range(x.size):
        prev = (1 - a[i]) * x[i] + a[i] * prev
        y[i] = prev
    return y


def whoosh(dur=0.45):
    """Смаз: шум, по которому снизу вверх и обратно проезжает срез."""
    n = int(dur * SR)
    t = np.linspace(0, 1, n, dtype=np.float32)
    cutoff = 400 + 6000 * np.abs(np.sin(np.pi * t)) ** 1.5
    x = _onepole(_noise(n), cutoff)
    hp = x - _onepole(x, np.full(n, 250.0, dtype=np.float32))
    return hp * _env(n, 0.02, power=1.6) * 0.55


def impact(dur=0.6):
    """Удар: низкий тон с уходом вниз плюс щелчок сверху."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    freq = 110 * np.exp(-9 * t) + 42
    body = np.sin(2 * np.pi * np.cumsum(freq) / SR).astype(np.float32)
    body *= _env(n, 0.002, power=3.0)
    cn = int(0.02 * SR)
    click = np.zeros(n, dtype=np.float32)
    nz = _noise(cn)
    click[:cn] = (nz - _onepole(nz, np.full(cn, 1200.0, dtype=np.float32))) \
        * _env(cn, 0.001, power=4.0)
    return (body * 0.85 + click * 0.45)


def click(dur=0.09):
    """Тик: короткий щелчок для серии мелких событий."""
    n = int(dur * SR)
    x = _noise(n)
    hp = x - _onepole(x, np.full(n, 2500.0, dtype=np.float32))
    return hp * _env(n, 0.001, power=5.0) * 0.5


def riser(dur=1.1):
    """Подъём: тон и шум ползут вверх, подводят к акценту."""
    n = int(dur * SR)
    t = np.linspace(0, 1, n, dtype=np.float32)
    freq = 180 * (1 + 7 * t ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR).astype(np.float32)
    nz = _onepole(_noise(n), 800 + 7000 * t ** 2)
    env = (t ** 2).astype(np.float32)
    return (tone * 0.35 + nz * 0.5) * env * 0.6


def pop(dur=0.25):
    """Появление карточки: мягкий щелчок с коротким тоном."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    freq = 900 * np.exp(-18 * t) + 220
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR).astype(np.float32)
    return tone * _env(n, 0.002, power=3.5) * 0.45


KINDS = {"whoosh": whoosh, "impact": impact, "click": click,
         "riser": riser, "pop": pop}


def write_wav(path, data, gain_db=0.0):
    import wave
    x = np.nan_to_num(np.asarray(data, dtype=np.float32), nan=0.0,
                      posinf=0.0, neginf=0.0) * (10 ** (gain_db / 20.0))
    peak = float(np.max(np.abs(x))) or 1.0
    x = np.clip(x / max(1.0, peak) * 0.9, -1, 1)
    pcm = (x * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    for name, fn in KINDS.items():
        print(write_wav(f"{out}/{name}.wav", fn()))


def bed(dur, bpm=104, key=55.0):
    """Музыкальная подложка: пульс, бас и пара аккордов. Намеренно простая —
    её задача заполнить паузы и сузить динамику, а не звучать на первом плане."""
    n = int(dur * SR)
    t = np.arange(n, dtype=np.float32) / SR
    beat = 60.0 / bpm
    out = np.zeros(n, dtype=np.float32)

    # пульс: бочка на каждую долю
    k = impact(0.34)
    for i in range(int(dur / beat)):
        p = int(i * beat * SR)
        m = min(k.size, n - p)
        if m > 0:
            out[p:p + m] += k[:m] * (0.5 if i % 4 else 0.75)

    # закрытый хэт на слабую долю
    h = click(0.06)
    for i in range(int(dur / (beat / 2))):
        if i % 2 == 0:
            continue
        p = int(i * (beat / 2) * SR)
        m = min(h.size, n - p)
        if m > 0:
            out[p:p + m] += h[:m] * 0.22

    # бас и минорное трезвучие, смена аккорда каждые 4 такта
    bars = np.floor(t / (beat * 4)).astype(np.int32)
    root = key * np.where(bars % 2 == 0, 1.0, 1.1892)   # i -> III
    bass = np.sin(2 * np.pi * np.cumsum(root) / SR).astype(np.float32)
    pad = np.zeros(n, dtype=np.float32)
    for mult in (2.0, 2.3784, 3.0):
        pad += np.sin(2 * np.pi * np.cumsum(root * mult) / SR).astype(np.float32)
    swell = 0.5 + 0.5 * np.sin(2 * np.pi * t / (beat * 8))
    return out * 0.55 + bass * 0.30 + pad * 0.055 * swell
