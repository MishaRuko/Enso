import React from "react";
import { useCurrentFrame, interpolate, Easing } from "remotion";

interface AnimatedTextProps {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  style?: React.CSSProperties;
  direction?: "up" | "right" | "scale";
}

export const AnimatedText: React.FC<AnimatedTextProps> = ({
  children,
  delay = 0,
  duration = 15,
  style,
  direction = "up",
}) => {
  const frame = useCurrentFrame();
  const localFrame = frame - delay;

  const opacity = interpolate(localFrame, [0, duration * 0.45], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  let transform = "";
  if (direction === "up") {
    const y = interpolate(localFrame, [0, duration * 0.65], [12, 0], {
      easing: Easing.out(Easing.poly(5)),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    transform = `translateY(${y}px)`;
  } else if (direction === "right") {
    const x = interpolate(localFrame, [0, duration * 0.65], [-12, 0], {
      easing: Easing.out(Easing.poly(5)),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    transform = `translateX(${x}px)`;
  } else if (direction === "scale") {
    const s = interpolate(localFrame, [0, duration * 0.65], [0.92, 1], {
      easing: Easing.out(Easing.poly(4)),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    transform = `scale(${s})`;
  }

  return (
    <div style={{ opacity, transform, willChange: "transform, opacity", ...style }}>
      {children}
    </div>
  );
};
