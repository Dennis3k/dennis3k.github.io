#!/usr/bin/env python3
"""Оверлеи-виджеты: рисуются в PIL покадрово, собираются в overlay.py.

Каждый рисовальщик получает прогресс p от 0 до 1 и возвращает кадр RGBA
фиксированного размера. Анимация живёт внутри рисовальщика, позиция в кадре —
забота overlay.py.
"""
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/opentype/inter/"
ACCENT = (79, 140, 255, 255)
WHITE = (255, 255, 255, 255)
DIM = (175, 185, 200, 255)
PANEL = (18, 22, 32, 232)


def f(weight, size):
    return ImageFont.truetype(f"{FONT_DIR}Inter-{weight}.otf", size)


def ease(p):
    """Плавный вход: быстро стартует, мягко останавливается."""
    p = max(0.0, min(1.0, p))
    return 1 - (1 - p) ** 3


def seg(p, a, b):
    """Прогресс внутри отрезка [a,b] общего прогресса p."""
    if p <= a:
        return 0.0
    if p >= b:
        return 1.0
    return (p - a) / (b - a)


def panel(d, box, radius=28, fill=PANEL, outline=(255, 255, 255, 28)):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def spaced(n):
    s = f"{int(n):,}".replace(",", " ")
    return s


# --------------------------------------------------------------- профиль
def profile(spec, p):
    W, H = 560, 300
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    slide = int((1 - ease(seg(p, 0, 0.18))) * W)
    panel(d, (slide + 10, 10, slide + W - 10, H - 10))
    x = slide + 44
    d.ellipse((x, 44, x + 72, 116), fill=(70, 80, 110, 255))
    d.text((x + 92, 48), spec.get("name", "account"), font=f("Bold", 30), fill=WHITE)
    d.text((x + 92, 88), spec.get("sub", ""), font=f("Medium", 22), fill=DIM)
    k = ease(seg(p, 0.2, 0.75))
    n = spec.get("from", 0) + (spec.get("to", 0) - spec.get("from", 0)) * k
    d.text((x, 150), spaced(n), font=f("Black", 72), fill=ACCENT)
    d.text((x + 4, 232), spec.get("label", "подписчиков"), font=f("Medium", 24), fill=DIM)
    return img


# ----------------------------------------------------------------- список
def items_list(spec, p):
    rows = spec["items"]
    W = int(spec.get("width", 760))
    sc = W / 760.0                      # вся вёрстка тянется за шириной панели
    pad = int(48 * sc)
    step = int(86 * sc)
    H = int(130 * sc) + step * len(rows) + pad
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    panel(d, (10, 10, W - 10, H - 10), radius=int(28 * sc))
    d.text((pad, pad), spec.get("title", ""), font=f("Black", int(40 * sc)),
           fill=WHITE)
    for i, row in enumerate(rows):
        k = ease(seg(p, 0.12 + i * 0.1, 0.3 + i * 0.1))
        if k <= 0:
            continue
        y = int(130 * sc) + i * step
        dx = int((1 - k) * 60 * sc)
        a = int(255 * k)
        d.text((pad + dx, y), f"{i + 1:02d}", font=f("Black", int(34 * sc)),
               fill=ACCENT[:3] + (a,))
        d.text((pad + int(72 * sc) + dx, y + int(4 * sc)), row,
               font=f("SemiBold", int(30 * sc)), fill=(255, 255, 255, a))
    return img


# -------------------------------------------------------------- ползунки
def sliders(spec, p):
    rows = spec["rows"]
    W, H = 620, 120 + 96 * len(rows)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    slide = int((1 - ease(seg(p, 0, 0.15))) * W)
    panel(d, (slide + 10, 10, slide + W - 10, H - 10))
    d.text((slide + 44, 44), spec.get("title", "СВЕТ"), font=f("Black", 30), fill=WHITE)
    for i, row in enumerate(rows):
        name, a0, a1 = row[0], row[1], row[2]
        p0 = row[3] if len(row) > 3 else 0.25 + i * 0.12
        p1 = row[4] if len(row) > 4 else 0.6 + i * 0.12
        k = ease(seg(p, p0, p1))
        val = a0 + (a1 - a0) * k
        y = 110 + i * 96
        d.text((slide + 44, y), name, font=f("Medium", 26), fill=DIM)
        bx0, bx1 = slide + 44, slide + W - 150
        d.rounded_rectangle((bx0, y + 46, bx1, y + 54), radius=4,
                            fill=(90, 100, 120, 200))
        rel = 0.5 + (val / 40.0 if abs(val) > 2 else val / 4.0) * 0.5
        rel = max(0.05, min(0.95, rel))
        kx = int(bx0 + (bx1 - bx0) * rel)
        d.ellipse((kx - 16, y + 34, kx + 16, y + 66), fill=ACCENT)
        txt = f"{val:+.1f}" if abs(a1) < 5 else f"{val:+.0f}"
        d.text((slide + W - 130, y + 36), txt, font=f("Bold", 26), fill=WHITE)
    return img


