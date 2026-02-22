"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect, useRef, useCallback, Suspense } from "react";
import { createSession } from "@/lib/backend";
import { EnsoLogo } from "@/components/enso-logo";
import { HeroScene } from "@/components/hero-scene";

/* ── Scroll-triggered fade-in wrapper ─────────────────────────── */

function FadeIn({
  children,
  delay = 0,
  style,
}: {
  children: React.ReactNode;
  delay?: number;
  style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          obs.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(24px)",
        transition: `opacity 0.9s cubic-bezier(0.4, 0, 0.2, 1) ${delay}s, transform 0.9s cubic-bezier(0.4, 0, 0.2, 1) ${delay}s`,
        ...style,
      }}
    >
      {children}
    </div>
  );
}

/* ── Data ─────────────────────────────────────────────────────── */

const STEPS = [
  {
    num: "01",
    label: "Describe",
    desc: "Tell our AI about your style, budget, and space through natural conversation.",
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
  },
  {
    num: "02",
    label: "Curate",
    desc: "AI searches real furniture catalogs to find pieces that match your vision perfectly.",
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
  },
  {
    num: "03",
    label: "Visualize",
    desc: "See every curated piece placed in your actual room layout in full 3D.",
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
  },
  {
    num: "04",
    label: "Purchase",
    desc: "Love what you see? Buy everything with a single click through Stripe checkout.",
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
        <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z" />
        <line x1="3" y1="6" x2="21" y2="6" />
        <path d="M16 10a4 4 0 0 1-8 0" />
      </svg>
    ),
  },
];

