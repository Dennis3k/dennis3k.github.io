# Промты: кадры 1–3

Движок не назван, поэтому промты на английском — он работает во всех
генераторах изображений. Формат везде **вертикальный 9:16**: референс
горизонтальный, кадр клипа вертикальный, композиция пересобрана.

---

## Метод удержания лица — читать до генерации

Текстовое описание задаёт **тип внешности**, а не конкретного человека. Одним
текстом получится «похожий мужчина», и в каждом кадре он будет другим. Лицо
держится тремя вещами вместе:

1. **Референс на входе обязателен.** Утверждённое изображение подаётся как
   character reference (Midjourney `--cref`, Flux PuLID или Redux, Seedance
   character ref, в SDXL — IP-Adapter FaceID). Без этого остальное не работает.
2. **Блок внешности копируется побайтово** во все промты. Ни одного
   переписанного слова: даже синоним смещает лицо.
3. **Цепочка, а не веер.** Сначала генерируется кадр 1 — самый крупный план,
   где лицо читается лучше всего. Он утверждается. **Дальше референсом для
   всех остальных кадров служит утверждённый кадр 1, а не исходная картинка
   заказчицы.** Так лицо не расходится от кадра к кадру, а наследуется от
   одного эталона.

Ещё: держи один и тот же seed-ряд там, где движок позволяет, и не меняй
соотношение сторон между кадрами — смена пропорций тянет за собой черты лица.

---

## Блок A — внешность. Копировать без изменений

```
A 48-year-old Caucasian man, lean build, weathered and sun-worn rather than
groomed. Face: oval, with high sharply defined cheekbones and a slight hollow
beneath them, and a firm jawline softened by stubble. Eyes: pale blue-grey,
almond-shaped, moderately deep-set beneath slightly hooded upper lids, fine
crow's-feet radiating from the outer corners, faint shadows beneath.
Eyebrows: medium-thick, straight with a low arch, ash-brown with a few grey
hairs. Nose: narrow and straight, a subtle dorsal hump near the bridge, a
slightly downturned rounded tip, moderately flared nostrils. Lips: medium
fullness, the upper lip noticeably thinner than the lower, a clearly drawn
cupid's bow, natural dusty-rose colour, lips slightly parted. Beard: roughly
one week of stubble, densest on the chin, jaw and upper lip, bare on the upper
cheeks, mid-brown shot through with grey and carrying a warm reddish cast in
low sunlight. Skin: tanned and sun-weathered, warm golden-olive undertone,
visible pores across the nose and cheeks, two or three horizontal creases on
the forehead, pronounced nasolabial folds, faint sun-redness across the
cheekbones and the bridge of the nose, no makeup, no retouching, no smoothing.
Hair: medium length falling just below the ears, thick, wavy, wind-tousled,
swept back off the forehead and to one side; dark ash-blond base with
sun-bleached lighter strands and golden-copper highlights where the low sun
strikes it; matte and slightly dry, salt-air texture, no gel, no shine.
```

## Блок B — костюм. Копировать без изменений

```
Wardrobe: an unbuttoned cream linen shirt, visibly creased, sleeves rolled to
three-quarter length just below the elbow, a single patch pocket on the chest.
Beneath it an ecru cotton t-shirt bearing a large round Jagannath deity print
across the chest: wide circular white eyes ringed in red and black, red and
charcoal forms, ochre and gold accents, rendered in a worn, faded,
watercolour-washed texture. A single short strand of small round amber-brown
wooden beads sits snug against the base of the neck. Light taupe-grey linen
trousers.
```

## Блок C — локация и свет. Копировать без изменений

```
Location: the clifftop at Seven Sisters, East Sussex, England. The chain of
white chalk cliffs recedes in a rhythmic line of rounded headlands toward the
horizon, their vertical faces bright, a narrow shingle beach and a thin white
line of surf at their feet. Low coastal scrub, wind-flattened grass and dark
green shrubs. Calm sea.

Light: golden hour. The sun is a low orange disc resting just above the sea
on the far left, laying a long broken column of gold glitter across the water
toward camera. The sky is stratified in orange, amber and rose, scattered
clouds lit along their undersides. Warm directional sunlight from the left
rim-lights the hair and the edge of the face; soft warm bounce fills the
shadows. No other light source.
```

## Блок D — техника и негатив. Копировать без изменений

