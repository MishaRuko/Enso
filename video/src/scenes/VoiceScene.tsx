import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";
import { COLORS, CONTAINER } from "../components/DesignTokens";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { WaveformViz } from "../components/WaveformViz";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const { fontFamily: displayFont } = loadRighteous();
const { fontFamily: bodyFont } = loadSpaceGrotesk();

const PREFERENCES = [
  "Scandinavian minimal",
  "Budget: $3,000",
  "Living room \u2014 5m \u00d7 4m",
  "Warm tones, natural wood",
  "Open shelving preferred",
];

export const VoiceScene: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill
      style={{
        background: COLORS.bg,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          ...CONTAINER,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 64,
          height: "100%",
        }}
      >
        {/* Left: Voice consultation */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-start",
            gap: 20,
            flex: 1,
          }}
        >
          <AnimatedText delay={0} duration={10}>
            <div
              style={{
                fontFamily: bodyFont,
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.accent,
                letterSpacing: "0.16em",
                textTransform: "uppercase" as const,
              }}
            >
              Your Remote Designer
            </div>
          </AnimatedText>

          <AnimatedText delay={4} duration={10}>
            <h2
              style={{
                fontFamily: displayFont,
                fontSize: 44,
                fontWeight: 400,
                color: COLORS.text,
                letterSpacing: "0.02em",
                lineHeight: 1.15,
              }}
            >
              Just describe
              <br />
              your style.
            </h2>
          </AnimatedText>

          <AnimatedText delay={8} duration={10}>
            <WaveformViz
              barCount={32}
              width={420}
              height={80}
              color={COLORS.accent}
            />
          </AnimatedText>

          <AnimatedText delay={14} duration={10}>
            <p
              style={{
                fontFamily: bodyFont,
                fontSize: 16,
                color: COLORS.textSecondary,
                maxWidth: 380,
                lineHeight: 1.6,
                marginTop: 4,
              }}
            >
              Enso listens, understands your taste, and handles the rest —
              like having a remote designer who truly gets you.
            </p>
          </AnimatedText>
        </div>

        {/* Right: Preferences card */}
        <AnimatedText delay={6} duration={12} direction="right">
          <GlassCard
            style={{
              padding: "36px 32px",
              width: 340,
            }}
          >
            <div
              style={{
                fontFamily: bodyFont,
                fontSize: 11,
                fontWeight: 600,
                color: COLORS.sage,
                letterSpacing: "0.16em",
                textTransform: "uppercase" as const,
                marginBottom: 18,
              }}
            >
              Design Preferences
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {PREFERENCES.map((pref, i) => {
                const tagOpacity = interpolate(
                  frame,
                  [12 + i * 6, 20 + i * 6],
                  [0, 1],
                  {
                    easing: Easing.out(Easing.cubic),
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  },
                );
                const tagX = interpolate(
                  frame,
                  [12 + i * 6, 20 + i * 6],
                  [16, 0],
                  {
                    easing: Easing.out(Easing.poly(5)),
                    extrapolateLeft: "clamp",
                    extrapolateRight: "clamp",
                  },
                );
                return (
                  <div
                    key={pref}
                    style={{
                      opacity: tagOpacity,
                      transform: `translateX(${tagX}px)`,
                      fontFamily: bodyFont,
                      fontSize: 14,
                      fontWeight: 500,
                      color: COLORS.text,
                      padding: "8px 14px",
                      background: "rgba(236,230,219,0.35)",
                      borderRadius: 10,
                      border: "1px solid rgba(236,230,219,0.5)",
                    }}
                  >
                    {pref}
                  </div>
                );
              })}
            </div>
          </GlassCard>
        </AnimatedText>
      </div>
    </AbsoluteFill>
  );
};
