export const FPS = 30;
export const FADE_FRAMES = 8;

// ─── Per-scene voiceover clips in public/vo/ ───
// Each clip is placed at its scene's absolute start frame via <Sequence>.
// Scene durations = clip duration + 0.5s breathing room.
// Clip durations: problem 10.0s, meet-enso 3.8s, voice 7.6s, floorplan 1.5s,
//   flythrough 4.1s, furniture 6.2s, purchase 3.1s, outro 1.6s
export const SCENE_STARTS_SEC = [
  0.0,      // intro — logo (music only)
  1.2,      // tagline — brand moment (music only)
  2.3,      // problem — "Designing a room…" (clip 10.0s)
  12.8,     // meet-enso — "Meet Enso. Your personal AI…" (clip 3.8s)
  17.1,     // voice — "Just describe your style…" (clip 7.6s)
  25.2,     // floorplan — "upload a floorplan," (clip 1.5s)
  27.2,     // flythrough — "and watch AI transform…" (clip 4.1s)
  31.8,     // furniture — "Every piece is real…" (clip 6.2s)
  38.5,     // purchase — "Love the result?…" (clip 3.1s)
  42.1,     // demo-1 — screen recording 1 (32.6s)
  74.8,     // demo-2 — screen recording 2 (53.2s)
  128.0,    // outro — "Your space, complete." (clip 1.6s)
];

export const TOTAL_DURATION_SEC = 131.5;

export function beatSyncedDurations(): number[] {
  return SCENE_STARTS_SEC.map((t, i) => {
    const nextT =
      i < SCENE_STARTS_SEC.length - 1
        ? SCENE_STARTS_SEC[i + 1]
        : TOTAL_DURATION_SEC;
    const rawFrames = Math.round((nextT - t) * FPS);
    return i < SCENE_STARTS_SEC.length - 1
      ? rawFrames + FADE_FRAMES
      : rawFrames;
  });
}

export function totalCompositionFrames(): number {
  const durs = beatSyncedDurations();
  const numTransitions = durs.length - 1;
  return durs.reduce((a, b) => a + b, 0) - numTransitions * FADE_FRAMES;
}
