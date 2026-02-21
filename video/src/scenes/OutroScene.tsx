import React from "react";
import { AbsoluteFill, useCurrentFrame, interpolate, Easing } from "remotion";
import { COLORS } from "../components/DesignTokens";
import { EnsoLogoDraw } from "../components/EnsoLogoDraw";
import { AnimatedText } from "../components/AnimatedText";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const { fontFamily: displayFont } = loadRighteous();
const { fontFamily: bodyFont } = loadSpaceGrotesk();

const SPONSORS = ["Anthropic", "ElevenLabs", "Stripe", "Supabase", "Miro"];

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();

  const footerHeight = 140;

  return (
    <AbsoluteFill style={{ background: COLORS.accent }}>
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at 50% 40%, rgba(219,80,74,0) 0%, rgba(160,42,38,0.4) 100%)",
        }}
      />

      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          paddingBottom: footerHeight,
        }}
      >
        <EnsoLogoDraw size={100} color={COLORS.text} drawDuration={22} delay={0} />

        <AnimatedText delay={8} duration={12}>
          <h2
            style={{
              fontFamily: displayFont,
              fontSize: 48,
              fontWeight: 400,
              color: COLORS.text,
              letterSpacing: "0.02em",
              textAlign: "center",
              marginTop: 20,
              lineHeight: 1.15,
            }}
          >
            your space, complete.
          </h2>
        </AnimatedText>

        <div
          style={{
            marginTop: 28,
            opacity: interpolate(frame, [18, 30], [0, 1], {
              easing: Easing.out(Easing.cubic),
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            background: COLORS.text,
            color: COLORS.bg,
            padding: "12px 36px",
            borderRadius: 100,
            fontFamily: bodyFont,
            fontWeight: 600,
            fontSize: 15,
            letterSpacing: "0.02em",
            boxShadow: "0 4px 24px rgba(26,26,56,0.25)",
          }}
        >
          Try Enso — enso.design
        </div>
      </AbsoluteFill>

      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: footerHeight,
          background: COLORS.charcoal,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 28,
          }}
        >
          <span
            style={{
              fontFamily: bodyFont,
              fontSize: 10,
              color: "rgba(250,249,247,0.35)",
              textTransform: "uppercase" as const,
              letterSpacing: "0.12em",
              fontWeight: 500,
            }}
          >
            Powered by
          </span>
          {SPONSORS.map((s, i) => {
            const sOpacity = interpolate(
              frame,
              [25 + i * 4, 33 + i * 4],
              [0, 1],
              {
                easing: Easing.out(Easing.cubic),
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              },
            );
            return (
              <span
                key={s}
                style={{
                  fontFamily: bodyFont,
                  fontSize: 13,
                  fontWeight: 500,
                  color: "rgba(250,249,247,0.55)",
                  letterSpacing: "0.02em",
                  opacity: sOpacity,
                }}
              >
                {s}
              </span>
            );
          })}
        </div>

        <span
          style={{
            fontFamily: bodyFont,
            fontSize: 10,
            color: "rgba(250,249,247,0.25)",
            letterSpacing: "0.08em",
            textTransform: "uppercase" as const,
          }}
        >
          HackEurope 2026
        </span>
      </div>
    </AbsoluteFill>
  );
};