```
Full-frame cinema camera, vertical 9:16, photorealistic, cinematic colour
grade, natural film grain, no stylisation, no illustration.

Negative: text, lettering, captions, subtitles, watermark, logo, signature,
extra limbs, deformed hands, extra fingers, plastic skin, beauty retouching,
airbrushing, HDR halos, oversaturation, second sun, duplicated horizon,
modern buildings, boats, other people, lens dirt, heavy vignette.
```

---

# КАДР 1 — крупный, три четверти, обложка клипа

**0.00–8.24 с.** Это первый кадр и превью в ленте: он должен читаться как
стоп-кадр, а не как начало движения.

**Грудь намеренно вне кадра** — принт Джаганнатхи в этом плане не участвует.
Это снимает главный риск клипа с самого рассматриваемого кадра.

```
[БЛОК A]

Framing: tight vertical close-up. Head and the very top of the shoulders only;
the chest and any garment print are entirely out of frame below the bottom
edge. The collar of the open linen shirt and the amber bead strand are just
visible at the lower edge. He is turned three-quarters toward camera-left, his
gaze travelling past the lens to the horizon, never into the camera. Head
upright, chin level. Expression still and inward, unperformed: neither sad nor
smiling, the face of a man thinking rather than posing. Wind lifts a few
strands of hair across his forehead and off his temple.

He occupies roughly two thirds of the frame height, set slightly right of
centre, with open sky above his head. Behind him the cliffs and the sea are
thrown far out of focus into soft orange and white shapes; the sun's glitter
on the water reads as a blurred vertical band of gold bokeh past his shoulder.
Shallow depth of field, the background fully defocused.

[БЛОК C — только свет, локация размыта до пятен]
[БЛОК D]
```

---

# КАДР 2 — дальний, верхний. Раскрытие локации

**8.24–13.50 с.** Здесь зритель впервые видит, где герой находится. Лицо на
этой дистанции не читается — лицевой блок всё равно подаётся, чтобы силуэт,
поза и волосы остались теми же.

```
[БЛОК A]
[БЛОК B]

Framing: wide vertical shot from an elevated position, the camera above the
man and slightly in front of him, looking down at about thirty degrees. He is
a small seated figure in the lower third of the frame, perched on the clifftop
edge among low scrub, one forearm resting on a raised knee. The camera is
placed so that his face and the line of his shoulders stay readable in
profile against the grass; never the back of his head. He is no more than one
eighth of the frame height.

The full chain of Seven Sisters chalk cliffs runs away from him toward the
upper right, each white rounded headland smaller and hazier than the last,
dissolving into warm atmospheric haze at the horizon. The sea fills the left
half of the frame, the low sun resting on the horizon with its broken gold
column crossing the water toward the bottom of the frame. Sky occupies the
upper third. Deep focus, everything sharp from the scrub in the foreground to
the farthest headland.

[БЛОК C]
[БЛОК D]
```

---

# КАДР 3 — макро, вода у подножия скалы. Вставка

**13.50–18.74 с.** Героя в кадре нет, блоки A и B не нужны. Самый дешёвый
кадр клипа: вода, пена и мел — ничего, на чём генерация ломается.

```
Framing: vertical shot taken at water level at the foot of a white chalk
cliff. The lower two thirds of the frame is the sea seen close: slow heavy
swells lifting and falling, translucent green-gold at their crests, collapsing
into lace-edged white foam that slides across wet shingle and a flat chalk
shelf, then drains back in thin bright sheets. The upper third is the sheer
white chalk wall rising straight out of the top of frame, its surface streaked
with horizontal grey flint bands, damp and dark at the base where the water
reaches, dry and brilliant above.

Light: the low sun strikes from the left and skims across the water, igniting
every wave crest in orange and scattering broken gold through the troughs.
Fine spray hangs backlit in the air above the foam. Warm orange light on the
chalk, cool blue-violet in the wet shadows at the base.

No horizon, no sky, no people, no birds. Macro scale, shallow depth of field
on the nearest foam, the chalk wall slightly soft behind.

Full-frame cinema camera, vertical 9:16, photorealistic, cinematic colour
grade, natural film grain.

Negative: text, lettering, watermark, logo, people, boats, horizon line, sky,
plastic water, oversaturation, HDR halos, cartoon foam.
```

---

## Порядок работы

1. Генерируй **кадр 1** с референсом заказчицы на входе. Отбирай до тех пор,
   пока лицо не совпадёт — это эталон на весь клип.
2. Утверждённый кадр 1 становится референсом для **кадра 2** и всех
   последующих планов с героем.
3. **Кадр 3** генерируется независимо: героя в нём нет, сцеплять нечего. Важно
   одно — тот же закат и та же цветовая температура, что в кадрах 1 и 2.
