#!/usr/bin/env python3
"""sfxlib.py — приёмник готовых сэмплов для score.py.

Кладёшь файл в assets/sfx/<слот>.<любое расширение> — он подхватывается вместо
синтезированного звука. Файла нет — остаётся синтез, ролик всё равно собирается.

Декодирование идёт через ffmpeg, поэтому формат любой: wav, mp3, aiff, flac,
любая частота, моно или стерео. Два важных шага делаются автоматически:

  • обрезка тишины в начале. Сэмпл с 40 мс паузы перед ударом встанет на 40 мс
    позже таймкода — а весь ролик смонтирован по кадрам, и это заметно;
  • нормализация по пику, чтобы уровни слотов не прыгали между библиотеками.
"""
import os, subprocess
import numpy as np

SR = 48000
SFX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'sfx')
EXTS = ('.wav', '.mp3', '.aif', '.aiff', '.flac', '.m4a', '.ogg', '.opus')

SLOTS = {
    'slam_1':      'удар под слово TODAY,',
    'slam_2':      'удар под слово THINKING',
    'slam_3':      'удар под слово GETS',
    'slam_4':      'удар под слово FASTER. — самый крупный из четырёх',
    'suck':        'нарастающий «присос» перед ударом, 0.3 с',
    'whoosh_short':'короткий вуш, 0.3–0.5 с',
    'whoosh_long': 'длинный вуш, 0.7–1.3 с',
    'impact_big':  'главный удар на «All answered», самый большой в ролике',
    'impact_mid':  'средний удар: дроп на 3.5 и логотип',
    'impact_soft': 'мягкий удар: приземления и мелкие акценты',
    'sub_drop':    'низкий суб-удар под дропы',
    'riser_build': 'райзер 3 с под билд перед главным дропом',
    'crash':       'тарелка на дропах',
    'crash_rev':   'обратная тарелка перед дропом',
    'click_ui':    'щелчок интерфейса',
    'tap':         'тап по кнопке отправки',
    'tick_type':   'тик одной набранной буквы, очень короткий',
    'twinkle':     'искорка на блике логотипа',
    'key_1':       'одно нажатие клавиши, вариант 1',
    'key_2':       'одно нажатие клавиши, вариант 2',
    'key_3':       'одно нажатие клавиши, вариант 3',
    'key_4':       'одно нажатие клавиши, вариант 4',
    'key_5':       'одно нажатие клавиши, вариант 5',
    'key_6':       'одно нажатие клавиши, вариант 6',
}

def _decode(path):
    out = subprocess.run(
        ['ffmpeg', '-v', 'error', '-i', path, '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'],
        capture_output=True)
    if out.returncode != 0:
        raise RuntimeError(f'ffmpeg не смог прочитать {path}: {out.stderr.decode()[:200]}')
    return np.frombuffer(out.stdout, dtype='<f4').astype(np.float64)

def _trim_head(x, thresh_db=-45.0):
    """срезает тишину до первого звука, чтобы удар сел ровно на таймкод"""
    if not len(x): return x
    thr = 10**(thresh_db/20) * max(np.max(np.abs(x)), 1e-9)
    idx = np.argmax(np.abs(x) > thr)
    if idx > 0:
        # оставляем 2 мс разгона, чтобы не срезать саму атаку
        idx = max(0, idx - int(0.002*SR))
    return x[idx:]

def load(verbose=False):
    lib = {}
    if not os.path.isdir(SFX_DIR):
        return lib
    for fn in sorted(os.listdir(SFX_DIR)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in EXTS: continue
        if stem not in SLOTS:
            if verbose: print(f'  ? {fn}: нет такого слота, пропущен')
            continue
        x = _trim_head(_decode(os.path.join(SFX_DIR, fn)))
        pk = np.max(np.abs(x)) or 1.0
        lib[stem] = x/pk*0.9
        if verbose:
            print(f'  + {stem:<13} {len(x)/SR:5.2f} с  из {fn}')
    return lib

def pan_sweep(mono, p0, p1):
    """моно-сэмпл, едущий по панораме — для вушей"""
    n = len(mono)
    th = (np.linspace(p0, p1, n) + 1)*np.pi/4
    return np.vstack([mono*np.cos(th), mono*np.sin(th)])

if __name__ == '__main__':
    print(f'папка: {SFX_DIR}')
    lib = load(verbose=True)
    print(f'\nзаполнено {len(lib)} из {len(SLOTS)} слотов')
    missing = [k for k in SLOTS if k not in lib]
    if missing:
        print('не хватает (останутся синтезом):')
        for k in missing: print(f'  − {k:<13} {SLOTS[k]}')
