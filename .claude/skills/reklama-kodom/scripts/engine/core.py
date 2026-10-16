"""Core 2.5D renderer: easing, camera, quad warping, glow, texture helpers."""
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

import config as C

cv2.setNumThreads(1)

# ===================================================================== easing
def clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)

def lerp(a, b, t):
    return a + (b - a) * t

def smooth(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)

def smoother(t):
    t = clamp(t)
    return t * t * t * (t * (t * 6 - 15) + 10)

def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3

def ease_out_quint(t):
    t = clamp(t)
    return 1 - (1 - t) ** 5

def ease_out_expo(t):
    t = clamp(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-11 * t)

def ease_in_cubic(t):
    t = clamp(t)
    return t ** 3

def ease_in_quint(t):
    t = clamp(t)
    return t ** 5

def ease_in_out_cubic(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2

def ease_in_out_quint(t):
    t = clamp(t)
    return 16 * t ** 5 if t < 0.5 else 1 - (-2 * t + 2) ** 5 / 2

def ease_out_back(t, s=1.5):
    t = clamp(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2

def ease_out_elastic(t, p=0.35, decay=7.0):
    t = clamp(t)
    if t <= 0 or t >= 1:
        return clamp(t)
    return 1 - math.exp(-decay * t) * math.cos(2 * math.pi * t / p)

EASES = {
    None: lambda t: t, "lin": lambda t: t, "smooth": smooth, "smoother": smoother,
    "oc": ease_out_cubic, "oq": ease_out_quint, "oe": ease_out_expo,
    "ic": ease_in_cubic, "iq": ease_in_quint,
    "ioc": ease_in_out_cubic, "ioq": ease_in_out_quint,
    "back": ease_out_back, "elastic": ease_out_elastic,
}

def seg(t, t0, t1, ease="smooth"):
    """normalised, eased progress of t across [t0, t1]"""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return EASES[ease](clamp((t - t0) / (t1 - t0)))

def kf(t, keys):
    """keys = [(time, value, ease_into_this_key), ...] ; scalars or tuples"""
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    for i in range(len(keys) - 1):
        t0, v0 = keys[i][0], keys[i][1]
        t1, v1 = keys[i + 1][0], keys[i + 1][1]
        if t0 <= t <= t1:
            e = keys[i + 1][2] if len(keys[i + 1]) > 2 else "smooth"
            u = EASES[e](clamp((t - t0) / (t1 - t0))) if t1 > t0 else 1.0
            if isinstance(v0, (tuple, list)):
                return tuple(lerp(a, b, u) for a, b in zip(v0, v1))
            return lerp(v0, v1, u)
    return keys[-1][1]

def noise1(t, seed=0.0, f=1.0):
    """cheap smooth 1d noise in [-1,1]"""
    x = t * f + seed
    return (math.sin(x * 1.7) * 0.6 + math.sin(x * 3.11 + 1.3) * 0.3
            + math.sin(x * 6.7 + 2.9) * 0.1)

# ===================================================================== camera
def _n(v):
    l = np.linalg.norm(v)
    return v / l if l > 1e-9 else v

class Camera:
    def __init__(self, w, h, fov):
        self.w, self.h = w, h
        self.fov = fov
        self.focal = (h * 0.5) / math.tan(math.radians(fov) * 0.5)
        self.pos = np.array([0, 0, -4.0], np.float64)
        self.target = np.array([0, 0, 0.0], np.float64)
        self.roll = 0.0
        self.focus = 4.0       # depth of field focal distance
        self.dof = 0.0         # blur px per unit of defocus
        self.shift = (0.0, 0.0)  # 2d screen shift in px (shake)
        self.zoom = 1.0

    def set(self, pos, target, roll=0.0, fov=None):
        self.pos = np.array(pos, np.float64)
        self.target = np.array(target, np.float64)
        self.roll = roll
        if fov is not None:
            self.fov = fov
            self.focal = (self.h * 0.5) / math.tan(math.radians(fov) * 0.5)
        f = _n(self.target - self.pos)
        up = np.array([0, 1, 0], np.float64)
        if abs(np.dot(f, up)) > 0.995:
            up = np.array([0, 0, 1], np.float64)
        r = _n(np.cross(up, f))
        u = np.cross(f, r)
        if roll:
            cr, sr = math.cos(roll), math.sin(roll)
            r, u = r * cr + u * sr, -r * sr + u * cr
        self._b = np.stack([r, u, f])     # 3x3 rows

    def project(self, pts):
        """pts (N,3) world -> (N,2) screen px, (N,) view depth"""
        p = np.atleast_2d(np.asarray(pts, np.float64)) - self.pos
        v = p @ self._b.T
        z = np.maximum(v[:, 2], 1e-4)
        k = self.focal * self.zoom / z
        sx = self.w * 0.5 + v[:, 0] * k + self.shift[0]
        sy = self.h * 0.5 - v[:, 1] * k + self.shift[1]
        return np.stack([sx, sy], 1), v[:, 2]

    def p2(self, pt):
        s, _ = self.project([pt])
        return (float(s[0, 0]), float(s[0, 1]))

    def blur_for(self, z):
        return min(28.0, abs(z - self.focus) * self.dof)

    def scale_at(self, z):
        return self.focal * self.zoom / max(z, 1e-4)

# ===================================================================== canvas
def canvas(w, h):
    return np.zeros((h, w, 3), np.float32)

def blur_img(img, sigma):
    if sigma < 0.35:
        return img
    if sigma > 7:
        f = max(1, int(sigma / 3.5))
        small = cv2.resize(img, (max(2, img.shape[1] // f), max(2, img.shape[0] // f)),
                           interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), sigma / f)
        return cv2.resize(small, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)
    return cv2.GaussianBlur(img, (0, 0), sigma)

def comp_premul(dst, src, x, y):
    """composite premultiplied RGBA float32 src at integer x,y into dst RGB"""
    h, w = src.shape[:2]
    H, W = dst.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    d = dst[y0:y1, x0:x1]
    a = s[:, :, 3:4]
    d *= (1.0 - a)
    d += s[:, :, :3]

def blit(dst, rgba, x, y, opacity=1.0, blur=0.0, premul=False):
    """place straight-alpha RGBA float32 at x,y (floats ok -> subpixel via shift)"""
    if rgba is None:
        return
    img = rgba
    if not premul:
        img = img.copy()
        img[:, :, :3] *= img[:, :, 3:4]
    if opacity != 1.0:
        img = img * np.float32(opacity)
    xi, yi = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - xi, y - yi
    if fx > 0.01 or fy > 0.01:
        M = np.float32([[1, 0, fx], [0, 1, fy]])
        img = cv2.warpAffine(img, M, (img.shape[1] + 1, img.shape[0] + 1),
                             flags=cv2.INTER_LINEAR, borderValue=0)
    if blur > 0.35:
        pad = int(blur * 3)
        img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
        img = blur_img(img, blur)
        xi -= pad
        yi -= pad
    comp_premul(dst, img, xi, yi)

def warp_quad(dst, tex, corners, opacity=1.0, blur=0.0, premul=False):
    """tex: RGBA float32 (th,tw,4) straight alpha. corners: 4x2 screen px, TL TR BR BL."""
    H, W = dst.shape[:2]
    c = np.asarray(corners, np.float32)
    if not np.isfinite(c).all():
        return
    pad = int(blur * 3) + 2
    x0 = int(math.floor(c[:, 0].min())) - pad
    y0 = int(math.floor(c[:, 1].min())) - pad
    x1 = int(math.ceil(c[:, 0].max())) + pad
    y1 = int(math.ceil(c[:, 1].max())) + pad
    x0c, y0c = max(0, x0), max(0, y0)
    x1c, y1c = min(W, x1), min(H, y1)
    if x1c <= x0c or y1c <= y0c:
        return
    bw, bh = x1c - x0c, y1c - y0c
    if bw * bh > 40_000_000:
        return
    th, tw = tex.shape[:2]
    src = np.float32([[0, 0], [tw, 0], [tw, th], [0, th]])
    M = cv2.getPerspectiveTransform(src, c - np.float32([x0c, y0c]))
    t = tex
    if not premul:
        t = tex.copy()
        t[:, :, :3] *= t[:, :, 3:4]
    w = cv2.warpPerspective(t, M, (bw, bh), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    if blur > 0.35:
        w = blur_img(w, blur)
    if opacity != 1.0:
        w = w * np.float32(opacity)
    comp_premul(dst, w, x0c, y0c)

def add_rgb(dst, src_rgb, x, y, amount=1.0):
    h, w = src_rgb.shape[:2]
    H, W = dst.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return
    dst[y0:y1, x0:x1] += src_rgb[y0 - y:y1 - y, x0 - x:x1 - x] * amount

# ===================================================================== glow
def glow_from_mask(dst, mask, color, strength, sigmas=(2.0, 9.0, 30.0),
                   weights=(1.0, 0.55, 0.3), x=0, y=0):
    """mask float32 single channel (any size) -> additive coloured glow"""
    col = np.float32(color).reshape(1, 1, 3)
    for s, wgt in zip(sigmas, weights):
        m = blur_img(mask, s)
        add_rgb(dst, m[:, :, None] * col, x, y, strength * wgt)

# ===================================================================== texture
_FONTS = {}
def font(path, size):
    key = (path, int(size))
    f = _FONTS.get(key)
    if f is None:
        f = ImageFont.truetype(path, int(size))
        _FONTS[key] = f
    return f

class Tex:
    """supersampled RGBA drawing surface -> float32 numpy"""
    SS = 2

    def __init__(self, w, h, ss=None, bg=None):
        self.w, self.h = int(w), int(h)
        self.ss = ss or Tex.SS
        s = self.ss
        col = (0, 0, 0, 0) if bg is None else (bg[0], bg[1], bg[2], 255 if len(bg) < 4 else bg[3])
        self.im = Image.new("RGBA", (self.w * s, self.h * s), col)
        self.d = ImageDraw.Draw(self.im, "RGBA")

    def _c(self, v):
        return [i * self.ss for i in v]

    def rr(self, box, r, fill=None, outline=None, width=1):
        self.d.rounded_rectangle(self._c(box), radius=r * self.ss, fill=fill,
                                 outline=outline, width=max(1, int(width * self.ss)))

    def rect(self, box, fill=None, outline=None, width=1):
        self.d.rectangle(self._c(box), fill=fill, outline=outline,
                         width=max(1, int(width * self.ss)))

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse(self._c(box), fill=fill, outline=outline,
                       width=max(1, int(width * self.ss)))

    def line(self, pts, fill, width=1, joint="curve"):
        p = [(x * self.ss, y * self.ss) for x, y in pts]
        self.d.line(p, fill=fill, width=max(1, int(width * self.ss)), joint=joint)

    def arc(self, box, a0, a1, fill, width=1):
        self.d.arc(self._c(box), a0, a1, fill=fill, width=max(1, int(width * self.ss)))

    def polygon(self, pts, fill=None, outline=None):
        p = [(x * self.ss, y * self.ss) for x, y in pts]
        self.d.polygon(p, fill=fill, outline=outline)

    def text(self, xy, s, fpath, size, fill, anchor="la", tracking=0.0, alpha=255):
        f = font(fpath, size * self.ss)
        col = (fill[0], fill[1], fill[2], alpha)
        x, y = xy[0] * self.ss, xy[1] * self.ss
        if abs(tracking) < 1e-6:
            self.d.text((x, y), s, font=f, fill=col, anchor=anchor)
            return
        tr = tracking * self.ss
        total = sum(f.getlength(ch) + tr for ch in s) - tr
        ax = anchor[0]
        if ax == "m":
            x -= total / 2
        elif ax == "r":
            x -= total
        va = anchor[1]
        for ch in s:
            self.d.text((x, y), ch, font=f, fill=col, anchor="l" + va)
            x += f.getlength(ch) + tr

    def width(self, s, fpath, size, tracking=0.0):
        f = font(fpath, size * self.ss)
        if abs(tracking) < 1e-6:
            return f.getlength(s) / self.ss
        return (sum(f.getlength(c) + tracking * self.ss for c in s) - tracking * self.ss) / self.ss

    def paste_np(self, rgba, x, y):
        im = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), "RGBA")
        im = im.resize((im.width * self.ss, im.height * self.ss), Image.LANCZOS)
        self.im.alpha_composite(im, (int(x * self.ss), int(y * self.ss)))

    def paste_im(self, im, x, y):
        self.im.alpha_composite(im, (int(x * self.ss), int(y * self.ss)))

    def np(self):
        im = self.im
        if self.ss != 1:
            im = im.resize((self.w, self.h), Image.LANCZOS)
        return np.asarray(im, np.float32) / 255.0

# ---- texture cache ------------------------------------------------------
_CACHE = {}
def cached(key, fn):
    v = _CACHE.get(key)
    if v is None:
        if len(_CACHE) > 220:
            _CACHE.clear()
        v = fn()
        _CACHE[key] = v
    return v

# ===================================================================== helpers
def text_rgba(s, fpath, size, color, tracking=0.0, pad=16, ss=3):
    """standalone text as straight-alpha RGBA float32 + (w,h)"""
    probe = Tex(10, 10, ss=1)
    w = probe.width(s, fpath, size, tracking)
    f = font(fpath, size)
    asc, desc = f.getmetrics()
    h = asc + desc
    t = Tex(int(w) + pad * 2, int(h) + pad * 2, ss=ss)
    t.text((pad, pad), s, fpath, size, color, anchor="la", tracking=tracking)
    return t.np()

def glyph_boxes(s, fpath, size, tracking=0.0):
    """per character x offsets and advances at final scale"""
    f = font(fpath, size)
    out, x = [], 0.0
    for ch in s:
        adv = f.getlength(ch)
        out.append((ch, x, adv))
        x += adv + tracking
    return out, x - tracking

def rounded_mask(w, h, r, ss=3):
    t = Tex(w, h, ss=ss)
    t.rr((0, 0, w - 1, h - 1), r, fill=(255, 255, 255, 255))
    return t.np()[:, :, 3]

def vgrad(w, h, c0, c1, vertical=True):
    a = np.linspace(0, 1, h if vertical else w, dtype=np.float32)
    a = a[:, None] if vertical else a[None, :]
    c0 = np.float32(c0).reshape(1, 1, 3) / 255.0
    c1 = np.float32(c1).reshape(1, 1, 3) / 255.0
    g = c0 + (c1 - c0) * a[:, :, None]
    return np.broadcast_to(g, (h, w, 3)).copy()

def radial(w, h, cx, cy, r, power=2.0):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(r, 1e-3)
    return np.clip(1.0 - d, 0, 1) ** power

def shadow_rgba(w, h, r, blur, alpha=0.6, ss=2):
    m = rounded_mask(w, h, r, ss=ss)
    m = blur_img(m, blur)
    out = np.zeros((h, w, 4), np.float32)
    out[:, :, 3] = m * alpha
    return out


# ===================================================================== solidity
def quad_mask(shape, corners, pad=0):
    """filled polygon mask for a projected quad, plus its ROI origin"""
    H, W = shape[:2]
    c = np.asarray(corners, np.float32)
    if not np.isfinite(c).all():
        return None, 0, 0
    x0 = max(0, int(c[:, 0].min()) - pad)
    y0 = max(0, int(c[:, 1].min()) - pad)
    x1 = min(W, int(c[:, 0].max()) + pad + 1)
    y1 = min(H, int(c[:, 1].max()) + pad + 1)
    if x1 <= x0 or y1 <= y0 or (x1 - x0) * (y1 - y0) > 30_000_000:
        return None, 0, 0
    m = np.zeros((y1 - y0, x1 - x0), np.float32)
    cv2.fillPoly(m, [np.int32((c - np.float32([x0, y0])) * 16)], 1.0, cv2.LINE_AA, 4)
    return m, x0, y0


def rim_quad(dst, corners, color, amount=1.0, halo=10.0, light=(-0.55, -0.85),
             edge=1.0, bias=0.18):
    """A lit edge on a solid: a thin bright line just inside the silhouette plus a
    halo hugging it outside, both weighted toward the key light."""
    if amount <= 0.004:
        return
    pad = int(halo * 3) + 4
    m, x0, y0 = quad_mask(dst.shape, corners, pad)
    if m is None:
        return
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = ((xx / max(w - 1, 1) - 0.5) * light[0] + (yy / max(h - 1, 1) - 0.5) * light[1])
    wgt = np.clip(bias + (1.0 - bias) * 2.0 * (d / 0.75 + 0.5), 0, 1.6)
    col = np.float32(color).reshape(1, 1, 3)
    ring = np.clip(blur_img(m, halo) - m, 0, 1) * wgt
    add_rgb(dst, ring[:, :, None] * col, x0, y0, 0.80 * amount)
    add_rgb(dst, blur_img(ring, halo * 2.4)[:, :, None] * col, x0, y0, 0.95 * amount)
    if edge > 0.01:
        k = np.ones((3, 3), np.uint8)
        inner = np.clip(m - cv2.erode(m, k, iterations=2), 0, 1) * wgt
        add_rgb(dst, inner[:, :, None] * col, x0, y0, 0.9 * amount * edge)
        add_rgb(dst, blur_img(inner, 3.5)[:, :, None] * col, x0, y0, 0.8 * amount * edge)


def spill(dst, corners, color, amount=1.0, sigma=70.0):
    """light a bright surface throws onto what is behind it"""
    if amount <= 0.004:
        return
    pad = int(sigma * 1.5)
    m, x0, y0 = quad_mask(dst.shape, corners, pad)
    if m is None:
        return
    col = np.float32(color).reshape(1, 1, 3)
    add_rgb(dst, blur_img(m, sigma)[:, :, None] * col, x0, y0, amount)
    add_rgb(dst, blur_img(m, sigma * 2.6)[:, :, None] * col, x0, y0, amount * 0.7)


def sheen(dst, corners, amount=0.14, angle=-0.6):
    """a soft diagonal reflection across a sheet of glass"""
    if amount <= 0.004:
        return
    m, x0, y0 = quad_mask(dst.shape, corners, 0)
    if m is None:
        return
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx / max(w - 1, 1) - 0.42) * math.cos(angle) + (yy / max(h - 1, 1) - 0.5) * math.sin(angle)
    band = np.exp(-((u - 0.02) ** 2) / 0.020) * 0.85 + np.exp(-((u + 0.30) ** 2) / 0.006) * 0.5
    add_rgb(dst, (m * band)[:, :, None] * np.float32([0.62, 0.70, 0.82]).reshape(1, 1, 3),
            x0, y0, amount)


def proj_clip(cam, pts3, min_z=0.18):
    """project a 3d polyline, dropping anything at or behind the camera plane"""
    sp, z = cam.project(np.asarray(pts3, np.float64))
    ok = z > min_z
    if ok.sum() < 2:
        return None
    return sp[ok]
