"""THE line.

One continuous orange line of light does every job in this film: the smile under
the wordmark, the search field's focus line, the Buy Now fill, the delivery route,
the wrap on the box, the arrow from A to Z.  Every one of those is drawn by
draw_line() below - one shared function, so the line is identical everywhere.
"""
import math
import numpy as np
import cv2

import config as C
from core import blur_img, add_rgb, clamp, lerp, smooth

SHIFT = 4
SC = 1 << SHIFT

ACCENT = np.float32(C.nrm(C.ACCENT))
HOT = np.float32(C.nrm(C.ACCENT_HOT)) * 0.45 + np.float32([1.0, 0.95, 1.0]) * 0.55
INK = np.float32([0.52, 0.06, 0.42])


# ------------------------------------------------------------------ path
class Path:
    """a 2d screen-space polyline, resampled by arc length"""

    def __init__(self, pts, samples=260, closed=False):
        p = np.asarray(pts, np.float64)
        if closed:
            p = np.vstack([p, p[:1]])
        if len(p) < 2:
            p = np.vstack([p, p])
        d = np.linalg.norm(np.diff(p, axis=0), axis=1)
        cl = np.concatenate([[0], np.cumsum(d)])
        self.length = float(cl[-1])
        if self.length < 1e-6:
            self.pts = np.repeat(p[:1], samples, 0)
            self.u = np.linspace(0, 1, samples)
            return
        u = cl / cl[-1]
        tu = np.linspace(0, 1, samples)
        self.pts = np.stack([np.interp(tu, u, p[:, 0]), np.interp(tu, u, p[:, 1])], 1)
        self.u = tu

    @classmethod
    def from3d(cls, cam, pts3d, samples=260, closed=False):
        p = np.asarray(pts3d, np.float64)
        if closed:
            p = np.vstack([p, p[:1]])
        s, _ = cam.project(p)
        return cls(s, samples=samples)

    @classmethod
    def arc(cls, cx, cy, rx, ry, a0, a1, n=90, samples=260):
        a = np.linspace(math.radians(a0), math.radians(a1), n)
        return cls(np.stack([cx + rx * np.cos(a), cy + ry * np.sin(a)], 1), samples)

    @classmethod
    def bezier(cls, p0, p1, p2, p3, n=90, samples=260):
        t = np.linspace(0, 1, n)[:, None]
        p0, p1, p2, p3 = map(lambda v: np.asarray(v, np.float64), (p0, p1, p2, p3))
        pts = ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
               + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
        return cls(pts, samples)

    def sub(self, u0, u1):
        u0, u1 = clamp(u0), clamp(u1)
        if u1 <= u0:
            return None
        i0 = np.searchsorted(self.u, u0)
        i1 = np.searchsorted(self.u, u1)
        seg = self.pts[max(0, i0 - 1):min(len(self.pts), i1 + 1)]
        a, b = self.at(u0), self.at(u1)
        if len(seg) < 1:
            return np.array([a, b])
        return np.vstack([[a], seg, [b]])

    def at(self, u):
        u = clamp(u)
        x = np.interp(u, self.u, self.pts[:, 0])
        y = np.interp(u, self.u, self.pts[:, 1])
        return np.array([x, y])

    def tangent(self, u):
        d = 0.004
        a, b = self.at(u - d), self.at(u + d)
        v = b - a
        n = np.linalg.norm(v)
        return v / n if n > 1e-9 else np.array([1.0, 0.0])

    def offset(self, dx, dy):
        p = Path.__new__(Path)
        p.pts = self.pts + np.array([dx, dy])
        p.u = self.u
        p.length = self.length
        return p


# ------------------------------------------------------------------ drawing
def _stroke(mask, pts, width, vals, x0, y0):
    """antialiased variable-width, variable-intensity polyline into a float mask"""
    n = len(pts)
    if n < 2:
        return
    for i in range(n - 1):
        v = float(vals[i])
        if v <= 0.004:
            continue
        w = max(0.55, float(width[i]))
        th = max(1, int(round(w)))
        a = v * min(1.0, w / th) if th > w else v
        p0 = (int((pts[i][0] - x0) * SC), int((pts[i][1] - y0) * SC))
        p1 = (int((pts[i + 1][0] - x0) * SC), int((pts[i + 1][1] - y0) * SC))
        cv2.line(mask, p0, p1, float(a), th, cv2.LINE_AA, SHIFT)


