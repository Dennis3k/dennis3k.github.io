# Промты: кадры 1–3

Формат везде **вертикальный 9:16**: референс горизонтальный, кадр клипа
вертикальный, композиция пересобрана.

---

## Принцип: указывать, а не описывать

Свободное описание внешности **конкурирует с референсом**. Текст «бледно-голубые
миндалевидные глаза» тянет модель к её собственному представлению о таких
глазах, референс — к конкретному человеку. Два сигнала спорят, и лицо плывёт.

Поэтому ниже не описание персонажа, а **инструкция, что взять с референса без
изменений и что менять запрещено**. Описательные слова оставлены только там,
где нужны как контрольный якорь, и всегда с привязкой «как на референсе».

**Про движок.** Директивная формулировка работает буквально в движках, которые
принимают изображение вместе с инструкцией — Flux Kontext, Seedream, Nano
Banana, GPT-Image. В Midjourney `--cref` и в SDXL с IP-Adapter текст к картинке
не обращается: там тот же эффект достигается тем, что описание лица из промта
**убирается почти целиком**, а работу делает адаптер. В обоих случаях вывод
один — длинного портрета в промте быть не должно. Назовёшь движок — подгоню
синтаксис точно.

---

## Блок A — замок личности. Копировать без изменений

```
The man in the attached reference image is the subject. Preserve his identity
exactly. Do not redesign him, do not idealise him, do not beautify him, do not
make him younger or older, do not make him more symmetrical.

Take the following directly from the reference, unchanged:

- EYES: the exact iris colour, the exact eye shape, the lid fold, the depth of
  the set, the spacing between the eyes, the brow shape and weight above them,
  and the fine lines at the outer corners. Do not change the iris colour. Do
  not enlarge, widen or prettify the eyes.
- NOSE: the exact bridge line including its slight curvature, the exact width,
  the exact tip and its angle, the exact nostrils. Do not straighten or slim it.
- MOUTH: the exact lip thickness and the exact ratio of upper lip to lower,
  the exact cupid's bow, the natural lip colour. Do not fill or redraw them.
- FACE STRUCTURE: the exact cheekbone height and width, the hollow beneath
  them, the jaw width, the chin shape, the forehead height and the hairline.
- SKIN: the exact tone and undertone, the exact degree of tan and weathering,
  the pore texture, every crease and fold including the forehead lines and the
  nasolabial folds, and the sun-redness across the cheekbones and the bridge
  of the nose. Keep the skin exactly as worn as it is in the reference. Do not
  smooth it, do not retouch it, do not remove lines, do not add makeup.
- BEARD: the exact length, the exact density and where it grows and where it
  does not, the exact colour and the exact distribution of grey.
- HAIR: the exact length, the exact wave, the exact way it is swept back and
  to one side, the exact base colour, the exact sun-bleached lighter strands,
  and the matte dry salt-air texture. No gel, no shine, no restyling.
- AGE AND BUILD: exactly as in the reference.

Invent nothing about the face, the hair or the build. Where a detail is not
visible in the reference, keep it neutral rather than inventing it.
```

## Блок B — костюм. Копировать без изменений

```
Keep the wardrobe exactly as in the reference, unchanged in cut, colour,
texture and wear:

- the unbuttoned cream linen shirt, the same creasing, sleeves rolled to the
  same three-quarter length below the elbow, the same chest patch pocket;
- the ecru t-shirt beneath it, carrying the same round Jagannath deity print
  in the same position, the same colours and the same faded worn texture.
  Reproduce the print as it is in the reference; do not redesign it, do not
  add lettering, do not add symbols that are not there;
- the same single short strand of small round amber-brown wooden beads, the
  same bead size and count, sitting snug at the base of the neck;
- the same light taupe-grey linen trousers.
```

## Блок C — локация и свет. Копировать без изменений

```
Keep the world of the reference unchanged: the clifftop at Seven Sisters, East
Sussex, England. The chain of white chalk cliffs recedes in a line of rounded
headlands toward the horizon, bright vertical faces, a narrow shingle beach
and a thin white line of surf at their feet. Low coastal scrub, wind-flattened
grass, dark green shrubs. Calm sea.

Keep the light of the reference unchanged: golden hour, the sun a low orange
disc resting just above the sea on the far left, laying a long broken column
of gold glitter across the water toward camera. Sky stratified in orange,
amber and rose, scattered clouds lit along their undersides. Warm directional
sunlight from the left rim-lighting hair and the edge of the face; soft warm
bounce filling the shadows. No other light source. The sun does not move
between shots.
```

## Блок D — техника и негатив. Копировать без изменений

```
Full-frame cinema camera, vertical 9:16, photorealistic, cinematic colour
grade, natural film grain, no stylisation, no illustration.

Negative: a different man, altered facial features, changed eye colour,
changed nose, changed lip shape, smoothed skin, retouched skin, removed
wrinkles, younger face, symmetrical face, restyled hair, different beard
length, text, lettering, captions, subtitles, watermark, logo, signature,
extra limbs, deformed hands, extra fingers, plastic skin, HDR halos,
oversaturation, second sun, duplicated horizon, modern buildings, boats,
other people.
```

