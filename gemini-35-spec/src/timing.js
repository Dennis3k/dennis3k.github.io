/* timing.js — the voice map is the master clock.
   Hand-authored now; replace each `t` with the ElevenLabs word timestamp
   and every type-on, slam and tick re-times itself. Nothing else changes. */
export const FPS = 30;
export const DUR = 26.0;              // 24 s + 2 s end card
export const TOTAL = Math.round(DUR * FPS);
export const BPM = 120;               // 1 beat = 0.5 s = 15 frames
export const BEAT = 60 / BPM;

export const VO = {
  l1: [
    { w: 'TODAY,', t: 0.12 },
    { w: 'THINKING', t: 0.70 },
    { w: 'GETS', t: 1.22 },
    { w: 'FASTER.', t: 1.62 },
  ],
  gemini: 2.74,
  three: 3.62, point: 3.92, five: 4.10,
  l3: [
    { w: 'Do', t: 7.78 }, { w: 'you', t: 7.96 }, { w: 'have', t: 8.14 },
    { w: 'new', t: 8.34 }, { w: 'ideas', t: 8.56 }, { w: 'to', t: 8.84 },
    { w: 'explore?', t: 9.00 },
  ],
  typeStart: 9.58, typeEnd: 10.86,
  l5: [
    { w: 'All', t: 16.15 }, { w: 'answered.', t: 16.45 },
    { w: 'In', t: 17.35 }, { w: 'seconds.', t: 17.62 },
  ],
  experience: 18.78, geminiWord: 19.30,
};

export const CUTS = {
  S1: [0.0, 2.5], S2: [2.5, 3.5], S3: [3.5, 5.5], S4: [5.5, 7.5],
  S5: [7.5, 9.5], S6: [9.5, 11.0], S7: [11.0, 12.0], S8: [12.0, 12.75],
  S9: [12.75, 16.0], S10: [16.0, 18.5], S11: [18.5, 21.0], S12: [21.0, 24.0],
  S13: [24.0, 26.0],
};

/** sub-frame count for the accumulation motion blur, by wall-clock time */
export function blurAt(t) {
  const fast = [
    [0.05, 0.40, 28], [0.63, 0.95, 28], [1.15, 1.45, 28], [1.55, 1.95, 32],
    [2.50, 3.05, 20], [3.50, 3.80, 32], [4.80, 5.55, 32],
    [5.50, 6.20, 14], [6.85, 7.55, 32], [7.50, 7.80, 10],
    [9.50, 11.00, 8], [11.00, 11.70, 26], [12.35, 12.80, 22],
    [12.75, 14.20, 14], [15.90, 16.70, 30], [17.10, 17.95, 22],
    [18.45, 19.40, 16], [21.00, 22.60, 20], [22.55, 23.10, 24],
    [23.90, 24.25, 12],
  ];
  for (const [a, b, n] of fast) if (t >= a && t < b) return n;
  return 4;                            // everything still gets a touch of blur
}