def draw_line(dst, path, u0=0.0, u1=1.0, width=6.0, heat=1.0, glow=1.0,
              cool=0.0, head=True, head_scale=1.0, opacity=1.0, taper=0.18,
              blur=0.0, color=None, core=True):
    """Draw the light line.

    cool: 0 = white-hot light, 1 = printed matte ink (no emission).
    """
    if u1 <= u0 or opacity <= 0.003:
        return
    pts = path.sub(u0, u1)
    if pts is None or len(pts) < 2:
        return
    H, W = dst.shape[:2]
    pad = int(width * 2 + 40 + blur * 3)
    x0 = int(max(-pad, pts[:, 0].min() - pad))
    y0 = int(max(-pad, pts[:, 1].min() - pad))
    x1 = int(min(W + pad, pts[:, 0].max() + pad))
    y1 = int(min(H + pad, pts[:, 1].max() + pad))
    bw, bh = x1 - x0, y1 - y0
    if bw <= 2 or bh <= 2 or bw * bh > 30_000_000:
        return
    n = len(pts)
    s = np.linspace(0, 1, n)                      # 0 tail -> 1 head
    tap = np.clip(s / max(taper, 1e-3), 0, 1) ** 0.7 if taper > 0 else np.ones(n)
    wid = width * (0.45 + 0.55 * tap)
    if head:
        wid = wid * (1.0 + 0.38 * np.clip((s - 0.86) / 0.14, 0, 1) ** 2 * head_scale)
    inten = (0.55 + 0.45 * tap) * opacity

    body = np.zeros((bh, bw), np.float32)
    _stroke(body, pts, wid, inten, x0, y0)

    col = ACCENT if color is None else np.float32(color)
    warm = col * (1.0 + 0.25 * heat)

    if cool < 0.999:
        g = glow * (1.0 - cool)
        for sig, wgt in ((1.6, 1.0), (6.0, 0.55), (20.0, 0.34), (54.0, 0.20)):
            m = blur_img(body, sig)
            add_rgb(dst, m[:, :, None] * warm.reshape(1, 1, 3), x0, y0, 0.95 * g * wgt * heat)

    if cool > 0.004:
        # printed ink: alpha composite, matte
        a = np.clip(body, 0, 1)[:, :, None] * cool
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(W, x1), min(H, y1)
        if xb > xa and yb > ya:
            sa = a[ya - y0:yb - y0, xa - x0:xb - x0]
            d = dst[ya:yb, xa:xb]
            d *= (1.0 - sa)
            d += sa * INK.reshape(1, 1, 3)

    if core and cool < 0.9:
        cmask = np.zeros((bh, bw), np.float32)
        ci = inten * np.clip((s - 0.0), 0, 1) * (0.35 + 0.65 * np.clip((s - 0.5) / 0.5, 0, 1))
        _stroke(cmask, pts, np.maximum(1.0, wid * 0.34), ci * (1 - cool), x0, y0)
        white = lerp(ACCENT, HOT, 0.85 * heat)
        add_rgb(dst, cmask[:, :, None] * white.reshape(1, 1, 3), x0, y0, 1.25 * opacity)
        add_rgb(dst, blur_img(cmask, 3.0)[:, :, None] * white.reshape(1, 1, 3),
                x0, y0, 0.7 * opacity)

    if head and cool < 0.9 and u1 < 0.9995:
        hp = path.at(u1)
        head_blob(dst, hp, width * 2.4 * head_scale, heat * opacity * (1 - cool))


def head_blob(dst, p, r, amount=1.0):
    """the hot leading edge"""
    if amount <= 0.004:
        return
    r = max(4.0, r)
    R = int(r * 7)
    H, W = dst.shape[:2]
    x0, y0 = int(p[0]) - R, int(p[1]) - R
    if x0 > W or y0 > H or x0 + 2 * R < 0 or y0 + 2 * R < 0:
        return
    m = np.zeros((2 * R, 2 * R), np.float32)
    cv2.circle(m, (R, R), max(1, int(r * 0.5)), 1.0, -1, cv2.LINE_AA)
    g1 = blur_img(m, r * 0.5)
    g2 = blur_img(m, r * 2.0)
    add_rgb(dst, g1[:, :, None] * HOT.reshape(1, 1, 3), x0, y0, 2.0 * amount)
    add_rgb(dst, g2[:, :, None] * ACCENT.reshape(1, 1, 3), x0, y0, 1.6 * amount)


def shards(dst, p, n, spread, length, amount, seed=0, angle=None):
    """light shards thrown off an impact"""
    if amount <= 0.004:
        return
    rng = np.random.default_rng(seed)
    R = int(length * 1.6) + 30
    H, W = dst.shape[:2]
    x0, y0 = int(p[0]) - R, int(p[1]) - R
    bw = bh = 2 * R
    if x0 > W or y0 > H or x0 + bw < 0 or y0 + bh < 0:
        return
    m = np.zeros((bh, bw), np.float32)
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi) if angle is None else angle + rng.normal(0, spread)
        l = length * rng.uniform(0.25, 1.0)
        r0 = length * rng.uniform(0.02, 0.25)
        w = max(1, int(rng.uniform(1, 3)))
        p0 = (int((R + math.cos(a) * r0) * SC), int((R + math.sin(a) * r0) * SC))
        p1 = (int((R + math.cos(a) * (r0 + l)) * SC), int((R + math.sin(a) * (r0 + l)) * SC))
        cv2.line(m, p0, p1, float(rng.uniform(0.4, 1.0)), w, cv2.LINE_AA, SHIFT)
    add_rgb(dst, m[:, :, None] * HOT.reshape(1, 1, 3), x0, y0, 1.1 * amount)
    add_rgb(dst, blur_img(m, 7.0)[:, :, None] * ACCENT.reshape(1, 1, 3), x0, y0, 1.5 * amount)


def streak(dst, p0, p1, width, amount, heat=1.0):
    """a single straight light streak (the incoming slam)"""
    pth = Path([p0, p1], samples=60)
    draw_line(dst, pth, 0, 1, width=width, heat=heat, glow=1.25, opacity=amount,
              taper=0.55, head=False)
