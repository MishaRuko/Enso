"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createSession } from "@/lib/backend";

const SPONSORS = [
  { name: "Anthropic", label: "Claude AI" },
  { name: "ElevenLabs", label: "Voice AI" },
  { name: "Stripe", label: "Payments" },
  { name: "Supabase", label: "Database" },
  { name: "Miro", label: "Collaboration" },
];

const FEATURES = [
  {
    icon: (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
      </svg>
    ),
    title: "Voice Consultation",
    desc: "Describe your dream room to our AI consultant",
  },
  {
    icon: (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="3" width="7" height="7" />
        <rect x="14" y="3" width="7" height="7" />
        <rect x="3" y="14" width="7" height="7" />
        <rect x="14" y="14" width="7" height="7" />
      </svg>
    ),
    title: "Smart Furniture Search",
    desc: "AI finds real products matching your style and budget",
  },
  {
    icon: (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
        <line x1="12" y1="22.08" x2="12" y2="12" />
      </svg>
    ),
    title: "3D Room Visualization",
    desc: "See furniture placed in your room in real-time 3D",
  },
  {
    icon: (
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
        <line x1="1" y1="10" x2="23" y2="10" />
      </svg>
    ),
    title: "One-Click Purchase",
    desc: "Buy everything through Stripe with a single click",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState<"design" | "consult" | null>(null);

  async function handleStart(mode: "design" | "consult") {
    setLoading(mode);
    try {
      const { session_id } = await createSession();
      if (mode === "consult") {
        router.push(`/consultation/${session_id}`);
      } else {
        router.push(`/session/${session_id}`);
      }
    } catch (err) {
      console.error("Failed to create session:", err);
      setLoading(null);
    }
  }

  return (
    <main
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        padding: "2rem",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Brand pill */}
      <div
        style={{
          fontFamily: "var(--font-display), sans-serif",
          fontSize: "20px",
          fontWeight: 400,
          letterSpacing: "0.06em",
          background: "#1a1a38",
          color: "#fff",
          padding: "12px 34px",
          borderRadius: "var(--radius-full)",
          marginBottom: "3rem",
          animation: "fadeUp 0.6s ease-out 0.2s both",
        }}
      >
        HomeDesigner
      </div>

      {/* Hero text */}
      <div
        style={{
          textAlign: "center",
          maxWidth: "640px",
          animation: "fadeUp 0.6s ease-out 0.4s both",
          position: "relative",
          zIndex: 1,
        }}
      >
        <h1
          style={{
            fontFamily: "var(--font-display), sans-serif",
            fontSize: "2.5rem",
            fontWeight: 400,
            letterSpacing: "0.02em",
            lineHeight: 1.2,
            marginBottom: "1.25rem",
            color: "#1a1a38",
          }}
        >
          Design Your Dream Room with AI
        </h1>
        <p
          style={{
            fontSize: "1.0625rem",
            color: "var(--text-secondary)",
            lineHeight: 1.75,
            maxWidth: "480px",
            margin: "0 auto",
            letterSpacing: "0.01em",
          }}
        >
          Voice-powered consultation, intelligent furniture search, 3D visualization, and one-click
          purchase — all driven by AI agents.
        </p>
      </div>

      {/* CTA buttons */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          flexWrap: "wrap",
          justifyContent: "center",
          marginTop: "2.5rem",
          animation: "fadeUp 0.6s ease-out 0.6s both",
          position: "relative",
          zIndex: 1,
        }}
      >
        <button
          onClick={() => handleStart("consult")}
          disabled={loading !== null}
          type="button"
          style={{
            background: "#1a1a38",
            color: "#fff",
            padding: "12px 32px",
            borderRadius: "var(--radius-full)",
            fontSize: "0.9375rem",
            fontWeight: 500,
            letterSpacing: "0.02em",
            transition: "all var(--transition-slow)",
            opacity: loading !== null ? 0.6 : 1,
            transform: loading === "consult" ? "scale(0.98)" : "scale(1)",
          }}
        >
          {loading === "consult" ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
              <span
                style={{
                  width: "14px",
                  height: "14px",
                  border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "#fff",
                  borderRadius: "50%",
                  animation: "spin 0.6s linear infinite",
                  display: "inline-block",
                }}
              />
              Creating...
            </span>
          ) : (
            "Start Voice Consultation"
          )}
        </button>

        <button
          onClick={() => handleStart("design")}
          disabled={loading !== null}
          type="button"
          style={{
            background: "rgba(255,255,255,0.7)",
            backdropFilter: "blur(8px)",
            color: "#1a1a38",
            padding: "12px 32px",
            borderRadius: "var(--radius-full)",
            fontSize: "0.9375rem",
            fontWeight: 500,
            letterSpacing: "0.02em",
            border: "1px solid rgba(26,26,56,0.1)",
            transition: "all var(--transition-slow)",
            opacity: loading !== null ? 0.6 : 1,
            transform: loading === "design" ? "scale(0.98)" : "scale(1)",
          }}
        >
          {loading === "design" ? (
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem" }}>
              <span
                style={{
                  width: "14px",
                  height: "14px",
                  border: "2px solid rgba(26,26,56,0.2)",
                  borderTopColor: "#1a1a38",
                  borderRadius: "50%",
                  animation: "spin 0.6s linear infinite",
                  display: "inline-block",
                }}
              />
              Creating...
            </span>
          ) : (
            "Skip to Design"
          )}
        </button>
      </div>

      {/* Feature cards — glassmorphism */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "1rem",
          maxWidth: "900px",
          width: "100%",
          marginTop: "4rem",
          animation: "fadeUp 0.6s ease-out 0.8s both",
          position: "relative",
          zIndex: 1,
        }}
      >
        {FEATURES.map((f, i) => (
          <div
            key={f.title}
            style={{
              padding: "1.5rem 1.25rem",
              borderRadius: "var(--radius-xl)",
              background: "rgba(255,255,255,0.95)",
              backdropFilter: "blur(20px)",
              boxShadow: "var(--shadow-lg)",
              transition: "all var(--transition-slow)",
              animation: `fadeUp 0.6s ease-out ${0.9 + i * 0.1}s both`,
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: "var(--radius-full)",
                background: "rgba(26,26,56,0.05)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#1a1a38",
                marginBottom: "0.875rem",
              }}
            >
              {f.icon}
            </div>
            <div
              style={{
                fontSize: "0.875rem",
                fontWeight: 600,
                marginBottom: "0.375rem",
                letterSpacing: "0.01em",
              }}
            >
              {f.title}
            </div>
            <div style={{ fontSize: "0.8125rem", color: "var(--muted)", lineHeight: 1.65 }}>
              {f.desc}
            </div>
          </div>
        ))}
      </div>

      {/* Sponsor badges */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "2rem",
          marginTop: "4rem",
          animation: "fadeUp 0.6s ease-out 1.4s both",
          position: "relative",
          zIndex: 1,
        }}
      >
        <span
          style={{
            fontSize: "0.6875rem",
            color: "var(--muted)",
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            fontWeight: 500,
          }}
        >
          Powered by
        </span>
        <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap", justifyContent: "center" }}>
          {SPONSORS.map((s) => (
            <div
              key={s.name}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "0.125rem",
              }}
            >
              <span
                style={{
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: "var(--text)",
                  opacity: 0.7,
                }}
              >
                {s.name}
              </span>
              <span style={{ fontSize: "0.6875rem", color: "var(--muted)" }}>{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Subtle tagline at bottom */}
      <div
        style={{
          position: "fixed",
          bottom: "32px",
          left: "50%",
          transform: "translateX(-50%)",
          fontSize: "0.6875rem",
          color: "var(--muted)",
          letterSpacing: "0.04em",
          animation: "fadeUp 0.6s ease-out 1.8s both",
        }}
      >
        HackEurope 2026 — Agentic AI Track
      </div>
    </main>
  );
}
