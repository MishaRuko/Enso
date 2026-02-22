"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const VoiceAgent = dynamic(() => import("@/components/voice-agent"), { ssr: false });
import TextIntake from "@/components/text-intake";
import MiroEmbed from "@/components/miro-embed";
import { EnsoLogo } from "@/components/enso-logo";

const AGENT_ID = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID ?? "";

export default function ConsultationPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = params.id;

  const textMode = searchParams.get("mode") === "text";
  const [miroBoardUrl, setMiroBoardUrl] = useState<string | null>(null);

  // Poll for miro_board_url while on the consultation page (e.g. during text intake).
  useEffect(() => {
    if (miroBoardUrl) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/sessions/${sessionId}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.miro_board_url) {
          setMiroBoardUrl(data.miro_board_url as string);
          clearInterval(interval);
        }
      } catch {
        // ignore
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [sessionId, miroBoardUrl]);

  const handleNavigate = useCallback(() => {
    router.push(`/session/${sessionId}`);
  }, [sessionId, router]);

  const handleIntakeComplete = useCallback(
    (_miroUrl: string) => {
      router.push(`/session/${sessionId}`);
    },
    [sessionId, router],
  );

  const Logo = (
    <a
      href="/"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.5rem",
        padding: "1rem 2rem",
        textDecoration: "none",
        flexShrink: 0,
      }}
    >
      <EnsoLogo size={24} color="var(--text)" />
      <span
        style={{
          fontFamily: "var(--font-display), sans-serif",
          fontSize: "1rem",
          fontWeight: 400,
          letterSpacing: "0.04em",
          color: "var(--text)",
        }}
      >
        enso
      </span>
    </a>
  );

  if (textMode) {
    return (
      <main style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
        {Logo}
        <section style={{ flex: 1, overflow: "auto", padding: "0 2rem 1.5rem" }}>
          <div style={{ maxWidth: "800px", margin: "0 auto" }}>
            <div style={{ marginBottom: "2rem" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  padding: "0.25rem 0.75rem",
                  borderRadius: "var(--radius-full)",
                  background: "var(--accent-subtle)",
                  border: "1px solid rgba(59,130,246,0.2)",
                  fontSize: "0.6875rem",
                  fontWeight: 600,
                  color: "var(--accent)",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                  marginBottom: "0.75rem",
                }}
              >
                <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--accent)" }} />
                Text Consultation
              </div>
              <h1
                style={{
                  fontSize: "1.75rem",
                  fontWeight: 800,
                  letterSpacing: "-0.02em",
                  marginBottom: "0.375rem",
                  background: "linear-gradient(135deg, var(--text), var(--text-secondary))",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}
              >
                Design Consultation
              </h1>
              <p style={{ fontSize: "0.875rem", color: "var(--muted)", lineHeight: 1.5 }}>
                Type naturally about your dream room — style, budget, colors, and lifestyle.
              </p>
            </div>
            <TextIntake
              sessionId={sessionId}
              onComplete={handleIntakeComplete}
              onBriefUpdate={() => {}}
              onStatusChange={() => {}}
            />
          </div>
        </section>
      </main>
    );
  }

  // Voice mode: two-column layout
  return (
    <main
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gridTemplateRows: "auto 1fr",
        height: "100vh",
        overflow: "hidden",
      }}
    >
      {/* Logo header */}
      <a
        href="/"
        style={{
          gridColumn: "1 / -1",
          display: "flex",
          alignItems: "center",
          gap: "0.5rem",
          padding: "1rem 2rem",
          textDecoration: "none",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <EnsoLogo size={24} color="var(--text)" />
        <span
          style={{
            fontFamily: "var(--font-display), sans-serif",
            fontSize: "1rem",
            fontWeight: 400,
            letterSpacing: "0.04em",
            color: "var(--text)",
          }}
        >
          enso
        </span>
      </a>

      {/* Left: Voice Agent */}
      <section
        style={{
          display: "flex",
          flexDirection: "column",
          padding: "1.5rem 2rem",
          borderRight: "1px solid var(--border)",
          overflow: "hidden",
          animation: "fadeIn 0.5s ease-out",
        }}
      >
        <div style={{ marginBottom: "1.5rem" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.25rem 0.75rem",
              borderRadius: "var(--radius-full)",
              background: "var(--accent-subtle)",
              border: "1px solid rgba(219,80,74,0.15)",
              fontSize: "0.6875rem",
              fontWeight: 600,
              color: "var(--accent)",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
              marginBottom: "0.75rem",
            }}
          >
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--accent)" }} />
            Voice Consultation
          </div>
          <h1
            style={{
              fontSize: "1.75rem",
              fontWeight: 800,
              letterSpacing: "-0.02em",
              marginBottom: "0.375rem",
              background: "linear-gradient(135deg, var(--text), var(--text-secondary))",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              backgroundClip: "text",
            }}
          >
            Design Consultation
          </h1>
          <p style={{ fontSize: "0.875rem", color: "var(--muted)", lineHeight: 1.5 }}>
            Tell the AI about your dream room. When you're done, click End Consultation — we'll extract your preferences and generate your vision board automatically.
          </p>
        </div>

        <div style={{ flex: 1, minHeight: 0 }}>
          <VoiceAgent
            agentId={AGENT_ID}
            sessionId={sessionId}
            onComplete={handleNavigate}
          />
        </div>
      </section>

      {/* Right: Vision Board */}
      <section
        style={{
          display: "flex",
          flexDirection: "column",
          background: "var(--bg-elevated)",
          animation: "fadeIn 0.5s ease-out 0.2s both",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            padding: "1.5rem 2rem",
            overflow: "hidden",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.875rem" }}>
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--accent)"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <h2 style={{ fontSize: "1rem", fontWeight: 700 }}>
              {miroBoardUrl ? "Vision Board" : "Your Vision Board"}
            </h2>
          </div>

          <div style={{ flex: 1, minHeight: 0 }}>
            {miroBoardUrl ? (
              <MiroEmbed boardUrl={miroBoardUrl} height="100%" />
            ) : (
              <div
                style={{
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "1rem",
                  borderRadius: "var(--radius-lg)",
                  border: "1px dashed var(--border)",
                  color: "var(--muted)",
                  textAlign: "center",
                  padding: "2rem",
                }}
              >
                <svg
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1"
                  strokeLinecap="round"
                  style={{ opacity: 0.3 }}
                >
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                <div>
                  <p style={{ fontSize: "0.875rem", fontWeight: 500, marginBottom: "0.375rem" }}>
                    Your vision board will appear here
                  </p>
                  <p style={{ fontSize: "0.8125rem", opacity: 0.7 }}>
                    Generated automatically when you end the consultation
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}
