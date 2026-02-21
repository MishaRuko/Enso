import React from "react";
import { useCurrentFrame } from "remotion";
import { COLORS } from "./DesignTokens";

interface WaveformVizProps {
  barCount?: number;
  width?: number;
  height?: number;
  color?: string;
}

export const WaveformViz: React.FC<WaveformVizProps> = ({
  barCount = 24,
  width = 400,
  height = 120,
  color = COLORS.accent,
}) => {
  const frame = useCurrentFrame();
  const barWidth = (width / barCount) * 0.6;
  const gap = (width / barCount) * 0.4;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: gap,
        height,
        width,
      }}
    >
      {Array.from({ length: barCount }).map((_, i) => {
        const barHeight =
          15 +
          (height - 30) *
            0.5 *
            (1 +
              Math.sin(frame * 0.12 + i * 0.6) *
                Math.cos(frame * 0.08 + i * 0.3));
        return (
          <div
            key={i}
            style={{
              width: barWidth,
              height: barHeight,
              borderRadius: barWidth / 2,
              background: color,
              opacity: 0.6 + 0.4 * Math.sin(frame * 0.1 + i * 0.4),
            }}
          />
        );
      })}
    </div>
  );
};
