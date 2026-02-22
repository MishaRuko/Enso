"use client";

import { useState, useEffect, useCallback } from "react";
import { EnsoLogo } from "@/components/enso-logo";

const NAVY = "#1a2744";
const VERMILLION = "#db504a";
const WHITE = "#faf9f7";
const CHARCOAL = "#2e2e38";

interface Slide {
  bg: string;
  render: () => React.ReactNode;
}

function SlideLayout({ children, bg }: { children: React.ReactNode; bg: string }) {
  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        background: bg,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "4rem clamp(2rem, 8vw, 8rem)",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

const SLIDES: Slide[] = [
  // ── 1. TITLE ──
  {
    bg: VERMILLION,
    render: () => (
      <SlideLayout bg={VERMILLION}>
        <div
          style={{
            position: "absolute",
            bottom: "-0.22em",
            right: "clamp(-0.5rem, 1vw, 1rem)",
            fontFamily: "var(--font-display), sans-serif",
            fontSize: "clamp(10rem, 20vw, 24rem)",
            fontWeight: 400,
            letterSpacing: "0.05em",
            lineHeight: 0.82,
            color: "rgba(26,26,56,0.1)",
            userSelect: "none",
            pointerEvents: "none",
            whiteSpace: "nowrap",
          }}
        >
          ENSO
        </div>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-start",
            maxWidth: "720px",
            width: "100%",
            zIndex: 1,
          }}
        >
          <EnsoLogo size={72} color={CHARCOAL} />
          <h1
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(3rem, 6vw, 5rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              lineHeight: 1.1,
              color: CHARCOAL,
              margin: "2rem 0 1.5rem",
            }}
          >
            your space,
            <br />
            complete.
          </h1>
          <p
            style={{
              fontSize: "1.25rem",
              color: "rgba(26,26,56,0.55)",
              lineHeight: 1.6,
              maxWidth: "480px",
            }}
          >
            The world&apos;s first independent AI interior designer.
          </p>
          <div
            style={{
              marginTop: "3rem",
              fontSize: "0.75rem",
              color: "rgba(26,26,56,0.35)",
              letterSpacing: "0.12em",
              textTransform: "uppercase",
              fontWeight: 500,
            }}
          >
            HackEurope 2026 &middot; Paris CentraleSup&eacute;lec
          </div>
        </div>
      </SlideLayout>
    ),
  },

  // ── 2. PROBLEM ──
  {
    bg: WHITE,
    render: () => (
      <SlideLayout bg={WHITE}>
        <div
          style={{
            maxWidth: "780px",
            width: "100%",
          }}
        >
          <p
            style={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              color: VERMILLION,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              marginBottom: "1.5rem",
            }}
          >
            The Problem
          </p>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(2rem, 4vw, 3.5rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              lineHeight: 1.15,
              color: CHARCOAL,
              marginBottom: "2.5rem",
            }}
          >
            Interior design is broken.
          </h2>
          <div
            style={{
              display: "flex",
              gap: "2rem",
              flexWrap: "wrap",
            }}
          >
            {[
              {
                stat: "8-12 weeks",
                label: "Average timeline for a single room redesign",
              },
              {
                stat: "$2,000+",
                label: "Minimum cost for a professional consultation",
              },
              {
                stat: "5+ tools",
                label: "Mood boards, floor planners, stores, carts, movers \u2014 all separate",
              },
            ].map((item) => (
              <div key={item.stat} style={{ flex: "1 1 200px" }}>
                <div
                  style={{
                    fontSize: "clamp(2rem, 3.5vw, 3rem)",
                    fontFamily: "var(--font-display), sans-serif",
                    color: VERMILLION,
                    marginBottom: "0.5rem",
                  }}
                >
                  {item.stat}
                </div>
                <div
                  style={{
                    fontSize: "0.9375rem",
                    color: "rgba(26,26,56,0.5)",
                    lineHeight: 1.6,
                  }}
                >
                  {item.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </SlideLayout>
    ),
  },

  // ── 3. SOLUTION ──
  {
    bg: NAVY,
    render: () => (
      <SlideLayout bg={NAVY}>
        <div style={{ maxWidth: "780px", width: "100%" }}>
          <p
            style={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              color: "rgba(255,255,255,0.4)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              marginBottom: "1.5rem",
            }}
          >
            Our Solution
          </p>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(2rem, 4vw, 3.5rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              lineHeight: 1.15,
              color: VERMILLION,
              marginBottom: "2rem",
            }}
          >
            Enso is your AI interior designer.
          </h2>
          <p
            style={{
              fontSize: "1.125rem",
              color: "rgba(255,255,255,0.7)",
              lineHeight: 1.7,
              maxWidth: "600px",
              marginBottom: "3rem",
            }}
          >
            One agent that handles the entire journey — from understanding your style through
            natural conversation, to curating real furniture, to placing it in a 3D model of your
            space, to checkout.
          </p>
          <div
            style={{
              display: "flex",
              gap: "1.5rem",
              flexWrap: "wrap",
            }}
          >
            {["Homes", "Offices", "Commercial Spaces", "Move-in Logistics"].map((tag) => (
              <span
                key={tag}
                style={{
                  padding: "0.625rem 1.25rem",
                  borderRadius: "100px",
                  background: "rgba(255,255,255,0.08)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "rgba(255,255,255,0.8)",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  letterSpacing: "0.02em",
                }}
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </SlideLayout>
    ),
  },

  // ── 4. HOW IT WORKS ──
  {
    bg: WHITE,
    render: () => (
      <SlideLayout bg={WHITE}>
        <div style={{ maxWidth: "900px", width: "100%" }}>
          <p
            style={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              color: VERMILLION,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              marginBottom: "1rem",
              textAlign: "center",
            }}
          >
            How It Works
          </p>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(1.75rem, 3vw, 2.5rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              color: CHARCOAL,
              textAlign: "center",
              marginBottom: "3.5rem",
            }}
          >
            Four steps. Zero complexity.
          </h2>
          <div
            style={{
              display: "flex",
              gap: "1.5rem",
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            {[
              {
                num: "01",
                title: "Describe",
                desc: "Voice conversation with our ElevenLabs AI agent about your style, budget, and space",
              },
              {
                num: "02",
                title: "Curate",
                desc: "Claude AI searches real IKEA catalogs to find furniture that matches your vision",
              },
              {
                num: "03",
                title: "Visualize",
                desc: "Your floorplan becomes a 3D room with furniture placed by Gemini spatial AI",
              },
              {
                num: "04",
                title: "Purchase",
                desc: "Buy everything with a single click through Stripe checkout",
              },
            ].map((step) => (
              <div
                key={step.num}
                style={{
                  flex: "1 1 180px",
                  maxWidth: "200px",
                  background: "rgba(236,230,219,0.25)",
                  backdropFilter: "blur(20px)",
                  border: "1px solid rgba(236,230,219,0.5)",
                  borderRadius: "1.75rem",
                  padding: "2rem 1.25rem",
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    fontSize: "0.625rem",
                    fontWeight: 600,
                    color: VERMILLION,
                    letterSpacing: "0.16em",
                    textTransform: "uppercase",
                    marginBottom: "1rem",
                  }}
                >
                  {step.num}
                </div>
                <div
                  style={{
                    fontSize: "1rem",
                    fontWeight: 600,
                    color: CHARCOAL,
                    marginBottom: "0.625rem",
                  }}
                >
                  {step.title}
                </div>
                <div
                  style={{
                    fontSize: "0.75rem",
                    color: "rgba(26,26,56,0.4)",
                    lineHeight: 1.7,
                  }}
                >
                  {step.desc}
                </div>
              </div>
            ))}
          </div>
        </div>
      </SlideLayout>
    ),
  },

  // ── 5. ARCHITECTURE ──
  {
    bg: NAVY,
    render: () => (
      <SlideLayout bg={NAVY}>
        <div style={{ maxWidth: "900px", width: "100%" }}>
          <p
            style={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              color: "rgba(255,255,255,0.4)",
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              marginBottom: "1rem",
              textAlign: "center",
            }}
          >
            Architecture
          </p>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(1.75rem, 3vw, 2.5rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              color: VERMILLION,
              textAlign: "center",
              marginBottom: "3rem",
            }}
          >
            Built with the best
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
              gap: "1.25rem",
            }}
          >
            {[
              {
                layer: "Intelligence",
                items: [
                  "Claude Opus 4.6 \u2014 planning & reasoning",
                  "Gemini 3.1 Pro \u2014 floorplan analysis & spatial placement",
                  "ElevenLabs \u2014 voice consultation agent",
                ],
              },
              {
                layer: "3D Pipeline",
                items: [
                  "TRELLIS 2 via fal.ai \u2014 3D room generation",
                  "Hunyuan3D v2 \u2014 furniture model fallback",
                  "React Three Fiber \u2014 interactive 3D viewer",
                ],
              },
              {
                layer: "Platform",
                items: [
                  "Next.js 15 + React 19 \u2014 frontend",
                  "FastAPI + Python 3.12 \u2014 backend",
                  "Supabase \u2014 database & auth",
                  "Stripe \u2014 payments",
                ],
              },
            ].map((col) => (
              <div
                key={col.layer}
                style={{
                  background: "rgba(255,255,255,0.05)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "1.25rem",
                  padding: "1.75rem 1.5rem",
                }}
              >
                <div
                  style={{
                    fontSize: "0.6875rem",
                    fontWeight: 600,
                    color: VERMILLION,
                    letterSpacing: "0.12em",
                    textTransform: "uppercase",
                    marginBottom: "1.25rem",
                  }}
                >
                  {col.layer}
                </div>
                <ul
                  style={{
                    listStyle: "none",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.75rem",
                  }}
                >
                  {col.items.map((item) => (
                    <li
                      key={item}
                      style={{
                        fontSize: "0.8125rem",
                        color: "rgba(255,255,255,0.6)",
                        lineHeight: 1.5,
                        paddingLeft: "1rem",
                        position: "relative",
                      }}
                    >
                      <span
                        style={{
                          position: "absolute",
                          left: 0,
                          color: "rgba(255,255,255,0.2)",
                        }}
                      >
                        &bull;
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </SlideLayout>
    ),
  },

  // ── 6. DEMO ──
  {
    bg: VERMILLION,
    render: () => (
      <SlideLayout bg={VERMILLION}>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
          }}
        >
          <EnsoLogo size={80} color={CHARCOAL} />
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(2.5rem, 5vw, 4.5rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              lineHeight: 1.1,
              color: CHARCOAL,
              margin: "2rem 0 1.5rem",
            }}
          >
            Live Demo
          </h2>
          <p
            style={{
              fontSize: "1.125rem",
              color: "rgba(26,26,56,0.5)",
              maxWidth: "400px",
              lineHeight: 1.6,
            }}
          >
            From voice consultation to a furnished 3D room — in real time.
          </p>
        </div>
      </SlideLayout>
    ),
  },

  // ── 7. CHALLENGES ──
  {
    bg: WHITE,
    render: () => (
      <SlideLayout bg={WHITE}>
        <div style={{ maxWidth: "960px", width: "100%" }}>
          <p
            style={{
              fontSize: "0.6875rem",
              fontWeight: 600,
              color: VERMILLION,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              marginBottom: "0.75rem",
              textAlign: "center",
            }}
          >
            Challenges We&apos;re Targeting
          </p>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(1.5rem, 2.5vw, 2.25rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              color: CHARCOAL,
              textAlign: "center",
              marginBottom: "2rem",
            }}
          >
            11 tracks, 1 product
          </h2>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "center",
              gap: "0.75rem",
            }}
          >
            {[
              { name: "Agentic AI Track", tag: "Primary" },
              { name: "Best Use of Claude", tag: "Anthropic" },
              { name: "Best Use of Gemini", tag: "Google" },
              { name: "Best Use of ElevenLabs", tag: "ElevenLabs" },
              { name: "Best Stripe Integration", tag: "Stripe" },
              { name: "Best use of Paid", tag: "Paid" },
              { name: "Autonomous Consulting Agent", tag: "Wavestone" },
              { name: "Best Adaptable Agent", tag: "Scaleway" },
              { name: "Best Use of Lovable", tag: "Lovable" },
              { name: "Best Use of Fibro AI", tag: "Fibro" },
              { name: "Best Team Under 22", tag: "al.Patch" },
            ].map((c) => (
              <div
                key={c.name}
                style={{
                  width: "220px",
                  background: "rgba(236,230,219,0.2)",
                  border: "1px solid rgba(236,230,219,0.5)",
                  borderRadius: "1rem",
                  padding: "1rem 1rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.625rem",
                }}
              >
                <span
                  style={{
                    fontSize: "0.5rem",
                    fontWeight: 600,
                    color: VERMILLION,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    background: "rgba(219,80,74,0.08)",
                    padding: "0.2rem 0.4rem",
                    borderRadius: "100px",
                    whiteSpace: "nowrap",
                    flexShrink: 0,
                  }}
                >
                  {c.tag}
                </span>
                <span
                  style={{
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    color: CHARCOAL,
                    lineHeight: 1.3,
                  }}
                >
                  {c.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </SlideLayout>
    ),
  },

  // ── 8. THANK YOU ──
  {
    bg: NAVY,
    render: () => (
      <SlideLayout bg={NAVY}>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
          }}
        >
          <EnsoLogo size={64} color={VERMILLION} />
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(2.5rem, 5vw, 4rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              lineHeight: 1.1,
              color: WHITE,
              margin: "2rem 0 1rem",
            }}
          >
            Thank you.
          </h2>
          <p
            style={{
              fontSize: "1.125rem",
              color: "rgba(255,255,255,0.5)",
              marginBottom: "3rem",
              lineHeight: 1.6,
            }}
          >
            your space, complete.
          </p>
          <div
            style={{
              display: "flex",
              gap: "2rem",
              flexWrap: "wrap",
              justifyContent: "center",
            }}
          >
            <div
              style={{
                padding: "0.875rem 2rem",
                borderRadius: "100px",
                background: VERMILLION,
                color: WHITE,
                fontSize: "0.9375rem",
                fontWeight: 500,
                letterSpacing: "0.02em",
              }}
            >
              enso.design
            </div>
          </div>
          <div
            style={{
              marginTop: "4rem",
              fontSize: "0.6875rem",
              color: "rgba(255,255,255,0.25)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            HackEurope 2026 &middot; Team Enso
          </div>
        </div>
      </SlideLayout>
    ),
  },
];

export default function DeckPage() {
  const [current, setCurrent] = useState(0);
  const [transitioning, setTransitioning] = useState(false);

  const goTo = useCallback(
    (index: number) => {
      if (index < 0 || index >= SLIDES.length || transitioning) return;
      setTransitioning(true);
      setCurrent(index);
      setTimeout(() => setTransitioning(false), 400);
    },
    [transitioning],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        goTo(current + 1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        goTo(current - 1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [current, goTo]);

  // Touch swipe
  useEffect(() => {
    let startX = 0;
    function onTouchStart(e: TouchEvent) {
      startX = e.touches[0].clientX;
    }
    function onTouchEnd(e: TouchEvent) {
      const dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 60) {
        goTo(current + (dx < 0 ? 1 : -1));
      }
    }
    window.addEventListener("touchstart", onTouchStart);
    window.addEventListener("touchend", onTouchEnd);
    return () => {
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchend", onTouchEnd);
    };
  }, [current, goTo]);

  const slide = SLIDES[current];

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
        position: "relative",
        cursor: "none",
      }}
    >
      {/* Logo home link */}
      <a
        href="/"
        style={{
          position: "fixed",
          top: "1.5rem",
          left: "1.5rem",
          zIndex: 100,
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          textDecoration: "none",
          cursor: "pointer",
        }}
      >
        <EnsoLogo
          size={28}
          color={slide.bg === NAVY || slide.bg === CHARCOAL ? "rgba(255,255,255,0.7)" : CHARCOAL}
        />
        <span
          style={{
            fontFamily: "var(--font-display), sans-serif",
            fontSize: "1.125rem",
            fontWeight: 400,
            letterSpacing: "0.04em",
            color: slide.bg === NAVY || slide.bg === CHARCOAL ? "rgba(255,255,255,0.7)" : CHARCOAL,
          }}
        >
          enso
        </span>
      </a>

      {/* Slide content */}
      <div
        key={current}
        style={{
          animation: "fadeInScale 0.4s cubic-bezier(0.4, 0, 0.2, 1) both",
        }}
      >
        {slide.render()}
      </div>

      {/* Navigation dots */}
      <div
        style={{
          position: "fixed",
          bottom: "2rem",
          left: "50%",
          transform: "translateX(-50%)",
          display: "flex",
          gap: "0.5rem",
          zIndex: 100,
        }}
      >
        {SLIDES.map((_, i) => (
          <button
            key={`dot-${i}`}
            onClick={() => goTo(i)}
            type="button"
            style={{
              width: i === current ? "24px" : "8px",
              height: "8px",
              borderRadius: "100px",
              border: "none",
              background:
                slide.bg === NAVY || slide.bg === CHARCOAL
                  ? i === current
                    ? "rgba(255,255,255,0.9)"
                    : "rgba(255,255,255,0.2)"
                  : i === current
                    ? VERMILLION
                    : "rgba(26,26,56,0.15)",
              cursor: "pointer",
              transition: "all 0.3s ease",
              padding: 0,
            }}
            aria-label={`Go to slide ${i + 1}`}
          />
        ))}
      </div>

      {/* Slide counter */}
      <div
        style={{
          position: "fixed",
          bottom: "2rem",
          right: "2rem",
          fontSize: "0.6875rem",
          letterSpacing: "0.08em",
          color:
            slide.bg === NAVY || slide.bg === CHARCOAL
              ? "rgba(255,255,255,0.3)"
              : "rgba(26,26,56,0.3)",
          zIndex: 100,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {current + 1} / {SLIDES.length}
      </div>

      {/* Click zones for navigation */}
      <div
        onClick={() => goTo(current - 1)}
        onKeyDown={() => {}}
        role="button"
        tabIndex={-1}
        aria-label="Previous slide"
        style={{
          position: "fixed",
          left: 0,
          top: 0,
          width: "20%",
          height: "100%",
          cursor: current > 0 ? "w-resize" : "default",
          zIndex: 50,
        }}
      />
      <div
        onClick={() => goTo(current + 1)}
        onKeyDown={() => {}}
        role="button"
        tabIndex={-1}
        aria-label="Next slide"
        style={{
          position: "fixed",
          right: 0,
          top: 0,
          width: "20%",
          height: "100%",
          cursor: current < SLIDES.length - 1 ? "e-resize" : "default",
          zIndex: 50,
        }}
      />
    </div>
  );
}