const FEATURES = [
  {
    icon: (
      <svg
        width="28"
        height="28"
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
    title: "Voice-First Design",
    desc: "No forms. No menus. Just talk. Our ElevenLabs-powered voice agent has a natural conversation about your style preferences, budget, and space constraints — then translates it into design intent.",
  },
  {
    icon: (
      <svg
        width="28"
        height="28"
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
    title: "Real Furniture, Real Prices",
    desc: "No generic renders. Enso searches real IKEA catalogs using Claude AI to curate actual products that match your taste, fit your dimensions, and stay within your budget.",
  },
  {
    icon: (
      <svg
        width="28"
        height="28"
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
    title: "True 3D Placement",
    desc: "Your floorplan becomes a 3D room via TRELLIS. Every piece of furniture gets its own 3D model, placed by AI in the optimal position — ready to explore from any angle.",
  },
];

const SPONSORS = ["Anthropic", "ElevenLabs", "Stripe", "Supabase", "Miro"];

/* ── Glass card shared styles ─────────────────────────────────── */

const CARD_PARCHMENT = {
  background: "rgba(236,230,219,0.25)",
  backdropFilter: "blur(20px)",
  WebkitBackdropFilter: "blur(20px)",
  border: "1px solid rgba(236,230,219,0.5)",
  boxShadow: "0 2px 24px rgba(26,26,56,0.03)",
  borderRadius: "var(--radius-xl)",
} as const;

/* ── Page ─────────────────────────────────────────────────────── */

export default function HomePage() {
  const router = useRouter();
  const [loading, setLoading] = useState<"design" | "consult" | null>(null);
  const [scrollY, setScrollY] = useState(0);
  const heroRef = useRef<HTMLElement>(null);

  const handleScroll = useCallback(() => {
    setScrollY(window.scrollY);
  }, []);

  useEffect(() => {
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  const heroHeight = typeof window !== "undefined" ? window.innerHeight : 900;
  const scrollProgress = Math.min(1, scrollY / heroHeight);

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
    <main style={{ position: "relative", overflow: "hidden" }}>
      {/* ─── HERO — Editorial layout with 3D ─── */}
      <section
        ref={heroRef}
        style={{
          minHeight: "100vh",
          display: "flex",
          position: "relative",
          background: "#db504a",
          overflow: "hidden",
        }}
      >
        {/* 3D scene behind everything */}
        <Suspense fallback={null}>
          <HeroScene scrollProgress={scrollProgress} />
        </Suspense>

        {/* Subtle gradient overlay for depth */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse at 30% 50%, rgba(219,80,74,0) 0%, rgba(160,42,38,0.5) 100%)",
            zIndex: 1,
            pointerEvents: "none",
          }}
        />

        {/* Left-aligned content column */}
        <div
          style={{
            position: "relative",
            zIndex: 2,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: "6rem clamp(2rem, 6vw, 6rem)",
            maxWidth: "640px",
            minHeight: "100vh",
          }}
        >
          {/* Enso mark */}
          <div
            style={{
              marginBottom: "2.5rem",
              animation: "fadeUp 1s cubic-bezier(0.4, 0, 0.2, 1) 0.1s both",
            }}
          >
            <EnsoLogo size={56} color="#1a1a38" animate />
          </div>

          {/* Tagline as hero headline */}
          <h1
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(2.5rem, 4.5vw, 3.75rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              lineHeight: 1.1,
              color: "#1a1a38",
              marginBottom: "1.5rem",
              animation: "fadeUp 1s cubic-bezier(0.4, 0, 0.2, 1) 0.3s both",
            }}
          >
            your space,
            <br />
            complete.
          </h1>

          {/* Description */}
          <p
            style={{
              fontSize: "1rem",
              color: "rgba(26,26,56,0.55)",
              lineHeight: 1.8,
              maxWidth: "400px",
              marginBottom: "2.5rem",
              animation: "fadeUp 1s cubic-bezier(0.4, 0, 0.2, 1) 0.55s both",
            }}
          >
            AI-powered interior design that goes from voice consultation to a fully furnished 3D
            room — in minutes, not weeks.
          </p>

          {/* CTA buttons */}
          <div
            style={{
              display: "flex",
              gap: "1rem",
              flexWrap: "wrap",
              animation: "fadeUp 1s cubic-bezier(0.4, 0, 0.2, 1) 0.75s both",
            }}
          >
            <button
              onClick={() => handleStart("consult")}
              disabled={loading !== null}
              type="button"
              style={{
                background: "#1a1a38",
                color: "#faf9f7",
                padding: "14px 36px",
                borderRadius: "100px",
                fontWeight: 600,
                fontSize: "0.9375rem",
                letterSpacing: "0.02em",
                border: "none",
                cursor: loading ? "not-allowed" : "pointer",
                transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
                opacity: loading !== null ? 0.7 : 1,
                boxShadow: "0 4px 24px rgba(26,26,56,0.25)",
              }}
            >
              {loading === "consult" ? "Creating..." : "Begin Consultation"}
            </button>
            <button
              onClick={() => handleStart("design")}
              disabled={loading !== null}
              type="button"
              style={{
                background: "rgba(26,26,56,0.06)",
                color: "#1a1a38",
                padding: "14px 36px",
                borderRadius: "100px",
                fontWeight: 500,
                fontSize: "0.9375rem",
                letterSpacing: "0.02em",
                border: "1px solid rgba(26,26,56,0.15)",
                cursor: loading ? "not-allowed" : "pointer",
                backdropFilter: "blur(8px)",
                transition: "all 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
                opacity: loading !== null ? 0.7 : 1,
              }}
            >
              {loading === "design" ? "Creating..." : "Upload Floorplan"}
            </button>
          </div>
          <a
            href="/deck"
            style={{
              marginTop: "1.25rem",
              fontSize: "0.75rem",
              color: "rgba(26,26,56,0.5)",
              textDecoration: "underline",
              textUnderlineOffset: "3px",
              letterSpacing: "0.04em",
              animation: "fadeUp 1s cubic-bezier(0.4, 0, 0.2, 1) 0.9s both",
            }}
          >
            deck
          </a>
        </div>

        {/* Scroll indicator — bottom-left */}
        <div
          style={{
            position: "absolute",
            bottom: "2.5rem",
            left: "clamp(2rem, 6vw, 6rem)",
            zIndex: 2,
            animation: "fadeUp 0.8s ease-out 2s both",
          }}
        >
          <div style={{ animation: "scrollBounce 2.5s ease-in-out infinite" }}>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="rgba(26,26,56,0.3)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>

        {/* Oversized ENSO — bottom-right, half-hidden by overflow */}
        <div
          style={{
            position: "absolute",
            bottom: "-0.22em",
            right: "clamp(-0.5rem, 1vw, 1rem)",
            zIndex: 3,
            fontFamily: "var(--font-display), sans-serif",
            fontSize: "clamp(12rem, 22vw, 26rem)",
            fontWeight: 400,
            letterSpacing: "0.05em",
            lineHeight: 0.82,
            color: "rgba(26,26,56,0.14)",
            userSelect: "none",
            pointerEvents: "none",
            whiteSpace: "nowrap",
            animation: "fadeUp 1.4s cubic-bezier(0.4, 0, 0.2, 1) 0.9s both",
          }}
        >
          ENSO
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section
        style={{
          position: "relative",
          zIndex: 1,
          padding: "7rem 2rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          background: "var(--bg)",
        }}
      >
        <FadeIn>
          <p
            style={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              color: "var(--accent)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              textAlign: "center",
              marginBottom: "0.75rem",
            }}
          >
            Process
          </p>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "2.25rem",
              fontWeight: 400,
              letterSpacing: "0.03em",
              color: "#1a1a38",
              marginBottom: "0.75rem",
              textAlign: "center",
            }}
          >
            From conversation to furnished room
          </h2>
          <p
            style={{
              fontSize: "0.9375rem",
              color: "var(--text-3)",
              textAlign: "center",
              marginBottom: "3.5rem",
            }}
          >
            Four steps. Zero complexity.
          </p>
        </FadeIn>

        <div
          style={{
            display: "flex",
            gap: "1.25rem",
            maxWidth: "940px",
            width: "100%",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {STEPS.map((step, i) => (
            <FadeIn
              key={step.num}
              delay={0.12 * i}
              style={{ flex: "1 1 190px", maxWidth: "220px" }}
            >
              <div
                className="card-hover"
                style={{
                  ...CARD_PARCHMENT,
                  padding: "2rem 1.25rem",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  textAlign: "center",
                  height: "100%",
                }}
              >
                <span
                  style={{
                    fontSize: "0.625rem",
                    fontWeight: 600,
                    color: "var(--accent)",
                    letterSpacing: "0.16em",
                    textTransform: "uppercase",
                    marginBottom: "1.25rem",
                  }}
                >
                  {step.num}
                </span>
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "50%",
                    background: "rgba(219,80,74,0.07)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#1a1a38",
                    marginBottom: "1.25rem",
                    transition: "all 0.4s ease",
                  }}
                >
                  {step.icon}
                </div>
                <div
                  style={{
                    fontSize: "0.9375rem",
                    fontWeight: 600,
                    color: "#1a1a38",
                    letterSpacing: "0.01em",
                    marginBottom: "0.625rem",
                  }}
                >
                  {step.label}
                </div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--text-3)",
                    lineHeight: 1.75,
                  }}
                >
                  {step.desc}
                </div>
              </div>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* ─── FEATURES ─── */}
      <section
        style={{
          position: "relative",
          zIndex: 1,
          padding: "6rem 2rem 7rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          background: "#1a2744",
        }}
      >
        <FadeIn>
          <p
            style={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              color: "rgba(255,255,255,0.5)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              textAlign: "center",
              marginBottom: "0.75rem",
            }}
          >
            Capabilities
          </p>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "2.25rem",
              fontWeight: 400,
              letterSpacing: "0.03em",
              color: "#db504a",
              marginBottom: "1rem",
              textAlign: "center",
            }}
          >
            What makes Enso different
          </h2>
          <p
            style={{
              fontSize: "1.0625rem",
              color: "rgba(255,255,255,0.75)",
              textAlign: "center",
              marginBottom: "1rem",
              maxWidth: "640px",
              lineHeight: 1.7,
            }}
          >
            The world&apos;s first independent AI interior designer. Enso handles homes, offices,
            and commercial spaces — from initial consultation through furniture curation, 3D
            visualization, and purchase logistics.
          </p>
          <p
            style={{
              fontSize: "0.9375rem",
              color: "rgba(255,255,255,0.45)",
              textAlign: "center",
              marginBottom: "3.5rem",
            }}
          >
            Not a mockup tool. A complete design agent that manages your move-in, end to end.
          </p>
        </FadeIn>

        <div
          style={{
            display: "flex",
            gap: "1.5rem",
            maxWidth: "960px",
            width: "100%",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {FEATURES.map((f, i) => (
            <FadeIn key={f.title} delay={0.12 * i} style={{ flex: "1 1 260px", maxWidth: "300px" }}>
              <div
                className="card-hover"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  backdropFilter: "blur(24px)",
                  WebkitBackdropFilter: "blur(24px)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  boxShadow: "0 4px 40px rgba(0,0,0,0.1)",
                  borderRadius: "var(--radius-xl)",
                  padding: "2.25rem 1.75rem",
                  height: "100%",
                }}
              >
                <div
                  style={{
                    width: "52px",
                    height: "52px",
                    borderRadius: "50%",
                    background: "rgba(255,255,255,0.08)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#db504a",
                    marginBottom: "1.5rem",
                  }}
                >
                  {f.icon}
                </div>
                <div
                  style={{
                    fontSize: "1rem",
                    fontWeight: 600,
                    color: "#db504a",
                    letterSpacing: "0.01em",
                    marginBottom: "0.75rem",
                  }}
                >
                  {f.title}
                </div>
                <div
                  style={{
                    fontSize: "0.8125rem",
                    color: "rgba(255,255,255,0.55)",
                    lineHeight: 1.85,
                  }}
                >
                  {f.desc}
                </div>
              </div>
            </FadeIn>
          ))}
        </div>
      </section>

      {/* ─── FINAL CTA ─── */}
      <section
        style={{
          position: "relative",
          zIndex: 1,
          padding: "4rem 2rem 0",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          background: "var(--bg)",
        }}
      >
        <FadeIn style={{ maxWidth: "480px", width: "100%" }}>
          <div
            style={{
              background: "rgba(236,230,219,0.3)",
              backdropFilter: "blur(24px)",
              WebkitBackdropFilter: "blur(24px)",
              border: "1px solid rgba(236,230,219,0.5)",
              boxShadow: "0 8px 60px rgba(26,26,56,0.04)",
              borderRadius: "2rem",
              padding: "3.5rem 3rem",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
            }}
          >
            <EnsoLogo size={36} color="#1a1a38" />
            <h3
              style={{
                fontFamily: "var(--font-display), sans-serif",
                fontSize: "1.625rem",
                fontWeight: 400,
                letterSpacing: "0.04em",
                color: "#1a1a38",
                margin: "1.5rem 0 0.75rem",
              }}
            >
              Ready to design your space?
            </h3>
            <p
              style={{
                fontSize: "0.875rem",
                color: "var(--text-3)",
                marginBottom: "2.25rem",
                lineHeight: 1.75,
              }}
            >
              Start with a voice consultation or upload your floorplan directly.
            </p>
            <div
              style={{
                display: "flex",
                gap: "0.875rem",
                flexWrap: "wrap",
                justifyContent: "center",
              }}
            >
              <button
                className="btn-primary"
                onClick={() => handleStart("consult")}
                disabled={loading !== null}
                type="button"
              >
                {loading === "consult" ? "Creating..." : "Get Started"}
              </button>
              <button
                className="btn-secondary"
                onClick={() => handleStart("design")}
                disabled={loading !== null}
                type="button"
              >
                {loading === "design" ? "Creating..." : "Upload Floorplan"}
              </button>
            </div>
          </div>
        </FadeIn>
      </section>

      {/* ─── CHARCOAL FOOTER ─── */}
      <footer
        style={{
          position: "relative",
          zIndex: 1,
          marginTop: "5rem",
          background: "#1a2744",
          padding: "3.5rem 2rem 2.5rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "2rem",
        }}
      >
        {/* Sponsors */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1.75rem",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          <span
            style={{
              fontSize: "0.625rem",
              color: "rgba(250,249,247,0.35)",
              textTransform: "uppercase",
              letterSpacing: "0.12em",
              fontWeight: 500,
            }}
          >
            Powered by
          </span>
          {SPONSORS.map((s) => (
            <span
              key={s}
              style={{
                fontSize: "0.75rem",
                fontWeight: 500,
                color: "rgba(250,249,247,0.55)",
                letterSpacing: "0.02em",
                transition: "color 0.3s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "rgba(250,249,247,0.9)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "rgba(250,249,247,0.55)";
              }}
            >
              {s}
            </span>
          ))}
        </div>

        {/* Divider */}
        <div style={{ width: "60px", height: "1px", background: "rgba(250,249,247,0.1)" }} />

        {/* Brand */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <EnsoLogo size={24} color="rgba(250,249,247,0.3)" />
          <span
            style={{
              fontSize: "0.625rem",
              color: "rgba(250,249,247,0.25)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            HackEurope 2026
          </span>
        </div>
      </footer>
    </main>
  );
}
