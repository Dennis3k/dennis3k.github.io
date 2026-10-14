# OpenMontage skills

49 скилов в `.claude/skills/` взяты из проекта
[calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) (`.claude/skills/`).

- Лицензия: **AGPL-3.0** — https://github.com/calesthio/OpenMontage/blob/main/LICENSE
- Установлено: 2026-10-14
- Собственный скил `montazh-reels` к OpenMontage не относится.

## Что не установлено

В репозитории OpenMontage помимо скилов есть Python-тулзы (`tools/`), пайплайны
(`pipeline_defs/`), Remotion-композер и `make setup`. Сюда скопированы **только скилы** —
это знания и инструкции, они самодостаточны. Часть скилов требует ключей API
(HeyGen, ElevenLabs, fal.ai, BFL, Azure, Gemini) и локальных бинарников (ffmpeg, yt-dlp,
whisper, node). Полная установка — на своей машине:

```
git clone https://github.com/calesthio/OpenMontage.git
cd OpenMontage && make setup
```