---

# КАДР 1 — крупный, три четверти, обложка клипа

**0.00–8.24 с.** Первый кадр и превью в ленте — должен читаться как стоп-кадр.
**Грудь намеренно вне кадра:** принт Джаганнатхи в этом плане не участвует,
и главный риск клипа уходит из самого рассматриваемого кадра.

```
[БЛОК A]

What changes from the reference — framing and pose only. The man, his face,
his hair and the light stay exactly as locked above.

Reframe to a tight vertical close-up: head and the very top of the shoulders
only. The chest and any garment print are entirely below the bottom edge of
frame. Only the collar of the open linen shirt and the amber bead strand are
visible at the lower edge.

Turn him three-quarters toward camera-left. His gaze travels past the lens to
the horizon — never into the camera. Head upright, chin level. Expression
still and inward, unperformed: neither sad nor smiling, a man thinking rather
than posing. Wind lifts a few strands of his hair across the forehead and off
the temple.

He occupies roughly two thirds of the frame height, set slightly right of
centre, open sky above his head. Behind him the cliffs and sea fall far out of
focus into soft orange and white shapes; the sun's glitter on the water reads
as a blurred vertical band of gold bokeh past his shoulder. Shallow depth of
field, background fully defocused.

[БЛОК C — свет сохраняется, локация размыта до цветных пятен]
[БЛОК D]
```

---

# КАДР 2 — дальний, верхний. Раскрытие локации

**8.24–13.50 с.** Лицо на этой дистанции не читается, но замок личности всё
равно подаётся: он удерживает силуэт, посадку головы, объём и цвет волос.

```
[БЛОК A]
[БЛОК B]

What changes from the reference — camera position and scale only. The man, his
wardrobe and the light stay exactly as locked above.

Move the camera to an elevated position above him and slightly in front,
looking down at about thirty degrees. He becomes a small seated figure in the
lower third of the frame, on the clifftop edge among low scrub, one forearm
resting on a raised knee as in the reference. Place the camera so his face and
the line of his shoulders stay readable in profile against the grass — never
the back of his head. He is no more than one eighth of the frame height.

The full chain of Seven Sisters chalk cliffs runs away from him toward the
upper right, each white rounded headland smaller and hazier than the last,
dissolving into warm atmospheric haze at the horizon. The sea fills the left
half of frame, the low sun on the horizon, its broken gold column crossing the
water toward the bottom of frame. Sky occupies the upper third. Deep focus:
sharp from the foreground scrub to the farthest headland.

[БЛОК C]
[БЛОК D]
```

---

# КАДР 3 — макро, вода у подножия скалы. Вставка

**13.50–18.74 с.** Героя нет, блоки A и B не нужны. Самый дешёвый кадр клипа:
вода, пена и мел — ничего, на чём генерация ломается.

```
Vertical shot taken at water level at the foot of a white chalk cliff.

The lower two thirds of frame is the sea seen close: slow heavy swells lifting
and falling, translucent green-gold at their crests, collapsing into
lace-edged white foam that slides across wet shingle and a flat chalk shelf,
then drains back in thin bright sheets. The upper third is the sheer white
chalk wall rising straight out of the top of frame, streaked with horizontal
grey flint bands, damp and dark at the base where the water reaches, dry and
brilliant above.

Light must match the other shots of this clip exactly: golden hour, the low
sun striking from the left and skimming across the water, igniting every wave
crest in orange and scattering broken gold through the troughs. Fine spray
hangs backlit above the foam. Warm orange on the chalk, cool blue-violet in
the wet shadows at the base.

No horizon, no sky, no people, no birds. Macro scale, shallow depth of field
on the nearest foam, the chalk wall slightly soft behind.

Full-frame cinema camera, vertical 9:16, photorealistic, cinematic colour
grade, natural film grain.

Negative: text, lettering, watermark, logo, people, boats, horizon line, sky,
plastic water, oversaturation, HDR halos, cartoon foam.
```

---

## Порядок работы

1. **Кадр 1** генерируется с референсом заказчицы на входе. Отбирать, пока
   лицо не совпадёт — это эталон на весь клип.
2. Утверждённый кадр 1 становится референсом для **кадра 2** и всех
   последующих планов с героем. Не исходная картинка, а именно утверждённый
   кадр: иначе лица расходятся веером от общего предка.
3. **Кадр 3** генерируется независимо. Единственное требование — тот же закат
   и та же цветовая температура.

## Чеклист отбраковки

Генерация не принимается, если по сравнению с референсом изменилось хоть одно:

- цвет радужки, разрез или посадка глаз;
- линия переносицы, ширина или кончик носа;
- соотношение верхней и нижней губы;
- высота и ширина скул, ширина челюсти, форма подбородка;
- кожа стала глаже, исчезли морщины на лбу или носогубные, ушло солнечное
  покраснение;
- длина или плотность щетины, распределение седины;
- длина, волна, пробор, цвет или выгоревшие пряди волос;
- возраст на вид.

Последние три проверяются даже на дальних планах: там лицо не читается, но
силуэт головы и объём волос читаются отлично.
