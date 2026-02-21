import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";
import { COLORS } from "../components/DesignTokens";
import { EnsoLogoDraw } from "../components/EnsoLogoDraw";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";

const { fontFamily: displayFont } = loadRighteous();

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();

  const ensoTextOpacity = interpolate(frame, [8, 22], [0, 0.14], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const ensoTextY = interpolate(frame, [8, 22], [20, 0], {
    easing: Easing.out(Easing.poly(5)),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: COLORS.accent,
        overflow: "hidden",
      }}
    >
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at 30% 50%, rgba(219,80,74,0) 0%, rgba(160,42,38,0.5) 100%)",
        }}
      />

      <AbsoluteFill
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          paddingBottom: 60,
        }}
      >
        <EnsoLogoDraw size={240} color={COLORS.text} drawDuration={25} />
      </AbsoluteFill>

      <div
        style={{
          position: "absolute",
          bottom: -20,
          right: 40,
          fontFamily: displayFont,
          fontSize: 340,
          fontWeight: 400,
          letterSpacing: "0.05em",
          lineHeight: 0.82,
          color: COLORS.text,
          opacity: ensoTextOpacity,
          transform: `translateY(${ensoTextY}px)`,
          userSelect: "none",
          whiteSpace: "nowrap",
        }}
      >
        ENSO
      </div>
    </AbsoluteFill>
  );
};
