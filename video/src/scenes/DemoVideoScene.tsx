import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";
import { COLORS } from "../components/DesignTokens";

export const DemoVideoScene: React.FC<{
  src: string;
  label: string;
}> = ({ src, label }) => {
  const frame = useCurrentFrame();

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  const labelY = interpolate(frame, [0, 20], [12, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.charcoal }}>
      <OffthreadVideo
        src={staticFile(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
        }}
      />

      {/* Label pill */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 48,
          opacity: labelOpacity,
          transform: `translateY(${labelY}px)`,
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            backgroundColor: COLORS.accent,
            boxShadow: `0 0 8px ${COLORS.accent}`,
          }}
        />
        <span
          style={{
            fontFamily: "Space Grotesk, sans-serif",
            fontSize: 18,
            fontWeight: 500,
            color: "rgba(255,255,255,0.85)",
            letterSpacing: "0.06em",
            textTransform: "uppercase" as const,
          }}
        >
          {label}
        </span>
      </div>
    </AbsoluteFill>
  );
};
