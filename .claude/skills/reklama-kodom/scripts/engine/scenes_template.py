# -*- coding: utf-8 -*-
"""Шаблон сцен. Скопируй в проект как scenes.py.

Контракт с рендерером ровно два имени:
    layout(fmt)                        -> словарь раскладки под формат
    render_scene(dst, L, t, cam, fx)   -> рисует кадр на момент t
"""
import math
import numpy as np
import cv2

import config as C
from core import (Camera, blur_img, add_rgb, blit, warp_quad, clamp, lerp, smooth,
                  seg, noise1, Tex, radial, rim_quad, spill, sheen, text_rgba)
from line import Path, draw_line, head_blob, streak

GLOW = np.float32([0.82, 0.24, 0.88])


def layout(fmt):
    """Раскладка под формат. Вертикаль — перевёрстка, а не кроп:
    размеры и позиции живут здесь, сцены только читают."""
    w, h = fmt["w"], fmt["h"]
    wide = w >= h
    return dict(w=w, h=h, wide=wide, cx=w * 0.5, cy=h * 0.5,
                camz=-3.45 if wide else -3.55,
                card_h=1.6 if wide else 2.2,
                type_w=w * (0.80 if wide else 0.90),
                safe=h * (0.09 if wide else 0.15))


def stage(dst, L, t, env=0.0):
    """Фон: почти чёрный, с дышащим свечением и опционально средой."""
    w, h = L["w"], L["h"]
    dst[:] = np.float32(C.nrm(C.BG)).reshape(1, 1, 3)
    sw, sh = w // 8, h // 8
    g = np.zeros((sh, sw, 3), np.float32)
    for i, (bx, by, br, s) in enumerate(((0.30, 0.62, 0.75, 0.30),
                                         (0.74, 0.30, 0.62, 0.22))):
        cx = (bx + noise1(t * 0.23, i * 3.1) * 0.06) * sw
        cy = (by + noise1(t * 0.19, i * 7.7) * 0.05) * sh
        g += radial(sw, sh, cx, cy, br * sw, 2.2)[:, :, None] * GLOW.reshape(1, 1, 3) * s
    dst += cv2.resize(g, (w, h), interpolation=cv2.INTER_LINEAR) * 0.085
    if env > 0.01:
        yy = np.linspace(0, 1, sh, dtype=np.float32)[:, None]
        wall = np.clip((yy - 0.30) / 0.70, 0, 1) ** 1.7
        e = np.repeat(wall[:, :, None], sw, axis=1) * np.float32([0.105, 0.042, 0.135])
        e += radial(sw, sh, sw * 0.5, sh * 0.6, sw * 0.62, 1.9)[:, :, None] \
            * np.float32([0.21, 0.07, 0.25])
        dst += cv2.resize(e, (w, h), interpolation=cv2.INTER_LINEAR) * env


def quad3(center, w, h, yaw=0.0, pitch=0.0):
    """Четыре угла плоскости в мире, в порядке TL, TR, BR, BL."""
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    rx = np.array([cy_, 0.0, -sy_])
    ry = np.array([sy_ * sp, cp, cy_ * sp])
    c = np.array(center, np.float64)
    return np.array([c + rx * (sx * w / 2) + ry * (sv * h / 2)
                     for sx, sv in ((-1, 1), (1, 1), (1, -1), (-1, -1))])


def demo(dst, L, t, cam, fx):
    """Демо-сцена: линия влетает, садится дугой, карточка выезжает с контровым
    светом и глубиной резкости. Проверяет камеру, квады, линию, свет и пост."""
    stage(dst, L, t, env=0.45)
    cam.set((0, 0, L["camz"]), (0, 0, 0))
    cam.focus, cam.dof = abs(L["camz"]) - 0.6, 9.0

    cx, cy = L["cx"], L["cy"] - L["h"] * 0.06
    arc = Path.bezier((cx - L["w"] * 0.17, cy + L["h"] * 0.13),
                      (cx - L["w"] * 0.07, cy + L["h"] * 0.19),
                      (cx + L["w"] * 0.09, cy + L["h"] * 0.18),
                      (cx + L["w"] * 0.18, cy + L["h"] * 0.09), n=120)

    if t < C.SLAM:                                   # влёт: кадр 0 уже в движении
        u = seg(t, 0.0, C.SLAM, "ic")
        far = np.array([cx - L["w"] * 0.70, cy - L["h"] * 0.46])
        d = arc.at(0.62) - far
        hu = 0.38 + 0.62 * u
        streak(dst, far + d * (hu - 0.52 + 0.40 * u), far + d * hu,
               width=lerp(4.5, 17.0, u ** 1.6), amount=0.55 + 0.45 * u, heat=1.3)
        return

    run = seg(t, 0.23, 0.90, "ioc")
    draw_line(dst, arc, 0, 1, width=L["w"] * 0.006, heat=1.4, glow=1.1,
              head=False, taper=0.0)
    if run < 1.0:
        draw_line(dst, arc, max(0, run - 0.26), run, width=L["w"] * 0.0085,
                  heat=2.2, glow=1.9, head=True, taper=0.55)

    tx = text_rgba(C.HEADLINE, C.F_DISPLAY_BOLD, L["w"] * 0.045, C.WHITE)
    blit(dst, tx, cx - tx.shape[1] / 2, cy - tx.shape[0] / 2, opacity=smooth(run))

    land = seg(t, 1.1, 2.0, "ioq")                   # карточка с контровым светом
    if land > 0.01:
        q = quad3((lerp(2.2, 0.85, land), -0.05, lerp(0.6, -0.7, land)),
                  L["card_h"] * 0.62, L["card_h"], yaw=lerp(0.5, 0.0, land))
        sp, z = cam.project(q)
        tex = Tex(240, 380, ss=2)
        tex.rr((0, 0, 239, 379), 18, fill=(42, 46, 49, 255))
        tex.rr((10, 10, 229, 220), 12, fill=(238, 238, 241, 255))
        spill(dst, sp, (0.26, 0.31, 0.38), 0.18 * land, sigma=L["w"] * 0.08)
        rim_quad(dst, sp, (1.0, 0.42, 0.92), 0.28 * land, halo=L["w"] * 0.015,
                 light=(-0.5, -0.9), edge=0.30)
        warp_quad(dst, tex.np(), sp, blur=cam.blur_for(z.mean()))
        sheen(dst, sp, amount=0.10 * land)
    fx["glow"] = 1.0


SCENES = [((0.0, 4.0), demo)]


def scene_at(t):
    for (a, b), fn in SCENES:
        if a <= t < b:
            return fn
    return SCENES[-1][1]


def render_scene(dst, L, t, cam, fx):
    """Стыки сцен: уходящая уходит в расфокус, а не растворяется наплывом.
    Параметры уходящей сцены обязательно применяются к её буферу — иначе
    смешиваются две резкие картинки, и это читается как склейка."""
    scene_at(t)(dst, L, t, cam, fx)


def mb_samples(t):
    """Подкадры моушн-блюра по времени: дорого только там, где быстро."""
    if t < 0.35:
        return 7
    if 1.0 < t < 2.1:
        return 4
    return 2
