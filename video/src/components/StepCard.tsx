import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { COLORS, CARD_PARCHMENT } from "./DesignTokens";

interface StepCardProps {
  num: string;
  label: string;
  desc: string;
  delay: number;
  icon: React.ReactNode;
}

export const StepCard: React.FC<StepCardProps> = ({
  num,
  label,
  desc,
  delay,
  icon,
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - delay;

  const opacity = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const y = interpolate(localFrame, [0, 25], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${y}px)`,
        background: CARD_PARCHMENT.background,
        border: CARD_PARCHMENT.border,
        boxShadow: CARD_PARCHMENT.boxShadow,
        borderRadius: CARD_PARCHMENT.borderRadius,
        padding: "40px 24px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        textAlign: "center" as const,
        width: 220,
      }}
    >
      <span
        style={{
          fontSize: 12,
          fontWeight: 600,
          color: COLORS.accent,
          letterSpacing: "0.16em",
          textTransform: "uppercase" as const,
          marginBottom: 20,
        }}
      >
        {num}
      </span>
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: "50%",
          background: "rgba(219,80,74,0.07)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: COLORS.text,
          marginBottom: 20,
        }}
      >
        {icon}
      </div>
      <div
        style={{
          fontSize: 15,
          fontWeight: 600,
          color: COLORS.text,
          letterSpacing: "0.01em",
          marginBottom: 10,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 12,
          color: COLORS.textMuted,
          lineHeight: 1.75,
        }}
      >
        {desc}
      </div>
    </div>
  );
};
