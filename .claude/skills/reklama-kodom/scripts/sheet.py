import sys, glob, os
from PIL import Image, ImageDraw, ImageFont
files = sys.argv[2:] if len(sys.argv) > 2 else sorted(glob.glob("out/still_*.png"))
cols = int(os.environ.get("COLS", 4))
tw = int(os.environ.get("TW", 480))
ims = []
for f in files:
    im = Image.open(f).convert("RGB")
    th = int(tw * im.height / im.width)
    im = im.resize((tw, th), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    lbl = os.path.basename(f).replace("still_", "").replace(".png", "").replace("_", ".")
    d.rectangle((0, 0, 150, 26), fill=(0, 0, 0))
    d.text((6, 5), lbl, fill=(255, 180, 60),
           font=ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 16))
    ims.append(im)
rh = max(im.height for im in ims)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * rh), (20, 20, 20))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * tw, (i // cols) * rh))
sheet.save(sys.argv[1])
print(sys.argv[1], sheet.size)
