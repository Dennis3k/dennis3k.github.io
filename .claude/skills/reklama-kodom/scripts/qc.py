"""Quality check: luminance curve over the whole film (pops, hand-overs) and
frame-by-frame strips around the hits."""
import subprocess, sys, os, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import config as C

FDIR = sys.argv[1] if len(sys.argv) > 1 else "frames/16x9"
TAG = os.path.basename(FDIR)


def curve():
    files = sorted(glob.glob(FDIR + "/*.png"))
    lum, mx = [], []
    for f in files:
        a = np.asarray(Image.open(f).convert("L").resize((160, 90)), np.float32) / 255
        lum.append(a.mean())
        mx.append(a.max())
    lum, mx = np.array(lum), np.array(mx)
    d = np.abs(np.diff(lum))
    print("frames %d  mean %.4f" % (len(lum), lum.mean()))
    print("biggest frame-to-frame jumps (t, delta):")
    for i in np.argsort(-d)[:12]:
        print("   t=%6.3f  d=%.4f   (%.4f -> %.4f)" % (i / C.FPS, d[i], lum[i], lum[i + 1]))
    dark = [i / C.FPS for i in range(len(lum)) if lum[i] < 0.004]
    if dark:
        print("near-black frames:", ["%.2f" % x for x in dark[:20]])
    else:
        print("no near-black frames")
    return lum


def strip(times, name, cols=6, tw=320):
    ims = []
    fnt = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 15)
    for t in times:
        fi = int(round(t * C.FPS))
        p = "%s/%05d.png" % (FDIR, fi)
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB")
        im = im.resize((tw, int(tw * im.height / im.width)), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 96, 24), fill=(0, 0, 0))
        d.text((5, 4), "%.3f" % t, fill=(255, 170, 40), font=fnt)
        ims.append(im)
    rows = (len(ims) + cols - 1) // cols
    rh = max(i.height for i in ims)
    sh = Image.new("RGB", (cols * tw, rows * rh), (18, 18, 18))
    for i, im in enumerate(ims):
        sh.paste(im, ((i % cols) * tw, (i // cols) * rh))
    sh.save("out/qc_%s_%s.png" % (TAG, name))
    print("out/qc_%s_%s.png" % (TAG, name))


if __name__ == "__main__":
    curve()
    strip([0.133 + i / 60 for i in range(12)], "slam")
    strip([C.TAP - 0.05 + i / 60 for i in range(12)], "tap")
    strip([C.DROP - 0.1 + i / 60 for i in range(12)], "drop")
    strip([C.WRAP - 0.08 + i / 60 for i in range(12)], "wrap")
    strip([C.HERO_HIT - 0.08 + i / 60 for i in range(12)], "hero")
    strip([4.74 + i / 60 for i in range(12)], "xfade_page")
    strip([9.96 + i / 60 for i in range(12)], "xfade_door")
    strip([13.26 + i / 60 for i in range(12)], "xfade_type")
