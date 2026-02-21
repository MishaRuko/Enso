import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";
import { COLORS } from "../components/DesignTokens";
import { AnimatedText } from "../components/AnimatedText";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const { fontFamily: displayFont } = loadRighteous();
const { fontFamily: bodyFont } = loadSpaceGrotesk();

export const TaglineScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Clip-path reveal for headline — premium cinematic feel
  const revealProgress = interpolate(frame, [0, 22], [0, 100], {
    easing: Easing.out(Easing.poly(5)),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ overflow: "hidden" }}>
        <div
          style={{
            clipPath: `inset(0 ${100 - revealProgress}% 0 0)`,
          }}
        >
          <h1
            style={{
              fontFamily: displayFont,
              fontSize: 72,
              fontWeight: 400,
              letterSpacing: "0.02em",
              lineHeight: 1.1,
              color: COLORS.text,
              textAlign: "center",
            }}
          >
            your space,
            <br />
            complete.
          </h1>
        </div>
      </div>

      <AnimatedText delay={10} duration={12}>
        <p
          style={{
            fontFamily: bodyFont,
            fontSize: 20,
            color: COLORS.textSecondary,
            lineHeight: 1.7,
            maxWidth: 480,
            textAlign: "center",
            marginTop: 24,
          }}
        >
          AI-powered interior design — from voice to fully furnished 3D room in
          minutes.
        </p>
      </AnimatedText>
    </AbsoluteFill>
  );
};
