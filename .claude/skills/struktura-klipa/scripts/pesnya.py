#!/usr/bin/env python3
"""Карта песни: секции, строки с таймкодами, энергия, паузы под склейки.

На входе аудио, на выходе всё, на что вешается сценарий: где вступление,
где первое слово, где каждая строка, где инструментальные паузы и где
финальный проигрыш.

  python3 pesnya.py track.mp3 -o razbor/klip01
  python3 pesnya.py track.mp3 -o razbor/klip01 --model medium --no-asr

Текст песни берётся из тегов mp3, если он там есть: Suno зашивает его
вместе с разметкой [Verse]/[Chorus]. Иначе распознаётся.

ВАЖНО про распознавание пения:
  - тайминги слов и строк ПРИБЛИЗИТЕЛЬНЫЕ (в припеве с реверберацией до 2 с):
    для склеек годятся только паузы, измеренные по самому wav пользователя
    (references/tayming.md);
  - модель small на вокале разваливается в повтор одной строки, нужна large-v3;
  - подсказка известным текстом помогает, но может породить фантомный сегмент
    в начале — он отсекается фильтром галлюцинаций;
  - резать аудио на окна НЕЛЬЗЯ, на обрезке модель фантазирует сильнее;
  - faster-whisper не умеет открыть файл с новым av, поэтому звук декодируется
    через ffmpeg и передаётся массивом.
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

SR_A, N, HOP = 22050, 2048, 512
SR_W = 16000
# Мусор, который whisper выдаёт на музыке без вокала.
JUNK = re.compile(r"субтитры|dimatorzok|редактор|amara\.org|продолжение следует"
                  r"|подписывайтесь|спасибо за просмотр", re.I)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def decode(path, sr, fmt="s16le"):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1",
                        "-ar", str(sr), "-f", fmt, "-"], capture_output=True)
    if r.returncode != 0:
        sys.exit(f"ffmpeg не прочитал файл:\n{r.stderr.decode()[:400]}")
    dt = np.int16 if fmt == "s16le" else np.float32
    a = np.frombuffer(r.stdout, dtype=dt)
    return a.astype(np.float32) / 32768 if fmt == "s16le" else a.copy()


def tags(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format_tags",
             "-of", "json", path])
    try:
        return json.loads(r.stdout).get("format", {}).get("tags", {})
    except json.JSONDecodeError:
        return {}


def embedded_lyrics(tg):
    for k, v in tg.items():
        if "lyric" in k.lower() and len(v) > 40:
            return v
    return None


def spectra(x):
    nf = (len(x) - N) // HOP
    w = np.hanning(N)
    S = np.abs(np.fft.rfft(np.stack([x[i*HOP:i*HOP+N]*w for i in range(nf)]), axis=1))
    return S, np.fft.rfftfreq(N, 1/SR_A), np.arange(nf)*HOP/SR_A


def smooth(a, k):
    return np.convolve(a, np.ones(k)/k, mode="same")


def air_ratio(S, fr):
    """Доля энергии выше 3 кГц. У голоса 20%+ (шипящие и дыхание),
    у инструментальной подложки вдвое меньше. Главный признак вокала."""
    return S[:, fr > 3000].sum(axis=1) / (S.sum(axis=1) + 1e-9)


def clean(segs, dur):
    """Отсев галлюцинаций whisper."""
    out = []
    for s in segs:
        txt = s["text"].strip()
        if not txt or JUNK.search(txt):
            continue
        ws = s.get("words") or []
        # вырожденные тайминги: несколько слов с одним и тем же временем
        if len(ws) > 2:
            starts = [w["s"] for w in ws]
            if len(set(starts)) < len(starts) - 1:
                continue
            spread = max(starts) - min(starts)
            if spread > 0 and (s["end"] - s["start"]) / max(len(ws), 1) > 2.0:
                continue
        if s["end"] - s["start"] > 0.6 * dur:
            continue
        out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("-o", "--outdir", required=True)
    ap.add_argument("--model", default="large-v3",
                    help="small разваливается на пении — не ставь его")
    ap.add_argument("--no-asr", action="store_true",
                    help="только энергия и полосы, без распознавания")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    x = decode(a.audio, SR_A)
    dur = len(x) / SR_A
    S, fr, t = spectra(x)
    air = smooth(air_ratio(S, fr), 41)
    energy = smooth(S.sum(axis=1), 41)
    energy /= energy.max()

    tg = tags(a.audio)
    lyr = embedded_lyrics(tg)
    if lyr:
        open(os.path.join(a.outdir, "lyrics.txt"), "w").write(lyr)

    segs = []
    if not a.no_asr:
        from faster_whisper import WhisperModel
        audio = decode(a.audio, SR_W, "f32le")
        prompt = None
        if lyr:
            lines = [l.strip() for l in lyr.splitlines()
                     if l.strip() and not l.strip().startswith("[")]
            prompt = " ".join(lines)[:600]
        m = WhisperModel(a.model, device="cpu", compute_type="int8")
        got, _ = m.transcribe(audio, language="ru", word_timestamps=True,
                              vad_filter=False, initial_prompt=prompt,
                              condition_on_previous_text=False, beam_size=5,
                              temperature=[0.0, 0.2, 0.4])
        for s in got:
            segs.append({"start": round(s.start, 2), "end": round(s.end, 2),
                         "text": s.text.strip(),
                         "words": [{"w": w.word.strip(), "s": round(w.start, 2)}
                                   for w in (s.words or [])]})
        segs = clean(segs, dur)

    first = segs[0]["start"] if segs else None
    last = segs[-1]["end"] if segs else None
    gaps = [(round(b["end"], 2), round(c["start"], 2))
            for b, c in zip(segs, segs[1:]) if c["start"] - b["end"] >= 1.0]

    pas = {"file": os.path.basename(a.audio), "duration": round(dur, 2),
           "title": tg.get("title"), "artist": tg.get("artist"),
           "suno": "suno" in (tg.get("comment", "") or "").lower(),
           "has_embedded_lyrics": bool(lyr),
           "intro_end": first, "last_word": last,
           "outro": round(dur - last, 2) if last else None,
           "lines": len(segs)}
    json.dump({"passport": pas, "segments": segs, "gaps": gaps},
              open(os.path.join(a.outdir, "pesnya.json"), "w"),
              ensure_ascii=False, indent=1)

    L = [f"# Карта песни: {pas['title'] or pas['file']}", ""]
    L.append(f"Длительность **{dur:.2f} с**"
             + (f" · {pas['artist']}" if pas['artist'] else "")
             + (" · сделано в Suno" if pas['suno'] else ""))
    if first is not None:
        L += ["", f"- Вступление без слов: **0 – {first:.2f} с** ({first:.2f} с)",
              f"- Первое слово: **{first:.2f} с**",
              f"- Последнее слово: **{last:.2f} с**",
              f"- Инструментальный финал: **{last:.2f} – {dur:.2f} с** "
              f"({dur-last:.2f} с, {100*(dur-last)/dur:.0f}% трека)"]
    if gaps:
        L += ["", "**Паузы между фразами — готовые точки склейки:**", ""]
        L += [f"- {b:.2f} – {c:.2f} с ({c-b:.2f} с)" for b, c in gaps]
    if segs:
        L += ["", "## Строки", "", "| вход | выход | длит. | строка |",
              "|---|---|---|---|"]
        L += [f"| {s['start']:.2f} | {s['end']:.2f} | "
              f"{s['end']-s['start']:.2f} | {s['text']} |" for s in segs]
    L += ["", "## Энергия по 4 секунды", "",
          "`E` — громкость от пика, `air` — доля выше 3 кГц "
          "(у вокала 0.20+, у подложки вдвое меньше).", "",
          "| с | E | air |", "|---|---|---|"]
    step = int(4 * SR_A / HOP)
    for i in range(0, len(t), step):
        j = min(i + step, len(t))
        L.append(f"| {t[i]:.0f} | {energy[i:j].mean():.2f} | {air[i:j].mean():.3f} |")
    open(os.path.join(a.outdir, "pesnya.md"), "w").write("\n".join(L) + "\n")

    print(json.dumps(pas, ensure_ascii=False, indent=2))
    print(f"\nкарта: {os.path.join(a.outdir, 'pesnya.md')}")
    if segs and first is not None and first > 5:
        print(f"! вступление {first:.1f} с — спроси, резать ли его")


if __name__ == "__main__":
    main()
