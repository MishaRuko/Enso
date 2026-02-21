import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
  Easing,
} from "remotion";
import { COLORS } from "../components/DesignTokens";
import { AnimatedText } from "../components/AnimatedText";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const { fontFamily: displayFont } = loadRighteous();
const { fontFamily: bodyFont } = loadSpaceGrotesk();

// Cute dotted-line Enso character — friendly AI designer mascot
function EnsoCharacter({ frame, fps }: { frame: number; fps: number }) {
  const scale = spring({ frame, fps, config: { stiffness: 80, damping: 14 } });
  const floatY = Math.sin(frame * 0.06) * 4;
  const waveAngle = Math.sin(frame * 0.12) * 8;

  // Blink every ~2 seconds
  const blinkCycle = frame % 60;
  const eyeScaleY = blinkCycle < 3 ? interpolate(blinkCycle, [0, 1.5, 3], [1, 0.1, 1]) : 1;

  // Dots that orbit the character
  const dotCount = 12;
  const dots = Array.from({ length: dotCount }, (_, i) => {
    const angle = (i / dotCount) * Math.PI * 2 + frame * 0.02;
    const radius = 110 + Math.sin(frame * 0.04 + i) * 8;
    return {
      cx: 150 + Math.cos(angle) * radius,
      cy: 160 + Math.sin(angle) * radius,
      r: 2.5 + Math.sin(i * 1.3) * 1,
      opacity: 0.15 + Math.sin(frame * 0.05 + i * 0.8) * 0.1,
    };
  });

  return (
    <svg
      width={300}
      height={320}
      viewBox="0 0 300 320"
      style={{
        transform: `scale(${scale}) translateY(${floatY}px)`,
      }}
    >
      {/* Orbiting dots */}
      {dots.map((d, i) => (
        <circle
          key={`dot-${i}`}
          cx={d.cx}
          cy={d.cy}
          r={d.r}
          fill={COLORS.accent}
          opacity={d.opacity}
        />
      ))}

      {/* Dotted circle aura */}
      <circle
        cx={150}
        cy={140}
        r={85}
        fill="none"
        stroke={COLORS.accent}
        strokeWidth={1.5}
        strokeDasharray="3 6"
        opacity={0.25}
      />

      {/* Head — warm circle */}
      <circle cx={150} cy={140} r={60} fill={COLORS.parchment} />
      <circle
        cx={150}
        cy={140}
        r={60}
        fill="none"
        stroke={COLORS.text}
        strokeWidth={2.5}
        strokeDasharray="4 3"
      />

      {/* Eyes */}
      <ellipse cx={133} cy={132} rx={5} ry={5 * eyeScaleY} fill={COLORS.text} />
      <ellipse cx={167} cy={132} rx={5} ry={5 * eyeScaleY} fill={COLORS.text} />

      {/* Friendly smile */}
      <path
        d="M 137 152 Q 150 164 163 152"
        fill="none"
        stroke={COLORS.text}
        strokeWidth={2.5}
        strokeLinecap="round"
      />

      {/* Cheek blush dots */}
      <circle cx={120} cy={148} r={7} fill={COLORS.accent} opacity={0.2} />
      <circle cx={180} cy={148} r={7} fill={COLORS.accent} opacity={0.2} />

      {/* Body — simple rounded shape */}
      <path
        d="M 115 195 Q 115 175 150 175 Q 185 175 185 195 L 185 240 Q 185 260 150 260 Q 115 260 115 240 Z"
        fill={COLORS.accent}
        opacity={0.9}
      />
      <path
        d="M 115 195 Q 115 175 150 175 Q 185 175 185 195 L 185 240 Q 185 260 150 260 Q 115 260 115 240 Z"
        fill="none"
        stroke={COLORS.text}
        strokeWidth={2}
        strokeDasharray="4 3"
      />

      {/* Enso brushstroke on chest */}
      <circle
        cx={150}
        cy={218}
        r={14}
        fill="none"
        stroke={COLORS.white}
        strokeWidth={3}
        strokeLinecap="round"
        strokeDasharray="75"
        strokeDashoffset={10}
        opacity={0.8}
      />

      {/* Waving hand */}
      <g transform={`translate(190, 200) rotate(${waveAngle}, 0, -15)`}>
        <circle cx={18} cy={-15} r={10} fill={COLORS.parchment} />
        <circle
          cx={18}
          cy={-15}
          r={10}
          fill="none"
          stroke={COLORS.text}
          strokeWidth={2}
          strokeDasharray="3 3"
        />
      </g>

      {/* Little design tool (pencil) in other hand */}
      <g transform="translate(100, 215) rotate(-20)">
        <rect x={-3} y={-22} width={6} height={18} rx={2} fill={COLORS.sage} />
        <polygon points="-2,-22 2,-22 0,-28" fill={COLORS.text} />
      </g>
    </svg>
  );
}

export const MeetEnsoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const subtitleOpacity = interpolate(frame, [20, 35], [0, 1], {
    easing: Easing.out(Easing.cubic),
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
        gap: 8,
      }}
    >
      <EnsoCharacter frame={frame} fps={fps} />

      <AnimatedText delay={5} duration={12}>
        <h2
          style={{
            fontFamily: displayFont,
            fontSize: 56,
            fontWeight: 400,
            color: COLORS.text,
            letterSpacing: "0.02em",
            textAlign: "center",
            marginTop: -8,
          }}
        >
          Meet Enso
        </h2>
      </AnimatedText>

      <div style={{ opacity: subtitleOpacity }}>
        <p
          style={{
            fontFamily: bodyFont,
            fontSize: 18,
            color: COLORS.textSecondary,
            textAlign: "center",
            lineHeight: 1.6,
          }}
        >
          Your personal AI interior designer
        </p>
      </div>
    </AbsoluteFill>
  );
};
