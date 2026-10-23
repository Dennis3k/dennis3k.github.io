# Gemini 3.5 — spec motion ad, animated in code

A 24 s + 2 s end-card film at 30 fps, delivered in **16:9 (1920×1080)** and a real
**9:16 (1080×1920) re-layout** — not a crop. Every frame is composed by JavaScript
into a canvas: no stock footage and no After Effects project. The only bitmaps in it
are three film posters, shown on the phone screens in the answers scene; everything
else — type, UI, devices, effects, the logo — is geometry drawn at render time.

Neither the score nor the effects in the delivered mix are synthesised any more.
A supplied track carries the music and 17 of the 18 effect slots are filled from
libraries (Pixabay, and Kenney's CC0 interface pack). `tools/sfx_prep.py` prepares
them — including cutting the track into two pieces so that its own drop lands on
both of the film's, at 3.62 s and 16.15 s — and `tools/sfxlib.py` loads them.
`tools/score.py` still writes everything the libraries do not cover, and mutes its
own drum kit, bass and arpeggio when a bed is present so the two do not stack.
`assets/sfx` and `assets/posters` are gitignored — the posters are studio artwork and
the effects are licensed to the subscriber, so neither belongs in a public repository.
A fresh clone therefore rebuilds the all-synthesised version, with posters drawn in code
instead — which is the right default, but means the committed mp4s and the ones you
would render are not the same mix.

> Spec work for portfolio purposes only. Not affiliated with, sponsored or endorsed by Google LLC.

## Run it

```bash
ln -s /path/to/node_modules node_modules     # needs playwright + a chromium build
node tools/capture.mjs h                     # -> out/gemini35_16x9.mp4
node tools/capture.mjs v                     # -> out/gemini35_9x16.mp4
python3 -I tools/score.py                    # -> out/score.wav + stems
bash tools/mux.sh gemini35_16x9 gemini35_9x16
node tools/shot.mjs h 1.75 3.78 16.60        # stills at any timecode, for review
node tools/audit.mjs                         # the word -> frame table below
```

`index.html` renders a single frame on demand (`window.__frame(n)`); `tools/capture.mjs`
drives it frame by frame and pipes PNGs straight into x264, so nothing is ever
screen-recorded and no frame is dropped.

## The voice is the master clock

`src/timing.js` holds one object, `VO`, with a timestamp per spoken word. Every
type-on, slam, shockwave, camera move and audio hit is derived from it. **When the
ElevenLabs read arrives, paste its word timestamps into that object and the whole
film re-times itself** — picture and score both, because `tools/score.py` mirrors the
same map. Nothing else has to change.

Until then the timings are hand-authored at a natural read speed, and the film ships
silent (`*.mp4`) plus a scored version (`*_scored.mp4`) carrying the code-made music
and SFX with the voice ducks already cut into them.

| line | word | voice t | frame | picture event |
|---:|---|---:|---:|---|
| 1 | TODAY, | 0.12s | 4 | word slams full-width |
| 1 | THINKING | 0.70s | 21 | word slams full-width |
| 1 | GETS | 1.22s | 37 | word slams full-width |
| 1 | FASTER. | 1.62s | 49 | word slams full-width (the biggest) |
| 2 | Gemini | 2.74s | 82 | sparkle window lands on the word |
| 2 | three | 3.62s | 109 | glossy 3.5 crashes in |
| 3 | Do…explore? | 7.78–9.00s | 233–270 | greeting resolves word by word |
| 4 | (typing) | 9.58–10.86s | 287–326 | one character per voice beat |
| 5 | All | 16.15s | 485 | slams, camera centred on it |
| 5 | answered. | 16.45s | 494 | camera rides to it, full-frame |
| 5 | In / seconds. | 17.35 / 17.62s | 521 / 529 | land inside the pull-back |
| 6 | Experience / Gemini. | 18.78 / 19.30s | 563 / 579 | headline, then the gradient wordmark |

## Motion blur is real

Each output frame is the average of up to **32 sub-frames** across an 0.85 shutter
(`src/main.js`). The average is taken pairwise up a binary tree — two canvases at a
time, each step an exact 50/50 blend — because accumulating 32 passes at 1/32 opacity
into an 8-bit canvas quantises dark detail to black. Sub-frame counts are per moment
(`blurAt` in `src/timing.js`): 32 on the slams and the fly-pasts, 4 on held frames.
The whole film costs 10 020 sub-frame renders for 780 output frames (12.8 per frame).

## Two layouts, not one crop

`L.vert` switches real composition, not scale:

- **S1** — 16:9 punches one word through the frame at a time; 9:16 slams each word
  into its own fixed row and builds a four-line poster. Rows are allocated up front
  so nothing ever slides to re-centre.
- **S5–S8** — the app is laid out as a wide centre column in 16:9 and a phone-shaped
  column in 9:16; the input bar, the send orb and the camera targets come from
  `appGeom(L)` so the push lands on the same control in both.
- **S9** — three phones in a row, re-proportioned and re-spaced per format.
- **S10/S11** — type sizes fit each frame's width, and the pull-back ends on a
  composition that works in both.

## What is drawn, scene by scene

| scene | in–out | what it is |
|---|---|---|
| S1 | 0.00–2.50 | word slam on navy + stars: rush out of depth, shockwave, star streaks, decaying frame shake |
| S2 | 2.50–3.50 | the dark frame collapses into a sparkle-shaped window on white; the mark recolours and seats beside "Gemini" as the word resolves from blur |
| S3 | 3.50–5.50 | drop 1 — a glossy extruded 3D "3.5" crashes in among blue bokeh, drifts in 3D, rushes past camera to white |
| S4 | 5.50–7.50 | a phone rises with an Android home screen; the Gemini tile blooms and the camera dives into it (22×) |
| S5 | 7.50–9.50 | hard cut into the app; the greeting resolves word by word, magenta glow |
| S6 | 9.50–11.00 | huge kinetic typing, the camera following the caret on a continuous curve (a per-character jump would smear the whole block under the shutter) |
| S7 | 11.00–12.00 | the block flies into the input bar; the camera pushes toward send |
| S8 | 12.00–12.75 | mic morphs into the send orb, tap, white fills the frame |
| S9 | 12.75–16.00 | white stage, three phones rise and slide into a row with answers — fictional films, posters drawn in code |
| S10 | 16.00–18.50 | drop 2 on a blue dot grid; the camera rides "All" → "answered." then pulls back to "All answered. In seconds." |
| S11 | 18.50–21.00 | "Experience Gemini" + gemini.google.com, phone and browser rising with neon edges |
| S12 | 21.00–24.00 | a light orb swirls in, bursts, and the Google G draws itself out of the burst; a twinkle; slow push |
| S13 | 24.00–26.00 | end card |

## Sound (code only, no samples)

`tools/score.py` writes the score, the SFX and the mix with numpy: 120 BPM
(1 beat = 0.5 s = 15 frames), a tense intro under the slams, the drop on "3.5",
lighter tension under the app, a build, the biggest drop on "All answered.", a hit
on the G, the last chord ringing under the end card. Every slam gets a suck + impact,
every move a whoosh, every typed character a tick, every UI action a click.

There is a four-note motif that arrives on the sparkle and resolves into the major
on the end card, so the film has something to remember it by.

Measured, not asserted (`python3 -I tools/audio_report.py out/score.wav`):

- master **−16.2 LUFS integrated, −1.00 dBTP**. The bed sits under the −14 target on
  purpose: the voice runs 9 dB over everything and carries the integrated figure up.
  The sections now span 4 dB of RMS rather than 2.8, so the drops have somewhere to
  arrive from.
- **stereo width 0.71** (channel correlation above 300 Hz; 1.0 would be mono). The
  bass stays mono and the reverb runs a different reflection grid per channel.
- A-weighted band balance at the big drop: **18 / 22 / 32 / 14 / 13 %** across
  low · low-mid · mid · high-mid · air. The first pass put 87 % of that moment below
  120 Hz, which is how a climax turns into a dull thud.
- a **−9 dB duck** is already cut under every word in the map, 35 ms in, 220 ms out,
  and the music bus is sidechained off the kick and sub on top of that
- `stem_music` + `stem_low` + `stem_sfx` **null against `out/score.wav` at −240 dBFS**
  — the same master-chain gain curve is applied to each stem rather than re-processed,
  so an editable project sums exactly to the delivered mix

What no measurement settles is whether it sounds good. That needs ears, and the
A/B against the first pass is in `out/ab_v1_staryi.m4a` and `out/ab_v2_novyi.m4a`.

## Deviations from the brief, and why

1. **Type** — Google Sans Flex is not installable in this sandbox (no font network
   access), so the film is set in **Inter / Inter Display** (also open source), the
   closest available grotesque. One constant in `src/core.js` (`FAM`) swaps it back.
2. **Brand marks** — the brief asks for the official SVGs from Wikimedia Commons;
   outbound access to `upload.wikimedia.org` is refused by this environment's network
   policy (403 at the proxy). The sparkle, the Google G and the app marks are therefore
   **constructed geometrically in code** (`src/brand.js`) rather than redrawn by hand or
   traced. Drop the official SVGs in and only `src/brand.js` changes.
3. **Voice** — not generated yet (no ElevenLabs in this session). See the timing map above.
4. **DaVinci Resolve project** — the brief lists it as "on request". The pieces it
   needs already exist: per-scene frame ranges, the word map, and stems that null
   against the mix.

## Files

```
index.html          one canvas, one render-on-demand entry point
src/core.js         easing, deterministic noise, canvas helpers, the type family
src/brand.js        sparkle, Google G, app marks, the Gemini gradient
src/stages.js       navy/white/dot-grid stages, bokeh, shockwaves, streaks, vignette
src/ui.js           phone and browser mockups, the app UI, code-drawn posters
src/timing.js       the voice map, the cut list, the motion-blur schedule
src/scenes.js       one function per scene, laid out per format
src/main.js         scene routing + the sub-frame motion-blur accumulator
tools/capture.mjs   frame-accurate render -> x264
tools/shot.mjs      stills at arbitrary timecodes
tools/score.py      the entire soundtrack, synthesised
tools/audio_report.py  A-weighted band balance and stereo width per section
tools/audit.mjs     word -> frame table, cut list, blur budget
tools/mux.sh        lay the score under a silent master
```
