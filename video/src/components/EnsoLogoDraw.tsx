import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import { easeInOut } from "./DesignTokens";

const BRUSH_PATH =
  "M55 26C57 12 44 2 29 3C14 3 2 15 3 31C3 47 15 57 32 57C44 56 51 48 51 41C48 46 40 51 31 50C19 50 11 42 12 30C11 17 19 9 30 10C41 10 50 17 49 28Q52 24 55 26Z";

const STROKE_PATH =
  "M52 28C52 16 42 8 30 8C18 8 9 17 9 30C9 43 18 52 31 52C40 52 47 46 50 40";

interface EnsoLogoDrawProps {
  size?: number;
  color?: string;
  drawDuration?: number;
  delay?: number;
}

export const EnsoLogoDraw: React.FC<EnsoLogoDrawProps> = ({
  size = 200,
  color = "#1a1a38",
  drawDuration = 60,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - delay;

  const rawProgress = interpolate(localFrame, [0, drawDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const drawProgress = easeInOut(rawProgress);
  const dashOffset = 160 * (1 - drawProgress);

  const brushOpacity = interpolate(
    localFrame,
    [drawDuration * 0.6, drawDuration],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

  const maskId = `enso-mask-${delay}`;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 60 60"
      fill="none"
      style={{ display: "block" }}
    >
      <defs>
        <mask id={maskId}>
          <path
            d={STROKE_PATH}
            stroke="white"
            strokeWidth={20}
            strokeLinecap="round"
            fill="none"
            strokeDasharray={160}
            strokeDashoffset={dashOffset}
          />
        </mask>
      </defs>
      <path
        d={BRUSH_PATH}
        fill={color}
        mask={`url(#${maskId})`}
        opacity={1}
      />
      <path d={BRUSH_PATH} fill={color} opacity={brushOpacity} />
    </svg>
  );
};

export const EnsoLogoStatic: React.FC<{
  size?: number;
  color?: string;
}> = ({ size = 60, color = "currentColor" }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 60 60"
    fill="none"
    style={{ display: "block" }}
  >
    <path d={BRUSH_PATH} fill={color} />
  </svg>
);
