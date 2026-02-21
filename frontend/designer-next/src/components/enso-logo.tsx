"use client";

import { useState, useEffect, useId } from "react";

interface EnsoLogoProps {
  size?: number;
  color?: string;
  animate?: boolean;
  className?: string;
}

/**
 * Filled brushstroke path — variable width, thick at 9 o'clock,
 * tapering to a point at 5 o'clock. Outer contour follows r≈27,
 * inner contour follows r≈19, with a rounded cap at the start
 * and a pointed taper at the end.
 */
const BRUSH_PATH =
  "M55 26C57 12 44 2 29 3C14 3 2 15 3 31C3 47 15 57 32 57C44 56 51 48 51 41C48 46 40 51 31 50C19 50 11 42 12 30C11 17 19 9 30 10C41 10 50 17 49 28Q52 24 55 26Z";

/** Uniform-stroke center path used for draw / unwind animations */
const STROKE_PATH = "M52 28C52 16 42 8 30 8C18 8 9 17 9 30C9 43 18 52 31 52C40 52 47 46 50 40";

/* ── Static logo (filled brushstroke) ──────────────────────────── */

export function EnsoLogo({
  size = 60,
  color = "currentColor",
  animate = false,
  className,
}: EnsoLogoProps) {
  const maskId = useId();

  if (animate) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 60 60"
        fill="none"
        className={className}
        style={{ display: "block" }}
      >
        <defs>
          <mask id={maskId}>
            {/* Wide stroke reveals the brushstroke shape as it draws */}
            <path
              d={STROKE_PATH}
              stroke="white"
              strokeWidth={20}
              strokeLinecap="round"
              fill="none"
              style={{
                strokeDasharray: 160,
                strokeDashoffset: 160,
                animation: "ensoDrawStroke 2s cubic-bezier(0.4, 0, 0.2, 1) forwards",
              }}
            />
          </mask>
        </defs>
        {/* Brushstroke revealed progressively by the mask */}
        <path d={BRUSH_PATH} fill={color} mask={`url(#${maskId})`} />
      </svg>
    );
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 60 60"
      fill="none"
      className={className}
      style={{ display: "block" }}
    >
      <path d={BRUSH_PATH} fill={color} />
    </svg>
  );
}

/* ── Scroll-driven hero enso ───────────────────────────────────── */

/**
 * Used on the landing page hero. On load the stroke draws in and the
 * brushstroke fades over it. As the user scrolls, the brushstroke
 * fades out and the stroke "unwinds" back to nothing.
 *
 * @param scrollProgress 0 = top of page (fully drawn), 1 = hero
 *   scrolled away (fully unwound).
 */
export function ScrollEnso({
  size = 100,
  color = "#1a1a38",
  scrollProgress = 0,
}: {
  size?: number;
  color?: string;
  scrollProgress?: number;
}) {
  const maskId = useId();
  const [phase, setPhase] = useState<"drawing" | "ready">("drawing");

  useEffect(() => {
    const timer = setTimeout(() => setPhase("ready"), 2300);
    return () => clearTimeout(timer);
  }, []);

  if (phase === "drawing") {
    return (
      <svg width={size} height={size} viewBox="0 0 60 60" fill="none" style={{ display: "block" }}>
        <defs>
          <mask id={maskId}>
            <path
              d={STROKE_PATH}
              stroke="white"
              strokeWidth={20}
              strokeLinecap="round"
              fill="none"
              style={{
                strokeDasharray: 160,
                strokeDashoffset: 160,
                animation: "ensoDrawStroke 2s cubic-bezier(0.4, 0, 0.2, 1) forwards",
              }}
            />
          </mask>
        </defs>
        <path d={BRUSH_PATH} fill={color} mask={`url(#${maskId})`} />
      </svg>
    );
  }

  /* Scroll-controlled phase: unwind as user scrolls down */
  const p = Math.min(1, Math.max(0, scrollProgress));
  const dashOffset = p * 160;
  const brushOpacity = Math.max(0, 1 - p * 2.5);
  const strokeOpacity = p > 0.05 ? 1 : 0;

  return (
    <svg width={size} height={size} viewBox="0 0 60 60" fill="none" style={{ display: "block" }}>
      {/* Stroke that unwinds */}
      <path
        d={STROKE_PATH}
        stroke={color}
        strokeWidth={5}
        strokeLinecap="round"
        fill="none"
        style={{
          strokeDasharray: 160,
          strokeDashoffset: dashOffset,
          opacity: strokeOpacity,
        }}
      />
      {/* Filled brushstroke that fades out */}
      <path d={BRUSH_PATH} fill={color} style={{ opacity: brushOpacity }} />
    </svg>
  );
}

/* ── Loading spinner ───────────────────────────────────────────── */

export function EnsoSpinner({ size = 48, color = "#1a1a38" }: { size?: number; color?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 60 60" fill="none" style={{ display: "block" }}>
      <path
        d={STROKE_PATH}
        stroke={color}
        strokeWidth={5}
        strokeLinecap="round"
        fill="none"
        style={{
          strokeDasharray: 160,
          strokeDashoffset: 160,
          animation: "ensoDrawLoop 3s ease-in-out infinite",
        }}
      />
    </svg>
  );
}