# ------------------------------------------------------------ сейчас играет
def nowplaying(spec, p):
    W, H = 500, 150
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    slide = int((1 - ease(seg(p, 0, 0.2))) * -W)
    panel(d, (slide + 10, 10, slide + W - 10, H - 10), radius=24)
    x = slide + 34
    d.rounded_rectangle((x, 34, x + 82, 116), radius=18, fill=ACCENT)
    # нота рисуется руками: в Inter её глифа нет, вместо неё встал бы пустой квадрат
    d.ellipse((x + 22, 78, x + 44, 96), fill=WHITE)
    d.rectangle((x + 41, 44, x + 45, 88), fill=WHITE)
    d.polygon([(x + 45, 44), (x + 60, 50), (x + 45, 58)], fill=WHITE)
    d.text((x + 104, 40), "СЕЙЧАС ИГРАЕТ", font=f("Bold", 20), fill=DIM)
    d.text((x + 104, 68), spec.get("track", ""), font=f("Bold", 28), fill=WHITE)
    d.text((x + 104, 104), spec.get("sub", ""), font=f("Medium", 20), fill=DIM)
    return img


# ---------------------------------------------------------------- таймлайн
TL_COLORS = [(236, 72, 153), (59, 130, 246), (234, 179, 8), (168, 85, 247),
             (34, 197, 94), (249, 115, 22), (14, 165, 233)]


def timeline(spec, p):
    labels = spec["labels"]
    W, H = 900, 300
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = ease(seg(p, 0, 0.18))
    if k <= 0:
        return img
    panel(d, (10, 10, W - 10, H - 10))
    d.rounded_rectangle((40, 48, W - 40, 110), radius=10, fill=(42, 50, 68, 255))
    for i in range(40, W - 40, 26):      # имитация волны
        h = 18 + (i * 7919 % 26)
        d.line((i, 79 - h // 2, i, 79 + h // 2), fill=(120, 190, 255, 220), width=5)
    for i, name in enumerate(labels):
        kk = ease(seg(p, 0.2 + i * 0.07, 0.4 + i * 0.07))
        if kk <= 0:
            continue
        col = TL_COLORS[i % len(TL_COLORS)]
        x = 40 + (i % 4) * 215
        y = 140 + (i // 4) * 70
        w = int(190 * kk)
        d.rounded_rectangle((x, y, x + w, y + 54), radius=12, fill=col + (235,))
        if kk > 0.6:
            d.text((x + 18, y + 13), name, font=f("Bold", 26), fill=(16, 18, 26, 255))
    px = int(40 + (W - 80) * ease(seg(p, 0.15, 1.0)))
    d.line((px, 40, px, H - 30), fill=(255, 255, 255, 220), width=3)
    return img


# ------------------------------------------------------ карточки субтитров
STYLES = [((255, 255, 255), (20, 22, 30)), ((0, 240, 255), (10, 10, 20)),
          ((255, 93, 162), (24, 10, 20)), ((255, 214, 10), (26, 22, 8)),
          ((124, 255, 148), (10, 24, 14)), ((190, 160, 255), (18, 12, 28))]


def stylecards(spec, p):
    word = spec.get("word", "МОНТАЖ")
    W, H = 1000, 900
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    spots = [(10, 60), (690, 20), (0, 330), (700, 300), (30, 620), (680, 590)]
    for i, (fg, bg) in enumerate(STYLES):
        k = ease(seg(p, 0.05 + i * 0.07, 0.35 + i * 0.07))
        if k <= 0:
            continue
        cw, ch = 300, 130
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        a = int(240 * k)
        cd.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=20, fill=bg + (a,),
                             outline=fg + (int(120 * k),), width=2)
        ft = f("Black", 44)
        tw = cd.textbbox((0, 0), word, font=ft)[2]
        cd.text(((cw - tw) // 2, 38), word, font=ft, fill=fg + (int(255 * k),))
        card = card.rotate(-14 + i * 5, expand=True, resample=Image.BICUBIC)
        s = 0.7 + 0.3 * k
        card = card.resize((int(card.width * s), int(card.height * s)),
                           Image.LANCZOS)
        x, y = spots[i]
        img.alpha_composite(card, (x, y + int((1 - k) * 40)))
    return img


# -------------------------------------------------------- поле комментария
def comment(spec, p):
    word = spec.get("word", "монтаж")
    W, H = 820, 130
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    k = ease(seg(p, 0, 0.12))
    if k <= 0:
        return img
    panel(d, (10, 20, W - 10, H - 20), radius=46)
    d.ellipse((34, 38, 106, 110), fill=(70, 80, 110, 255))
    typed = word[:max(0, int(len(word) * seg(p, 0.08, 0.5) + 0.001))]
    d.text((132, 52), typed, font=f("SemiBold", 34), fill=WHITE)
    tw = d.textbbox((0, 0), typed, font=f("SemiBold", 34))[2]
    if int(p * 14) % 2 == 0:
        d.line((138 + tw, 48, 138 + tw, 96), fill=WHITE, width=3)
    d.ellipse((W - 112, 38, W - 40, 110), fill=ACCENT)
    d.polygon([(W - 76, 58), (W - 58, 82), (W - 94, 82)], fill=WHITE)
    return img


RENDERERS = {
    "profile": profile,
    "list": items_list,
    "sliders": sliders,
    "nowplaying": nowplaying,
    "timeline": timeline,
    "stylecards": stylecards,
    "comment": comment,
}
