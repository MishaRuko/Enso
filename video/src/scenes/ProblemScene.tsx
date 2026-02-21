import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";
import { COLORS } from "../components/DesignTokens";
import { AnimatedText } from "../components/AnimatedText";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const { fontFamily: bodyFont } = loadSpaceGrotesk();

const LINES = [
  "Designing a room is overwhelming.",
  "Endless browsing. Mismatched furniture. No spatial sense.",
  "What if AI could handle it all?",
];

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
      }}
    >
      {LINES.map((line, i) => {
        // Stagger: clip plays from scene start, sentences at ~0s and ~3.5s in clip
        // Line 0: immediate (matches "Designing a room…")
        // Line 1: frame 105 (3.5s, matches "Endless browsing…")
        // Line 2: frame 260 (8.7s, accent bridge near end of problem clip)
        const delays = [0, 105, 260];
        const delay = delays[i];

        if (i === 2) {
          const revealProgress = interpolate(
            frame - delay,
            [0, 20],
            [0, 100],
            {
              easing: Easing.out(Easing.poly(5)),
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            },
          );
          const opacity = interpolate(
            frame - delay,
            [0, 10],
            [0, 1],
            {
              easing: Easing.out(Easing.cubic),
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            },
          );
          return (
            <div
              key={line}
              style={{
                opacity,
                clipPath: `inset(0 ${100 - revealProgress}% 0 0)`,
              }}
            >
              <p
                style={{
                  fontFamily: bodyFont,
                  fontSize: 36,
                  fontWeight: 600,
                  color: COLORS.accent,
                  textAlign: "center",
                  lineHeight: 1.4,
                  maxWidth: 800,
                }}
              >
                {line}
              </p>
            </div>
          );
        }
        return (
          <AnimatedText key={line} delay={delay} duration={12}>
            <p
              style={{
                fontFamily: bodyFont,
                fontSize: 28,
                fontWeight: 400,
                color: COLORS.text,
                textAlign: "center",
                lineHeight: 1.4,
                maxWidth: 800,
              }}
            >
              {line}
            </p>
          </AnimatedText>
        );
      })}
    </AbsoluteFill>
  );
};
