import type React from "react";

export const COLORS = {
  bg: "#faf9f7",
  bgElevated: "rgba(250, 249, 247, 0.97)",
  text: "#1a1a38",
  textSecondary: "rgba(26, 26, 56, 0.55)",
  textMuted: "rgba(26, 26, 56, 0.38)",
  textHint: "rgba(26, 26, 56, 0.22)",
  accent: "#db504a",
  accentHover: "#c4423d",
  accentGlow: "rgba(219, 80, 74, 0.15)",
  accentSubtle: "rgba(219, 80, 74, 0.06)",
  parchment: "#ece6db",
  parchmentSubtle: "rgba(236, 230, 219, 0.4)",
  sage: "#7c8c6e",
  sageGlow: "rgba(124, 140, 110, 0.12)",
  charcoal: "#2e2e38",
  charcoalLight: "#3d3d4a",
  surface: "rgba(250, 249, 247, 0.7)",
  border: "rgba(26, 26, 56, 0.07)",
  stripePurple: "#635bff",
  white: "#ffffff",
  warmWhite: "#fff5ee",
  coolBlue: "#93c5fd",
  warmYellow: "#fef3c7",
} as const;

export const GLASS = {
  background: "rgba(250,249,247,0.55)",
  border: "1px solid rgba(236,230,219,0.6)",
  boxShadow:
    "0 4px 40px rgba(26,26,56,0.03), inset 0 1px 0 rgba(255,255,255,0.5)",
  borderRadius: 28,
} as const;

export const CARD_PARCHMENT = {
  background: "rgba(236,230,219,0.25)",
  border: "1px solid rgba(236,230,219,0.5)",
  boxShadow: "0 2px 24px rgba(26,26,56,0.03)",
  borderRadius: 28,
} as const;

export const SHADOWS = {
  sm: "0 2px 8px rgba(26, 26, 56, 0.03)",
  md: "0 4px 24px rgba(26, 26, 56, 0.05)",
  lg: "0 4px 80px rgba(26, 26, 56, 0.06), 0 0 0 1px rgba(26, 26, 56, 0.03)",
  glow: "0 4px 40px rgba(26, 26, 56, 0.08)",
  button: "0 4px 24px rgba(26,26,56,0.25)",
} as const;

export function smoothstep(t: number): number {
  return t * t * (3 - 2 * t);
}

export function easeOut(t: number): number {
  return 1 - (1 - t) ** 3;
}

export function easeInOut(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export const CONTAINER: React.CSSProperties = {
  maxWidth: 1280,
  width: "100%",
  margin: "0 auto",
  padding: "0 80px",
  boxSizing: "border-box" as const,
};
