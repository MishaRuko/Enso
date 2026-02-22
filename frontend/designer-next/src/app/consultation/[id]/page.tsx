"use client";

import dynamic from "next/dynamic";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useState } from "react";

const VoiceAgent = dynamic(() => import("@/components/voice-agent"), { ssr: false });
import TextIntake from "@/components/text-intake";
import MoodBoard from "@/components/mood-board";
import MiroEmbed from "@/components/miro-embed";
import type { MoodBoardItem } from "@/components/mood-board";
import PreferenceTags from "@/components/preference-tags";
import { EnsoLogo } from "@/components/enso-logo";
import type { UserPreferences } from "@/lib/types";

const AGENT_ID = process.env.NEXT_PUBLIC_ELEVENLABS_AGENT_ID ?? "";

export default function ConsultationPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const sessionId = params.id;

  // Allow ?mode=text to use text intake instead of voice agent
  const textMode = searchParams.get("mode") === "text";
  const [moodItems, setMoodItems] = useState<MoodBoardItem[]>([]);
  const [preferences, setPreferences] = useState<Partial<UserPreferences>>({});
  const [saving, setSaving] = useState(false);
  const [_briefSummary, setBriefSummary] = useState<Record<string, any>>({});
  const [miroBoardUrl, setMiroBoardUrl] = useState<string | null>(null);

  const handleMoodBoardAdd = useCallback((item: MoodBoardItem) => {
    setMoodItems((prev) => [...prev, item]);
  }, []);

  const handlePreferenceUpdate = useCallback((key: string, value: unknown) => {
    setPreferences((prev) => {
      const arrayFields = [
        "colors",
        "lifestyle",
        "must_haves",
        "dealbreakers",
        "existing_furniture",
      ];
      if (arrayFields.includes(key) && typeof value === "string") {
        const current = (prev[key as keyof UserPreferences] as string[] | undefined) ?? [];
        return { ...prev, [key]: [...current, value] };
      }
      return { ...prev, [key]: value };
    });
  }, []);

  const handleRoomTypeSet = useCallback((type: string) => {
    setPreferences((prev) => ({ ...prev, room_type: type }));
  }, []);

  const handleBriefUpdate = useCallback((brief: Record<string, any>) => {
    setBriefSummary(brief);
  }, []);

  const handleMiroBoardCreated = useCallback((url: string, _boardId: string) => {
    setMiroBoardUrl(url);
  }, []);

  const handleIntakeComplete = useCallback(
    (_miroUrl: string) => {
      router.push(`/session/${sessionId}`);
    },
    [sessionId, router],
  );

  const handleComplete = useCallback(async () => {
    setSaving(true);
    try {
      await fetch(`/api/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          preferences,
          status: "consulting",
        }),
      });
      router.push(`/session/${sessionId}`);
    } catch (err) {
      console.error("Failed to save preferences:", err);
      setSaving(false);
    }
  }, [preferences, sessionId, router]);

  // In text mode, show full-width text intake; in voice mode, show two-column layout
  if (textMode) {
    return (
      <main
        style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}
      >
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
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: "var(--accent)",
                  }}
                />
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
              onBriefUpdate={handleBriefUpdate}
              onStatusChange={(status) => {
                if (status === "finalized") {
                  // Brief is being finalized, will navigate on completion
                }
              }}
            />
          </div>
        </section>
      </main>
    );
  }

  // Voice mode (default): two-column layout with VoiceAgent + Mood Board
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
      {/* Logo header spanning full width */}
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
            <span
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "var(--accent)",
              }}
            />
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
            Tell the AI about your dream room — style, budget, colors, and lifestyle.
          </p>
        </div>

        <div style={{ flex: 1, minHeight: 0 }}>
          <VoiceAgent
            agentId={AGENT_ID}
            sessionId={sessionId}
            onMoodBoardAdd={handleMoodBoardAdd}
            onPreferenceUpdate={handlePreferenceUpdate}
            onRoomTypeSet={handleRoomTypeSet}
            onMiroBoardCreated={handleMiroBoardCreated}
            onComplete={handleComplete}
          />
        </div>

        {/* Manual complete button */}
        <button
          onClick={handleComplete}
          disabled={saving}
          type="button"
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1.5rem",
            borderRadius: "var(--radius-md)",
            fontSize: "0.875rem",
            fontWeight: 600,
            background: "transparent",
            border: "1px solid var(--border)",
            color: "var(--muted)",
            transition: "all var(--transition-base)",
            opacity: saving ? 0.6 : 1,
            display: "inline-flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          {saving ? (
            <>
              <span
                style={{
                  width: "14px",
                  height: "14px",
                  border: "2px solid var(--border)",
                  borderTopColor: "var(--muted)",
                  borderRadius: "50%",
                  animation: "spin 0.6s linear infinite",
                  display: "inline-block",
                }}
              />
              Saving...
            </>
          ) : (
            <>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              >
                <polyline points="13 17 18 12 13 7" />
                <polyline points="6 17 11 12 6 7" />
              </svg>
              Skip to Design Phase
            </>
          )}
        </button>
      </section>

      {/* Right: Mood Board + Preferences */}
      <section
        style={{
          display: "flex",
          flexDirection: "column",
          padding: "1.5rem 2rem",
          overflowY: "auto",
          gap: "1.5rem",
          background: "var(--bg-elevated)",
          animation: "fadeIn 0.5s ease-out 0.2s both",
        }}
      >
        <div
          style={{ flex: miroBoardUrl ? 1 : undefined, minHeight: miroBoardUrl ? 0 : undefined }}
        >
          <div
            style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}
          >
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
              {miroBoardUrl ? "Vision Board" : "Mood Board"}
            </h2>
          </div>
          {miroBoardUrl ? (
            <MiroEmbed boardUrl={miroBoardUrl} height="100%" />
          ) : (
            <MoodBoard items={moodItems} />
          )}
        </div>

        <div
          style={{
            borderTop: "1px solid var(--border)",
            paddingTop: "1.5rem",
          }}
        >
          <div
            style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--accent)"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <line x1="4" y1="21" x2="4" y2="14" />
              <line x1="4" y1="10" x2="4" y2="3" />
              <line x1="12" y1="21" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12" y2="3" />
              <line x1="20" y1="21" x2="20" y2="16" />
              <line x1="20" y1="12" x2="20" y2="3" />
              <line x1="1" y1="14" x2="7" y2="14" />
              <line x1="9" y1="8" x2="15" y2="8" />
              <line x1="17" y1="16" x2="23" y2="16" />
            </svg>
            <h2 style={{ fontSize: "1rem", fontWeight: 700 }}>Collected Preferences</h2>
            {Object.keys(preferences).length > 0 && (
              <span
                style={{
                  fontSize: "0.6875rem",
                  fontWeight: 600,
                  padding: "0.125rem 0.5rem",
                  borderRadius: "var(--radius-full)",
                  background: "rgba(139,92,246,0.1)",
                  color: "var(--accent)",
                }}
              >
                {Object.keys(preferences).length}
              </span>
            )}
          </div>
          <PreferenceTags preferences={preferences} />
        </div>
      </section>
    </main>
  );
}
