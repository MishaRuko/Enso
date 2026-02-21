"use client";

import Link from "next/link";
import { EnsoLogo } from "@/components/enso-logo";

const PHASES = [
  { key: "Upload", desc: "Upload floorplan" },
  { key: "Analyze", desc: "Analyzing layout" },
  { key: "Search", desc: "Curating furniture" },
  { key: "Source", desc: "Sourcing 3D models" },
  { key: "Place", desc: "Computing placement" },
  { key: "Done", desc: "Design complete" },
] as const;

interface StatusBarProps {
  currentPhase: string;
}

function phaseIndex(status: string): number {
  const map: Record<string, number> = {
    pending: 0,
    consulting: 0,
    analyzing_floorplan: 1,
    floorplan_ready: 1,
    floorplan_failed: 1,
    searching: 2,
    furniture_found: 2,
    searching_failed: 2,
    sourcing: 3,
    sourcing_failed: 3,
    placing: 4,
    placing_failed: 4,
    placement_ready: 4,
    placement_failed: 4,
    complete: 5,
  };
  return map[status.toLowerCase()] ?? 0;
}

function isFailed(status: string): boolean {
  return status.endsWith("_failed");
}

function isProcessing(status: string): boolean {
  return ["analyzing_floorplan", "searching", "sourcing", "placing", "placing_furniture"].includes(
    status,
  );
}

export function StatusBar({ currentPhase }: StatusBarProps) {
  const activeIdx = phaseIndex(currentPhase);
  const failed = isFailed(currentPhase);
  const processing = isProcessing(currentPhase);
  const progressPercent = Math.min(100, (activeIdx / (PHASES.length - 1)) * 100);

  return (
    <div
      style={{
        background: "rgba(250,249,247,0.95)",
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        borderBottom: "1px solid var(--border)",
        padding: "0",
        position: "relative",
      }}
    >
      {/* Progress bar track */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: "2px",
          background: "var(--border)",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${progressPercent}%`,
            background: failed ? "var(--error)" : "var(--accent)",
            transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        />
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.125rem",
          padding: "0.5rem 1rem",
        }}
      >
        {/* Enso brand mark + wordmark */}
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.375rem",
            marginRight: "1.5rem",
            textDecoration: "none",
          }}
        >
          <EnsoLogo size={20} color="#1a1a38" />
          <span
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontWeight: 400,
              fontSize: "0.875rem",
              color: "#1a1a38",
              letterSpacing: "0.04em",
            }}
          >
            enso
          </span>
        </Link>

        {PHASES.map((phase, i) => {
          const isActive = i === activeIdx;
          const isDone = i < activeIdx;
          const isError = isActive && failed;
          const isInProgress = isActive && processing;

          return (
            <div key={phase.key} style={{ display: "flex", alignItems: "center" }}>
              {i > 0 && (
                <div
                  style={{
                    width: "1.5rem",
                    height: "1px",
                    background: isDone ? "var(--sage)" : isError ? "var(--error)" : "var(--border)",
                    margin: "0 0.125rem",
                    transition: "background var(--transition-slow)",
                  }}
                />
              )}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.375rem",
                  padding: "0.25rem 0.75rem",
                  borderRadius: "var(--radius-full)",
                  fontSize: "0.75rem",
                  fontWeight: 500,
                  letterSpacing: "0.02em",
                  transition: "all var(--transition-base)",
                  background: isError
                    ? "var(--error-subtle)"
                    : isActive
                      ? "#1a1a38"
                      : isDone
                        ? "rgba(124,140,110,0.1)"
                        : "transparent",
                  color: isError
                    ? "var(--error)"
                    : isActive
                      ? "#faf9f7"
                      : isDone
                        ? "var(--sage)"
                        : "var(--text-3)",
                  border: `1px solid ${
                    isError
                      ? "var(--error)"
                      : isActive
                        ? "#1a1a38"
                        : isDone
                          ? "rgba(124,140,110,0.2)"
                          : "var(--border)"
                  }`,
                  animation: isInProgress ? "pulseGlow 2s ease-in-out infinite" : "none",
                }}
              >
                {isDone && (
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                  >
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                )}
                {isError && (
                  <svg
                    width="12"
                    height="12"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                  >
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                )}
                {isInProgress && (
                  <span
                    style={{
                      width: "10px",
                      height: "10px",
                      border: "1.5px solid rgba(255,255,255,0.3)",
                      borderTopColor: "#fff",
                      borderRadius: "50%",
                      animation: "spin 0.7s linear infinite",
                      display: "inline-block",
                    }}
                  />
                )}
                {phase.key}
              </div>
            </div>
          );
        })}

        {/* Phase description */}
        <div
          style={{
            marginLeft: "auto",
            fontSize: "0.75rem",
            color: failed ? "var(--error)" : "var(--muted)",
            fontStyle: "italic",
            letterSpacing: "0.02em",
            animation: processing ? "progressPulse 2s ease-in-out infinite" : "none",
          }}
        >
          {PHASES[activeIdx]?.desc}
        </div>
      </div>
    </div>
  );
}
