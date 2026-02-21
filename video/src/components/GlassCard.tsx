import React from "react";
import { GLASS, CARD_PARCHMENT } from "./DesignTokens";

interface GlassCardProps {
  children: React.ReactNode;
  variant?: "glass" | "parchment";
  style?: React.CSSProperties;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  variant = "glass",
  style,
}) => {
  const base = variant === "glass" ? GLASS : CARD_PARCHMENT;

  return (
    <div
      style={{
        background: base.background,
        border: base.border,
        boxShadow: base.boxShadow,
        borderRadius: base.borderRadius,
        ...style,
      }}
    >
      {children}
    </div>
  );
};
