import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { beatSyncedDurations, FADE_FRAMES, totalCompositionFrames } from "./beat-map";

import { IntroScene } from "./scenes/IntroScene";
import { TaglineScene } from "./scenes/TaglineScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { MeetEnsoScene } from "./scenes/MeetEnsoScene";
import { VoiceScene } from "./scenes/VoiceScene";
import { FloorplanScene } from "./scenes/FloorplanScene";
import { FlythroughScene } from "./scenes/FlythroughScene";
import { FurnitureScene } from "./scenes/FurnitureScene";
import { PurchaseScene } from "./scenes/PurchaseScene";
import { OutroScene } from "./scenes/OutroScene";

const durations = beatSyncedDurations();

const SCENES = [
  { id: "intro", dur: durations[0], Component: IntroScene },
  { id: "tagline", dur: durations[1], Component: TaglineScene },
  { id: "problem", dur: durations[2], Component: ProblemScene },
  { id: "meet-enso", dur: durations[3], Component: MeetEnsoScene },
  { id: "voice", dur: durations[4], Component: VoiceScene },
  { id: "floorplan", dur: durations[5], Component: FloorplanScene },
  { id: "flythrough", dur: durations[6], Component: FlythroughScene },
  { id: "furniture", dur: durations[7], Component: FurnitureScene },
  { id: "purchase", dur: durations[8], Component: PurchaseScene },
  { id: "outro", dur: durations[9], Component: OutroScene },
];

// Per-scene voice clips mapped to their absolute composition frame.
// Computed from TransitionSeries: each scene starts at
// sum(prev durations) - numPrevTransitions * FADE_FRAMES.
function computeSceneAbsFrames(): number[] {
  const frames: number[] = [0];
  for (let i = 1; i < durations.length; i++) {
    frames.push(frames[i - 1] + durations[i - 1] - FADE_FRAMES);
  }
  return frames;
}

const sceneFrames = computeSceneAbsFrames();

// Voice clips: scene index → filename in public/vo/
const VOICE_CLIPS: [number, string][] = [
  [2, "problem"],      // "Designing a room…"
  [3, "meet-enso"],    // "Meet Enso. Your personal AI…"
  [4, "voice"],        // "Just describe your style…"
  [5, "floorplan"],    // "upload a floorplan,"
  [6, "flythrough"],   // "and watch AI transform…"
  [7, "furniture"],    // "Every piece is real…"
  [8, "purchase"],     // "Love the result?…"
  [9, "outro"],        // "Your space, complete."
];

// Varied transitions
type TransitionKind = "fade" | "slide-right" | "wipe-left";
const TRANSITION_TYPES: TransitionKind[] = [
  "fade",        // intro → tagline
  "fade",        // tagline → problem
  "slide-right", // problem → meet-enso (entering the solution)
  "fade",        // meet-enso → voice
  "fade",        // voice → floorplan
  "fade",        // floorplan → flythrough
  "fade",        // flythrough → furniture
  "wipe-left",   // furniture → purchase (entering checkout)
  "fade",        // purchase → outro
];

// biome-ignore lint/suspicious/noExplicitAny: transition presentation union
function getPresentation(kind: TransitionKind): any {
  switch (kind) {
    case "slide-right":
      return slide({ direction: "from-right" });
    case "wipe-left":
      return wipe({ direction: "from-left" });
    default:
      return fade();
  }
}

const GRAIN_SVG = encodeURIComponent(
  '<svg viewBox="0 0 256 256" xmlns="http://www.w3.org/2000/svg"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" stitchTiles="stitch"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>',
);

// First voice clip starts at the Problem scene
const FIRST_VO_FRAME = sceneFrames[2];

export const EnsoPromo: React.FC = () => {
  const frame = useCurrentFrame();
  const totalFrames = totalCompositionFrames();

  // Music plays full volume during intro/tagline, ducks when voice starts
  const musicVolume = interpolate(
    frame,
    [0, FIRST_VO_FRAME, FIRST_VO_FRAME + 15, totalFrames - 60, totalFrames - 20, totalFrames],
    [0.3, 0.3, 0.12, 0.12, 0.3, 0.3],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const grainX = Math.sin(frame * 0.37) * 8;
  const grainY = Math.cos(frame * 0.29) * 8;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#faf9f7",
        filter: "saturate(1.06) contrast(1.02)",
      }}
    >
      <Audio src={staticFile("music.mp3")} volume={musicVolume} />

      {/* Per-scene voice clips — each placed at its scene's exact start frame */}
      {VOICE_CLIPS.map(([sceneIdx, name]) => (
        <Sequence key={name} from={sceneFrames[sceneIdx]}>
          <Audio src={staticFile(`vo/${name}.mp3`)} volume={0.85} />
        </Sequence>
      ))}

      <TransitionSeries>
        {SCENES.map((scene, i) => (
          <React.Fragment key={scene.id}>
            {i > 0 && (
              <TransitionSeries.Transition
                presentation={getPresentation(TRANSITION_TYPES[i - 1])}
                timing={linearTiming({ durationInFrames: FADE_FRAMES })}
              />
            )}
            <TransitionSeries.Sequence durationInFrames={scene.dur}>
              <scene.Component />
            </TransitionSeries.Sequence>
          </React.Fragment>
        ))}
      </TransitionSeries>

      {/* Film grain overlay */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "150%",
          height: "150%",
          backgroundImage: `url("data:image/svg+xml,${GRAIN_SVG}")`,
          backgroundSize: "256px 256px",
          opacity: 0.028,
          mixBlendMode: "overlay" as const,
          pointerEvents: "none" as const,
          transform: `translate(${grainX}px, ${grainY}px)`,
        }}
      />

      {/* Vignette */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.1) 100%)",
          pointerEvents: "none" as const,
        }}
      />
    </AbsoluteFill>
  );
};
