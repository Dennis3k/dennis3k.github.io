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


# ------------------------------------------------- половина экрана со списком
def _tilt(img, k):
    """Лёгкая перспектива: дальний край уже ближнего. k=0 — сильный наклон."""
    w, h = img.size
    d = int(h * 0.42 * (1 - k))          # насколько «уехал» дальний край
    if d < 2:
        return img
    # QUAD задаёт четырёхугольник ИСХОДНИКА, который натянется на прямоугольник
    quad = (0, -d, 0, h + d, w, h, w, 0)
    return img.transform((w, h), Image.QUAD, quad, resample=Image.BICUBIC)


def _row(text, num, w, h, accent, text_font=None):
    """Плита пункта. Все размеры от высоты плиты: работает и на 1080, и на 500."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # плита с градиентом: сверху светлее, снизу уходит в темноту — даёт объём
    grad = Image.new("RGBA", (1, h))
    gd = ImageDraw.Draw(grad)
    for y in range(h):
        v = y / max(1, h - 1)           # не f: f — это функция шрифта выше
        gd.point((0, y), fill=(int(38 - 16 * v), int(44 - 18 * v),
                               int(62 - 24 * v), 245))
    plate = grad.resize((w, h), Image.BILINEAR)
    r = max(8, int(h * 0.19))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    img.paste(plate, (0, 0), mask)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=r,
                        outline=(255, 255, 255, 40), width=2)
    d.rounded_rectangle((0, 0, max(5, int(h * 0.07)), h - 1), radius=4,
                        fill=accent + (255,))
    nf = f("Black", max(14, int(h * 0.34)))
    nx = int(h * 0.36)
    d.text((nx, h // 2), num, font=nf, fill=accent + (255,), anchor="lm")
    tx = nx + int(d.textlength("00", font=nf)) + int(h * 0.22)
    tf = text_font or _fit_font("SemiBold", text, w - tx - int(h * 0.2), int(h * 0.32))
    d.text((tx, h // 2), text, font=tf, fill=WHITE, anchor="lm")
    return img


def split_list(spec, p):
    """Половина кадра: заголовок и пункты, прилетающие с наклоном.
    Вёрстка считается от размеров панели — годится и для нижней половины
    рилса (1080x960), и для левой половины окна (500x640)."""
    W, H = int(spec.get("w", 1080)), int(spec.get("h", 960))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(img)
    for y in range(H):                    # фон уходит вглубь
        t = y / (H - 1)
        d.line((0, y, W, y), fill=(int(10 + 16 * t), int(13 + 20 * t),
                                   int(22 + 34 * t), 255))
    if W >= H:
        d.line((0, 0, W, 0), fill=(79, 140, 255, 200), width=4)
    else:
        d.line((W - 2, 0, W - 2, H), fill=(79, 140, 255, 200), width=4)
    pad = max(20, int(min(W, H) * 0.055))
    rows = spec["items"]
    n = len(rows)

    badge = spec.get("badge")
    ty = pad
    if badge:                             # плашка над заголовком, как «ТОП-5»
        bf = f("Bold", max(14, int(H * 0.03)))
        bw = int(d.textlength(badge, font=bf)) + 28
        bh = int(H * 0.05)
        d.rounded_rectangle((pad, ty, pad + bw, ty + bh), radius=8,
                            fill=(40, 46, 66, 255), outline=(234, 179, 8, 255), width=2)
        d.text((pad + 14, ty + bh // 2), badge, font=bf, fill=WHITE, anchor="lm")
        ty += bh + int(pad * 0.6)
    tk = ease(seg(p, 0.0, 0.14))
    tf = _fit_font("Black", spec.get("title", ""), W - 2 * pad, int(min(52, H * 0.075)))
    d.text((pad, int(ty - 18 * (1 - tk))), spec.get("title", ""),
           font=tf, fill=(255, 255, 255, int(255 * tk)))
    top = ty + int(tf.size * 1.5)

    avail = H - top - pad
    slot = avail / n
    rh = int(min(118, slot * 0.82))
    rw = W - 2 * pad
    longest = max(rows, key=len)
    probe = _row(longest, "00", rw, rh, (255, 255, 255))   # общий кегль для всех плит
    nx = int(rh * 0.36)
    nf = f("Black", max(14, int(rh * 0.34)))
    tx = nx + int(ImageDraw.Draw(probe).textlength("00", font=nf)) + int(rh * 0.22)
    shared = _fit_font("SemiBold", longest, rw - tx - int(rh * 0.2), int(rh * 0.32))
    for i, text in enumerate(rows):
        k = ease(seg(p, 0.14 + i * 0.1, 0.42 + i * 0.1))
        if k <= 0:
            continue
        accent = TL_COLORS[i % len(TL_COLORS)]
        row = _row(text, f"{i + 1:02d}", rw, rh, accent, text_font=shared)
        row = _tilt(row, k)
        s = 0.86 + 0.14 * k
        row = row.resize((max(1, int(rw * s)), max(1, int(rh * s))), Image.LANCZOS)
        if k < 1:
            row.putalpha(row.getchannel("A").point(lambda a, k=k: int(a * k)))
        x = int(pad + (1 - k) * W * 0.24)
        y = int(top + i * slot + (1 - k) * rh * 0.3)
        shadow = Image.new("RGBA", row.size, (0, 0, 0, int(90 * k)))
        img.alpha_composite(Image.composite(shadow, Image.new("RGBA", row.size),
                                            row.getchannel("A")), (x + 6, y + 8))
        img.alpha_composite(row, (x, y))
    return img


RENDERERS["split_list"] = split_list


# =============================================================== 3D-элементы
def _fit_font(weight, text, max_w, start, floor=14):
    """Самый крупный кегль, при котором строка влезает в max_w."""
    size = start
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    while size > floor and probe.textlength(text, font=f(weight, size)) > max_w:
        size -= 1
    return f(weight, size)


def _lean_back(img, amount):
    """Наклон «от зрителя»: верхний край уже нижнего, как у лежащей панели."""
    w, h = img.size
    d = int(w * amount)
    if d < 1:
        return img
    quad = (-d, 0, 0, h, w, h, w + d, 0)
    return img.transform((w, h), Image.QUAD, quad, resample=Image.BICUBIC)


# --------------------------------------------------------- хромированный титул
def chrome_title(spec, p):
    """Объёмный хромированный текст: экструзия слоями + градиентное лицо + блик."""
    text = spec.get("text", "TITLE")
    size = int(spec.get("size", 120))
    depth = int(spec.get("depth", 14))
    ft = f("Black", size)
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    tw = int(probe.textlength(text, font=ft))
    W, H = tw + depth + 60, int(size * 1.35) + depth + 40
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).text((30, 20), text, font=ft, fill=255)

    # экструзия: слои сдвигаются вниз-вправо и темнеют вглубь
    for i in range(depth, 0, -1):
        shade = int(40 + 70 * (1 - i / depth))
        layer = Image.new("RGBA", (W, H), (shade, shade + 6, shade + 18, 255))
        shifted = Image.new("L", (W, H), 0)
        shifted.paste(mask, (i, i))
        img.paste(layer, (0, 0), shifted)

    # лицо: хром — светлый верх, тёмная полоса горизонта, светлый низ
    grad = Image.new("RGBA", (1, H))
    gd = ImageDraw.Draw(grad)
    for y in range(H):
        v = y / (H - 1)
        if v < 0.45:
            c = int(255 - 70 * (v / 0.45))
        elif v < 0.55:
            c = int(185 - 110 * ((v - 0.45) / 0.1))
        else:
            c = int(75 + 170 * ((v - 0.55) / 0.45))
        gd.point((0, y), fill=(c, min(255, c + 6), min(255, c + 16), 255))
    face = grad.resize((W, H), Image.BILINEAR)

    # блик: диагональная полоса проезжает слева направо
    sh = seg(p, 0.35, 0.75)
    if 0 < sh < 1:
        band = Image.new("L", (W, H), 0)
        bx = int(-W * 0.3 + sh * W * 1.6)
        ImageDraw.Draw(band).polygon(
            [(bx, 0), (bx + 46, 0), (bx + 46 - H // 2, H), (bx - H // 2, H)], fill=110)
        face = Image.composite(Image.new("RGBA", (W, H), (255, 255, 255, 255)),
                               face, band)
    img.paste(face, (0, 0), mask)
    rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(rim).text((30, 20), text, font=ft, fill=(0, 0, 0, 0),
                             stroke_width=2, stroke_fill=(255, 255, 255, 170))
    img.alpha_composite(rim)

    # вход: прилетает из глубины с перелётом
    k = seg(p, 0.0, 0.22)
    if k < 1:
        s = 1.7 - 0.7 * ease(k) + 0.06 * (k > 0.7) * (1 - k) * 10
        s = max(0.4, s)
        sw, sh2 = int(W * s), int(H * s)
        big = img.resize((sw, sh2), Image.LANCZOS)
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(big, ((W - sw) // 2, (H - sh2) // 2)) if s <= 1 else \
            out.alpha_composite(big.crop(((sw - W) // 2, (sh2 - H) // 2,
                                          (sw - W) // 2 + W, (sh2 - H) // 2 + H)))
        out.putalpha(out.getchannel("A").point(lambda a, k=k: int(a * ease(k))))
        return out
    return img


# ------------------------------------------------------ объёмный эквалайзер
def eq_bars(spec, p):
    """Изометрические столбики: перед, верх и бок разной яркости дают объём."""
    n = int(spec.get("bars", 9))
    W, H = int(spec.get("w", 1000)), int(spec.get("h", 420))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cols = [(255, 122, 48), (255, 92, 140), (255, 160, 60)]
    bw = int(W / (n * 1.35))
    dx, dy = int(bw * 0.45), int(bw * 0.3)          # смещение «вглубь»
    for i in range(n):
        k = ease(seg(p, 0.03 * i, 0.28 + 0.03 * i))
        wob = 0.75 + 0.25 * abs(__import__("math").sin(p * 18 + i * 1.7))
        h = int((H - dy - 10) * (0.35 + 0.6 * ((i * 37) % 10) / 10) * k * wob)
        if h < 4:
            continue
        x = int(i * W / n + 6)
        base = H - 4
        c = cols[i % len(cols)]
        front = (x, base - h, x + bw, base)
        d.rectangle(front, fill=c + (245,))
        side = [(x + bw, base - h), (x + bw + dx, base - h - dy),
                (x + bw + dx, base - dy), (x + bw, base)]
        d.polygon(side, fill=tuple(int(v * 0.62) for v in c) + (245,))
        top = [(x, base - h), (x + dx, base - h - dy),
               (x + bw + dx, base - h - dy), (x + bw, base - h)]
        d.polygon(top, fill=tuple(min(255, int(v * 1.18) + 25) for v in c) + (250,))
    return img


# ------------------------------------------------------------- график роста
def growth_chart(spec, p):
    pts = spec.get("points", [1, 2, 3, 5, 8])
    labels = spec.get("labels", [""] * len(pts))
    W, H = int(spec.get("w", 820)), int(spec.get("h", 520))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    panel(d, (6, 6, W - 6, H - 6))
    d.text((44, 34), spec.get("title", ""), font=f("Bold", 30), fill=DIM)
    x0, x1, y0, y1 = 60, W - 60, H - 90, 170
    lo, hi = 0, max(pts) * 1.1
    xy = [(x0 + (x1 - x0) * i / (len(pts) - 1),
           y0 - (y0 - y1) * (v - lo) / (hi - lo)) for i, v in enumerate(pts)]
    for gx in range(len(pts)):
        X = x0 + (x1 - x0) * gx / (len(pts) - 1)
        d.line((X, y1, X, y0), fill=(255, 255, 255, 18), width=1)
        d.text((X - 20, y0 + 22), str(labels[gx]), font=f("Medium", 22), fill=DIM)
    k = ease(seg(p, 0.08, 0.7))
    total = len(xy) - 1
    upto = k * total
    drawn = [xy[0]]
    for i in range(1, len(xy)):
        if i <= upto:
            drawn.append(xy[i])
        else:
            fr = upto - (i - 1)
            if fr > 0:
                a, b = xy[i - 1], xy[i]
                drawn.append((a[0] + (b[0] - a[0]) * fr, a[1] + (b[1] - a[1]) * fr))
            break
    if len(drawn) > 1:
        area = drawn + [(drawn[-1][0], y0), (drawn[0][0], y0)]
        fill = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(fill).polygon(area, fill=ACCENT[:3] + (60,))
        img.alpha_composite(fill)
        d.line(drawn, fill=ACCENT, width=7, joint="curve")
        ex, ey = drawn[-1]
        for r, a in ((26, 40), (17, 90), (9, 255)):
            d.ellipse((ex - r, ey - r, ex + r, ey + r), fill=ACCENT[:3] + (a,))
    big = spec.get("value", pts[-1]) * ease(seg(p, 0.1, 0.75))
    d.text((44, 74), spec.get("prefix", "") + spaced(big) + spec.get("suffix", ""),
           font=f("Black", 64), fill=WHITE)
    return img


# ----------------------------------------------------------- веер кейсов
def cases_fan(spec, p):
    names = spec.get("names", ["A", "B", "C"])
    W, H = int(spec.get("w", 1000)), int(spec.get("h", 620))
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    n = len(names)
    order = sorted(range(n), key=lambda i: -abs(i - (n - 1) / 2))
    step = min(205, (W - 220) / max(1, n - 1))
    for i in order:
        name = names[i]
        k = ease(seg(p, 0.05 + i * 0.08, 0.4 + i * 0.08))
        if k <= 0:
            continue
        cw, ch = 200, 150
        card = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)
        col = TL_COLORS[i % len(TL_COLORS)]
        cd.rounded_rectangle((0, 0, cw - 1, ch - 1), radius=24, fill=(20, 24, 36, 245),
                             outline=col + (220,), width=3)
        cd.rounded_rectangle((0, 0, cw - 1, 14), radius=7, fill=col + (255,))
        ft = _fit_font("Black", name, cw - 34, 40)
        tw = cd.textlength(name, font=ft)
        cd.text(((cw - tw) / 2, 56), name, font=ft, fill=WHITE)
        card = _tilt(card, 0.55 + 0.45 * k)
        spread = (i - (n - 1) / 2)
        ang = -spread * 9 * k
        card = card.rotate(ang, expand=True, resample=Image.BICUBIC)
        s = 0.6 + 0.4 * k
        card = card.resize((int(card.width * s), int(card.height * s)), Image.LANCZOS)
        cx = W / 2 + spread * step * k - card.width / 2
        cy = H * 0.44 + abs(spread) * 30 * k - card.height / 2 + (1 - k) * 120
        card.putalpha(card.getchannel("A").point(lambda a, k=k: int(a * min(1, k * 1.4))))
        img.alpha_composite(card, (int(cx), int(cy)))
    return img


RENDERERS.update({"chrome_title": chrome_title, "eq_bars": eq_bars,
                  "growth_chart": growth_chart, "cases_fan": cases_fan})
