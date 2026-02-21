"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect, useRef } from "react";
import { createSession } from "@/lib/backend";
import { EnsoLogo } from "@/components/enso-logo";

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
      { threshold: 0.15 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(20px)",
        transition: `opacity 0.7s ease-out ${delay}s, transform 0.7s ease-out ${delay}s`,
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

/* ── Glass card shared style ─────────────────────────────────── */

const GLASS = {
  background: "rgba(255,255,255,0.4)",
  backdropFilter: "blur(20px)",
  WebkitBackdropFilter: "blur(20px)",
  border: "1px solid rgba(255,255,255,0.5)",
  boxShadow: "0 4px 40px rgba(26,26,56,0.04), inset 0 1px 0 rgba(255,255,255,0.6)",
  borderRadius: "var(--radius-xl)",
} as const;

const GLASS_HERO = {
  background: "rgba(255,255,255,0.45)",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  border: "1px solid rgba(255,255,255,0.6)",
  boxShadow: "0 8px 60px rgba(26,26,56,0.06), inset 0 1px 0 rgba(255,255,255,0.8)",
  borderRadius: "2rem",
} as const;

/* ── Page ─────────────────────────────────────────────────────── */

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
    <main style={{ position: "relative", overflow: "hidden" }}>
      {/* ─── Global decorative gradient blobs ─── */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0 }}>
        <div
          style={{
            position: "absolute",
            top: "-20%",
            right: "-10%",
            width: "700px",
            height: "700px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(219,80,74,0.08), transparent 70%)",
            filter: "blur(60px)",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: "-15%",
            left: "-10%",
            width: "600px",
            height: "600px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(26,26,56,0.05), transparent 70%)",
            filter: "blur(80px)",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "55%",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(26,26,56,0.04), transparent 70%)",
            filter: "blur(50px)",
          }}
        />
      </div>

      {/* ─── HERO ─── */}
      <section
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          zIndex: 1,
          padding: "2rem",
        }}
      >
        {/* Enso mark */}
        <div
          style={{
            marginBottom: "1.5rem",
            color: "#1a1a38",
            animation: "fadeUp 0.8s ease-out 0.1s both",
          }}
        >
          <EnsoLogo size={100} animate />
        </div>

        {/* Wordmark */}
        <h1
          style={{
            fontFamily: "var(--font-display), sans-serif",
            fontSize: "4rem",
            fontWeight: 400,
            letterSpacing: "0.08em",
            color: "#1a1a38",
            marginBottom: "0.75rem",
            animation: "fadeUp 0.8s ease-out 0.3s both",
          }}
        >
          Enso
        </h1>

        {/* Tagline */}
        <p
          style={{
            fontSize: "1.25rem",
            color: "var(--text-secondary)",
            letterSpacing: "0.04em",
            marginBottom: "1.5rem",
            animation: "fadeUp 0.8s ease-out 0.5s both",
          }}
        >
          your space, complete.
        </p>

        {/* Description */}
        <p
          style={{
            fontSize: "1rem",
            color: "var(--muted)",
            lineHeight: 1.8,
            textAlign: "center",
            maxWidth: "460px",
            marginBottom: "2.5rem",
            animation: "fadeUp 0.8s ease-out 0.7s both",
          }}
        >
          AI-powered interior design that goes from voice consultation to a fully
          furnished 3D room — in minutes, not weeks.
        </p>

        {/* CTA buttons */}
        <div
          style={{
            display: "flex",
            gap: "1rem",
            flexWrap: "wrap",
            justifyContent: "center",
            animation: "fadeUp 0.8s ease-out 0.9s both",
          }}
        >
          <button
            className="btn-primary"
            onClick={() => handleStart("consult")}
            disabled={loading !== null}
            type="button"
          >
            {loading === "consult" ? "Creating..." : "Begin Consultation"}
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

        {/* Scroll indicator */}
        <div
          style={{
            position: "absolute",
            bottom: "2rem",
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
            animation: "fadeUp 0.6s ease-out 1.5s both",
          }}
        >
          <div style={{ animation: "scrollBounce 2s ease-in-out infinite" }}>
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="rgba(26,26,56,0.3)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─── */}
      <section
        style={{
          position: "relative",
          zIndex: 1,
          padding: "6rem 2rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <FadeIn>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "2rem",
              fontWeight: 400,
              letterSpacing: "0.04em",
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
              color: "var(--muted)",
              textAlign: "center",
              marginBottom: "3rem",
            }}
          >
            Four steps. Zero complexity.
          </p>
        </FadeIn>

        <div
          style={{
            display: "flex",
            gap: "1.25rem",
            maxWidth: "920px",
            width: "100%",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          {STEPS.map((step, i) => (
            <FadeIn
              key={step.num}
              delay={0.1 * i}
              style={{ flex: "1 1 180px", maxWidth: "220px" }}
            >
              <div
                style={{
                  ...GLASS,
                  padding: "1.75rem 1.25rem",
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
                    color: "#db504a",
                    letterSpacing: "0.15em",
                    textTransform: "uppercase",
                    marginBottom: "1rem",
                  }}
                >
                  {step.num}
                </span>
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "var(--radius-full)",
                    background: "rgba(219,80,74,0.06)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#1a1a38",
                    marginBottom: "1rem",
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
                    marginBottom: "0.5rem",
                  }}
                >
                  {step.label}
                </div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "var(--muted)",
                    lineHeight: 1.7,
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
          padding: "4rem 2rem 6rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <FadeIn>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "2rem",
              fontWeight: 400,
              letterSpacing: "0.04em",
              color: "#1a1a38",
              marginBottom: "0.75rem",
              textAlign: "center",
            }}
          >
            What makes Enso different
          </h2>
          <p
            style={{
              fontSize: "0.9375rem",
              color: "var(--muted)",
              textAlign: "center",
              marginBottom: "3rem",
            }}
          >
            Not a mockup tool. A complete design agent.
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
          {FEATURES.map((f, i) => {
            const iconBg = [
              "rgba(219,80,74,0.08)",
              "rgba(219,80,74,0.06)",
              "rgba(26,26,56,0.05)",
            ][i % 3];
            return (
            <FadeIn
              key={f.title}
              delay={0.1 * i}
              style={{ flex: "1 1 260px", maxWidth: "300px" }}
            >
              <div
                className="card-hover"
                style={{
                  ...GLASS,
                  padding: "2rem 1.5rem",
                  height: "100%",
                }}
              >
                <div
                  style={{
                    width: "48px",
                    height: "48px",
                    borderRadius: "var(--radius-full)",
                    background: iconBg,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#1a1a38",
                    marginBottom: "1.25rem",
                  }}
                >
                  {f.icon}
                </div>
                <div
                  style={{
                    fontSize: "1rem",
                    fontWeight: 600,
                    color: "#1a1a38",
                    letterSpacing: "0.01em",
                    marginBottom: "0.625rem",
                  }}
                >
                  {f.title}
                </div>
                <div
                  style={{
                    fontSize: "0.8125rem",
                    color: "var(--muted)",
                    lineHeight: 1.8,
                  }}
                >
                  {f.desc}
                </div>
              </div>
            </FadeIn>
            );
          })}
        </div>
      </section>

      {/* ─── FINAL CTA + FOOTER ─── */}
      <section
        style={{
          position: "relative",
          zIndex: 1,
          padding: "4rem 2rem 3rem",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <FadeIn style={{ maxWidth: "500px", width: "100%" }}>
          <div
            style={{
              ...GLASS_HERO,
              padding: "3rem 4rem",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
            }}
          >
            <EnsoLogo size={40} color="#1a1a38" />
            <h3
              style={{
                fontFamily: "var(--font-display), sans-serif",
                fontSize: "1.5rem",
                fontWeight: 400,
                letterSpacing: "0.04em",
                color: "#1a1a38",
                margin: "1.25rem 0 0.75rem",
              }}
            >
              Ready to design your space?
            </h3>
            <p
              style={{
                fontSize: "0.875rem",
                color: "var(--muted)",
                marginBottom: "2rem",
                lineHeight: 1.7,
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

        {/* Sponsors */}
        <FadeIn delay={0.2}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "1.5rem",
              marginTop: "4rem",
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontSize: "0.625rem",
                color: "var(--muted)",
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                fontWeight: 500,
              }}
            >
              Powered by
            </span>
            {SPONSORS.map((s) => (
              <span
                key={s}
                className="sponsor-badge"
                style={{
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  color: "#1a1a38",
                  letterSpacing: "0.01em",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </FadeIn>

        {/* Footer */}
        <div
          style={{
            marginTop: "3rem",
            marginBottom: "1rem",
            fontSize: "0.625rem",
            color: "var(--muted)",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          HackEurope 2026
        </div>
      </section>
    </main>
  );
}
