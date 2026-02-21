import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
  Easing,
} from "remotion";
import { COLORS, CONTAINER } from "../components/DesignTokens";
import { AnimatedText } from "../components/AnimatedText";
import { GlassCard } from "../components/GlassCard";
import { loadFont as loadRighteous } from "@remotion/google-fonts/Righteous";
import { loadFont as loadSpaceGrotesk } from "@remotion/google-fonts/SpaceGrotesk";

const { fontFamily: displayFont } = loadRighteous();
const { fontFamily: bodyFont } = loadSpaceGrotesk();

const ITEMS = [
  { name: "KIVIK Sofa", price: "$599" },
  { name: "LACK Coffee Table", price: "$49" },
  { name: "BILLY Bookshelf", price: "$79" },
  { name: "STRANDMON Armchair", price: "$329" },
  { name: "HEKTAR Floor Lamp", price: "$69" },
];

export const PurchaseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Eased card entrance
  const cardX = interpolate(frame, [0, 20], [180, 0], {
    easing: Easing.out(Easing.poly(5)),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const cardOpacity = interpolate(frame, [0, 12], [0, 1], {
    easing: Easing.out(Easing.cubic),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Counter-motion: title drifts slightly left as card enters from right
  const titleCounterX = interpolate(frame, [0, 20], [0, -8], {
    easing: Easing.out(Easing.poly(3)),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const checkScale = spring({
    frame: frame - 50,
    fps,
    config: { stiffness: 200, damping: 12 },
  });
  const checkOpacity = frame > 50 ? 1 : 0;

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
        }}
      >
        {/* Left: title with counter-motion */}
        <div style={{ flex: 1, transform: `translateX(${titleCounterX}px)` }}>
          <AnimatedText delay={0} duration={10}>
            <div
              style={{
                fontFamily: bodyFont,
                fontSize: 13,
                fontWeight: 600,
                color: COLORS.sage,
                letterSpacing: "0.16em",
                textTransform: "uppercase" as const,
                marginBottom: 12,
              }}
            >
              One-Click Purchase
            </div>
          </AnimatedText>
          <AnimatedText delay={3} duration={12}>
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
              Love it?
              <br />
              Buy it all.
            </h2>
          </AnimatedText>
          <AnimatedText delay={8} duration={12}>
            <p
              style={{
                fontFamily: bodyFont,
                fontSize: 16,
                color: COLORS.textSecondary,
                lineHeight: 1.6,
                maxWidth: 360,
                marginTop: 16,
              }}
            >
              Every piece from your AI-designed room — one click, one checkout
              via Stripe.
            </p>
          </AnimatedText>
        </div>

        {/* Right: Checkout card */}
        <div
          style={{
            opacity: cardOpacity,
            transform: `translateX(${cardX}px)`,
          }}
        >
          <GlassCard style={{ padding: "32px 28px", width: 340 }}>
            <div
              style={{
                fontFamily: bodyFont,
                fontSize: 11,
                fontWeight: 600,
                color: COLORS.textMuted,
                letterSpacing: "0.12em",
                textTransform: "uppercase" as const,
                marginBottom: 18,
              }}
            >
              Order Summary
            </div>

            {ITEMS.map((item, i) => {
              const itemOpacity = interpolate(
                frame,
                [10 + i * 4, 18 + i * 4],
                [0, 1],
                {
                  easing: Easing.out(Easing.cubic),
                  extrapolateLeft: "clamp",
                  extrapolateRight: "clamp",
                },
              );
              return (
                <div
                  key={item.name}
                  style={{
                    opacity: itemOpacity,
                    display: "flex",
                    justifyContent: "space-between",
                    fontFamily: bodyFont,
                    fontSize: 13,
                    color: COLORS.text,
                    padding: "6px 0",
                    borderBottom: "1px solid rgba(26,26,56,0.05)",
                  }}
                >
                  <span>{item.name}</span>
                  <span style={{ fontWeight: 600 }}>{item.price}</span>
                </div>
              );
            })}

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontFamily: bodyFont,
                fontSize: 15,
                fontWeight: 600,
                color: COLORS.text,
                marginTop: 12,
                paddingTop: 12,
                borderTop: "2px solid rgba(26,26,56,0.1)",
              }}
            >
              <span>Total</span>
              <span>$1,125</span>
            </div>

            <div style={{ position: "relative", marginTop: 18 }}>
              <button
                style={{
                  width: "100%",
                  background: COLORS.stripePurple,
                  color: COLORS.white,
                  padding: "12px 32px",
                  borderRadius: 100,
                  fontFamily: bodyFont,
                  fontWeight: 600,
                  fontSize: 14,
                  letterSpacing: "0.02em",
                  border: "none",
                  boxShadow: "0 4px 16px rgba(99,91,255,0.3)",
                }}
              >
                Pay with Stripe
              </button>
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "#4ade80",
                  borderRadius: 100,
                  opacity: checkOpacity,
                  transform: `scale(${checkScale})`,
                }}
              >
                <svg
                  width={22}
                  height={22}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="white"
                  strokeWidth={3}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </AbsoluteFill>
  );
};
