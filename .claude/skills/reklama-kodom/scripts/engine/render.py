"""Render: motion blur, post chain, frames -> ffmpeg."""
import argparse, math, os, sys, time
import numpy as np
import cv2

import config as C
import core
from core import clamp, blur_img, Camera
import scenes as S
try:                       # проектный модуль ассетов не обязателен
    import assets as A
except ImportError:
    A = None

cv2.setNumThreads(1)

STATE = {}


def mb_samples(t, scale=1.0):
    """Сколько подкадров усреднять в моушн-блюре на момент t.

    Это свойство конкретного ролика: на ударе и на пролёте нужно 6-7, на
    спокойной сцене хватает 2, а равномерные 6 по всему хронометражу просто
    утраивают время рендера. Поэтому проект может задать свою функцию
    mb_samples(t) в scenes.py; здесь — безопасный запас по умолчанию.
    """
    if hasattr(S, "mb_samples"):
        n = S.mb_samples(t)
    else:
        n = 2
    return max(1, n // 2) if scale < 0.75 else n


def setup(fmt, scale):
    f = C.FORMATS[fmt]
    w, h = int(f["w"] * scale), int(f["h"] * scale)
    w -= w % 2; h -= h % 2
    if A is not None and hasattr(A, "set_res"):
        # текстуры в вертикали крупнее на экране — рисуем их с запасом
        A.set_res((1.0 if f["w"] >= f["h"] else 1.30) * scale)
    L = S.layout(dict(w=w, h=h))
    cam = Camera(w, h, f["fov"])
    # vignette
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx / w - .5) * 2) ** 2 + ((yy / h - .5) * 2) ** 2) / 1.414
    vig = np.clip(1.0 - (d ** 2.2) * C.VIGNETTE, 0, 1).astype(np.float32)
    # grain
    rng = np.random.default_rng(11)
    grains = [cv2.resize(rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32),
                         (w, h), interpolation=cv2.INTER_LINEAR) for _ in range(6)]
    # chromatic aberration maps
    k = 0.0013
    mx = (xx - w / 2); my = (yy - h / 2)
    mapRx = (w / 2 + mx * (1 + k)).astype(np.float32); mapRy = (h / 2 + my * (1 + k)).astype(np.float32)
    mapBx = (w / 2 + mx * (1 - k)).astype(np.float32); mapBy = (h / 2 + my * (1 - k)).astype(np.float32)
    STATE.update(w=w, h=h, L=L, cam=cam, vig=vig, grains=grains,
                 ca=(mapRx, mapRy, mapBx, mapBy), scale=scale, fmt=fmt)
    return STATE


def zoom_blur(img, amount, n=7):
    if amount < 0.003:
        return img
    h, w = img.shape[:2]
    acc = img.copy()
    for i in range(1, n):
        s = 1.0 + amount * i / n
        M = np.float32([[s, 0, w / 2 * (1 - s)], [0, s, h / 2 * (1 - s)]])
        acc += cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REPLICATE)
    return acc / n


def post(img, fx, fi):
    w, h = STATE["w"], STATE["h"]
    if fx.get("zoom", 0) > 0.003:
        img = zoom_blur(img, fx["zoom"])
    if fx.get("blur", 0) > 0.35:
        img = blur_img(img, fx["blur"])
    # bloom
    sm = cv2.resize(img, (w // 4, h // 4), interpolation=cv2.INTER_AREA)
    br = np.clip(sm - 0.62, 0, None)
    b = cv2.GaussianBlur(br, (0, 0), 5.0) * 0.75 + cv2.GaussianBlur(br, (0, 0), 17.0) * 0.55
    img = img + cv2.resize(b, (w, h), interpolation=cv2.INTER_LINEAR) * C.BLOOM * fx.get("glow", 1.0)
    # chromatic aberration
    mRx, mRy, mBx, mBy = STATE["ca"]
    img[:, :, 0] = cv2.remap(img[:, :, 0], mBx, mBy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    img[:, :, 2] = cv2.remap(img[:, :, 2], mRx, mRy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    img *= STATE["vig"][:, :, None]
    img += STATE["grains"][fi % 6][:, :, None] * C.GRAIN
    # filmic shoulder
    knee = 0.78
    hi = img > knee
    img[hi] = knee + (1 - knee) * (1 - np.exp(-(img[hi] - knee) / (1 - knee)))
    np.clip(img, 0, 1, out=img)
    return img


def render_frame(fi):
    L, cam = STATE["L"], STATE["cam"]
    t0 = fi / C.FPS
    n = mb_samples(t0, STATE["scale"])
    acc = None
    fx = {}
    for i in range(n):
        t = t0 + (i / n - 0.5) * C.SHUTTER / C.FPS if n > 1 else t0
        buf = np.zeros((STATE["h"], STATE["w"], 3), np.float32)
        cam.shift = (0.0, 0.0)
        cam.zoom = 1.0
        f2 = {}
        S.render_scene(buf, L, max(0.0, t), cam, f2)
        if i == n // 2:
            fx = f2
        acc = buf if acc is None else acc + buf
    acc /= n
    img = post(acc, fx, fi)
    return (img * 255.0 + 0.5).astype(np.uint8)


def worker(args):
    fi, outdir = args
    im = render_frame(fi)
    cv2.imwrite(os.path.join(outdir, "%05d.png" % fi), im[:, :, ::-1],
                [cv2.IMWRITE_PNG_COMPRESSION, 1])
    return fi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fmt", default="16x9")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=C.DUR)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--stills", default=None, help="comma separated times -> png")
    a = ap.parse_args()
    setup(a.fmt, a.scale)
    if a.stills:
        os.makedirs("out", exist_ok=True)
        for s in a.stills.split(","):
            fi = int(round(float(s) * C.FPS))
            im = render_frame(fi)
            p = "out/still_%s_%s.png" % (a.fmt, s.replace(".", "_"))
            cv2.imwrite(p, im[:, :, ::-1])
            print("wrote", p)
        return
    outdir = a.outdir or ("frames/%s" % a.fmt)
    os.makedirs(outdir, exist_ok=True)
    f0 = int(round(a.start * C.FPS))
    f1 = min(C.NFRAMES, int(round(a.end * C.FPS)))
    todo = [(fi, outdir) for fi in range(f0, f1)]
    t0 = time.time()
    if a.jobs > 1:
        import multiprocessing as mp
        with mp.Pool(a.jobs) as p:
            for k, _ in enumerate(p.imap_unordered(worker, todo, chunksize=4)):
                if k % 60 == 0:
                    el = time.time() - t0
                    print("  %d/%d  %.1fs  eta %.0fs" % (k, len(todo), el,
                          el / max(k, 1) * (len(todo) - k)), flush=True)
    else:
        for k, job in enumerate(todo):
            worker(job)
            if k % 20 == 0:
                print("  %d/%d %.1fs" % (k, len(todo), time.time() - t0), flush=True)
    print("done %d frames in %.1fs" % (len(todo), time.time() - t0))


if __name__ == "__main__":
    main()
