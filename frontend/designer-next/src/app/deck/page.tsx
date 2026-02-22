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

  // ── 2. INSPIRATION ──
  {
    bg: WHITE,
    render: () => (
      <SlideLayout bg={WHITE}>
        <div style={{ maxWidth: "900px", width: "100%", textAlign: "center" }}>
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
            The Inspiration
          </p>
          <h2
            style={{
              fontFamily: "var(--font-display), sans-serif",
              fontSize: "clamp(1.75rem, 3.5vw, 2.75rem)",
              fontWeight: 400,
              letterSpacing: "0.02em",
              lineHeight: 1.15,
              color: CHARCOAL,
              marginBottom: "2.5rem",
            }}
          >
            We saw the problem firsthand.
          </h2>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "3rem",
              marginBottom: "3rem",
            }}
          >
            {/* Family photo */}
            <div style={{ flexShrink: 0, textAlign: "center" }}>
              <img
                src="/family.jpg"
                alt="Danila with his parents"
                style={{
                  width: "220px",
                  height: "220px",
                  objectFit: "cover",
                  borderRadius: "1.25rem",
                  boxShadow: "0 20px 40px rgba(0,0,0,0.12)",
                }}
              />
              <div
                style={{
                  marginTop: "0.75rem",
                  fontSize: "0.75rem",
                  color: "rgba(46,46,56,0.4)",
                }}
              >
                Danila with his parents
              </div>
            </div>

            {/* Story */}
            <div style={{ maxWidth: "480px", textAlign: "left" }}>
              <svg
                viewBox="0 0 24 24"
                fill={VERMILLION}
                style={{ width: "32px", height: "32px", opacity: 0.3, marginBottom: "0.75rem" }}
              >
                <path d="M14.017 21v-7.391c0-5.704 3.731-9.57 8.983-10.609l.995 2.151c-2.432.917-3.995 3.638-3.995 5.849h4v10h-9.983zm-14.017 0v-7.391c0-5.704 3.748-9.57 9-10.609l.996 2.151c-2.433.917-3.996 3.638-3.996 5.849h3.983v10h-9.983z" />
              </svg>
              <p
                style={{
                  fontFamily: "var(--font-display), sans-serif",
                  fontSize: "1.25rem",
                  fontWeight: 400,
                  color: CHARCOAL,
                  lineHeight: 1.5,
                  marginBottom: "0.75rem",
                }}
              >
                My parents work in real estate.
              </p>
              <p
                style={{
                  fontSize: "1rem",
                  color: "rgba(46,46,56,0.55)",
                  lineHeight: 1.7,
                }}
              >
                I watched them spend hours staging apartments, coordinating movers, and
                juggling five different tools &mdash; just to furnish a single space. I knew AI
                could do this end-to-end.
              </p>
            </div>
          </div>

          {/* Validation row */}
          <div
            style={{
              display: "flex",
              gap: "1.5rem",
            }}
          >
            {/* BFL Hack Win */}
            <div
              style={{
                flex: 1,
                background: "rgba(236,230,219,0.25)",
                border: "1px solid rgba(236,230,219,0.5)",
                borderRadius: "1.25rem",
                padding: "1.5rem",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  fontSize: "1.75rem",
                  fontFamily: "var(--font-display), sans-serif",
                  color: VERMILLION,
                  marginBottom: "0.375rem",
                }}
              >
                HouseView
              </div>
              <div
                style={{
                  fontSize: "0.8125rem",
                  color: "rgba(46,46,56,0.5)",
                  lineHeight: 1.6,
                }}
              >
                Won the BFL Hack with an AI floorplan-to-3D pipeline &mdash; the precursor to
                Enso
              </div>
            </div>

            {/* Zillow */}
            <div
              style={{
                flex: 1,
                background: "rgba(236,230,219,0.25)",
                border: "1px solid rgba(236,230,219,0.5)",
                borderRadius: "1.25rem",
                padding: "1.5rem",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.625rem",
              }}
            >
              <svg
                viewBox="0 0 23.283 25.577"
                style={{ width: "28px", height: "28px" }}
              >
                <g fill="#006aff" fillRule="nonzero">
                  <path d="m15.743 6.897c.117-.026.169.013.24.091.403.448 1.691 2.021 2.041 2.45.065.078.02.163-.032.208-2.6 2.028-5.493 4.901-7.105 6.955-.032.046-.006.046.02.039 2.808-1.209 9.405-3.14 12.376-3.679v-3.763l-11.628-9.198-11.648 9.191v4.114c3.607-2.144 11.953-5.466 15.736-6.408z" />
                  <path d="m6.279 22.705c-.097.052-.176.039-.254-.039l-2.171-2.587c-.058-.072-.065-.111.013-.221 1.678-2.457 5.103-6.286 7.287-7.904.039-.026.026-.059-.02-.039-2.275.741-8.742 3.523-11.134 4.875v8.787h23.277v-8.462c-3.172.539-12.675 3.367-16.998 5.59z" />
                </g>
              </svg>
              <div
                style={{
                  fontSize: "0.8125rem",
                  color: "rgba(46,46,56,0.5)",
                  lineHeight: 1.5,
                  textAlign: "center",
                }}
              >
                In conversations with{" "}
                <span style={{ fontWeight: 600, color: CHARCOAL }}>Zillow</span> about
                AI-powered staging
              </div>
            </div>

            {/* Dwelly */}
            <div
              style={{
                flex: 1,
                background: "rgba(236,230,219,0.25)",
                border: "1px solid rgba(236,230,219,0.5)",
                borderRadius: "1.25rem",
                padding: "1.5rem",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.625rem",
              }}
            >
              <svg
                viewBox="0 0 383.09 323.88"
                style={{ width: "32px", height: "28px" }}
              >
                <defs>
                  <linearGradient id="dw1" x1="-47.79" y1="306.07" x2="228.38" y2="34.96" gradientUnits="userSpaceOnUse">
                    <stop offset="0" stopColor="#7aecc3" />
                    <stop offset=".5" stopColor="#efec53" />
                    <stop offset="1" stopColor="#92cef6" />
                  </linearGradient>
                  <linearGradient id="dw2" x1="29.94" y1="384.58" x2="305.34" y2="114.23" gradientUnits="userSpaceOnUse">
                    <stop offset="0" stopColor="#7aecc3" />
                    <stop offset=".5" stopColor="#efec53" />
                    <stop offset="1" stopColor="#92cef6" />
                  </linearGradient>
                </defs>
                <path fill="#2e2e38" d="M92.32,106.79c-.38,0-.69.12-.92.35-.24.24-.35.5-.35.78v139.32c0,.38.12.66.35.85.24.19.54.28.92.28h158.72c11.79,0,21.87-4.11,30.23-12.32,8.35-8.21,12.53-18.12,12.53-29.73v-57.34c0-11.61-4.18-21.54-12.53-29.8-8.36-8.26-18.43-12.39-30.23-12.39H92.32ZM258.82,145.16v64.99c0,2.08-.78,3.87-2.34,5.38-1.56,1.51-3.38,2.27-5.45,2.27h-124.88v-80.28h124.88c2.07,0,3.89.73,5.45,2.19,1.56,1.46,2.34,3.28,2.34,5.45Z" />
                <path fill="url(#dw1)" d="M35.52,145.48v-60.79L181.48,26s178.67,54.62,201.61,59.21L172.6,0S0,57.04,0,57.04c.02,3.51,0,56.71,0,56.71l35.52,31.73Z" />
                <path fill="url(#dw2)" d="M373.68,162.92h-20.46c-4.09,0-7.41,3.32-7.41,7.41v110.89c0,4.09-3.32,7.41-7.41,7.41H42.93c-4.09,0-7.41-3.32-7.41-7.41v-101.73L0,147.76v145.22c0,16.38,13.27,30.91,29.64,30.91h321.82c16.38,0,29.63-14.53,29.63-30.91v-122.65c0-4.09-3.32-7.41-7.41-7.41Z" />
              </svg>
              <div
                style={{
                  fontSize: "0.8125rem",
                  color: "rgba(46,46,56,0.5)",
                  lineHeight: 1.5,
                  textAlign: "center",
                }}
              >
                Exploring partnerships with{" "}
                <span style={{ fontWeight: 600, color: CHARCOAL }}>Dwelly</span> for
                AI-assisted lettings
              </div>
            </div>
          </div>
        </div>
      </SlideLayout>
    ),
  },

  // ── 3. PROBLEM (was 2) ──
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
            A team of specialized AI agents that orchestrate the entire journey &mdash; from
            understanding your style through natural conversation, to curating real furniture, to
            placing it in a 3D model of your space, to checkout.
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
            Multi-Agent Architecture
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
            Five agents, one pipeline
          </h2>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
              gap: "1.25rem",
            }}
          >
            {[
              {
                layer: "Consultation Agent",
                items: [
                  "ElevenLabs voice AI \u2014 interviews the user",
                  "Extracts style, budget & room preferences",
                  "Builds a structured design brief",
                ],
              },
              {
                layer: "Curation Agent",
                items: [
                  "Claude Opus 4.6 \u2014 generates a shopping list",
                  "Searches real IKEA catalogs in parallel",
                  "Scores & ranks matches against the brief",
                ],
              },
              {
                layer: "Spatial Agent",
                items: [
                  "Gemini 3.1 Pro \u2014 analyzes floorplan geometry",
                  "TRELLIS 2 via fal.ai \u2014 generates 3D room",
                  "Computes furniture placement coordinates",
                ],
              },
              {
                layer: "Rendering + Checkout",
                items: [
                  "React Three Fiber \u2014 interactive 3D scene",
                  "Stripe Agent Toolkit \u2014 one-click purchase",
                  "Supabase \u2014 durable session state",
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
