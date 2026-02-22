/**
 * Text-based voice intake component (demo/fallback mode).
 * Simple interface to test design brief collection without ElevenLabs realtime.
 * Uses the /voice_intake/turn endpoint.
 */

"use client";

import { useCallback, useState, useEffect } from "react";

interface TextIntakeProps {
  sessionId: string;
  onComplete?: (miroUrl: string) => void;
  onBriefUpdate?: (brief: any) => void;
  onStatusChange?: (status: "collecting" | "confirmed" | "finalized") => void;
}

interface BriefState {
  status: "collecting" | "confirmed" | "finalized";
  brief: Record<string, any>;
  missing_fields: string[];
  done: boolean;
  last_assistant_text: string;
}

export default function TextIntake({
  sessionId,
  onComplete,
  onBriefUpdate,
  onStatusChange,
}: TextIntakeProps) {
  const [state, setState] = useState<BriefState>({
    status: "collecting",
    brief: {},
    missing_fields: [],
    done: false,
    last_assistant_text: "Hello! Let's design your space. What rooms would you like to focus on?",
  });
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Initialize by fetching current session status
  useEffect(() => {
    const initSession = async () => {
      try {
        const res = await fetch(`/backend-session/${sessionId}`);
        if (res.ok) {
          const session = await res.json();
          setState((prev) => ({
            ...prev,
            status: session.status,
            brief: session.brief,
            missing_fields: session.missing_fields,
            done: session.status === "finalized",
          }));
          onStatusChange?.(session.status);
          onBriefUpdate?.(session.brief);
        }
      } catch (err) {
        console.error("Failed to init session:", err);
      }
    };
    initSession();
  }, [sessionId, onStatusChange, onBriefUpdate]);

  const handleSendMessage = useCallback(async () => {
    if (!userInput.trim()) return;

    setError(null);
    setLoading(true);

    try {
      // Show user message
      setTranscript((prev) => [...prev, `You: ${userInput}`]);

      // Send to backend
      const res = await fetch("/voice_intake/turn", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          user_text: userInput,
        }),
      });

      if (!res.ok) {
        throw new Error(`API error ${res.status}`);
      }

      const result = await res.json();
      const { assistant_text: assistantText, brief, missing_fields: missingFields, done } = result;

      // Update state
      setState({
        status: done ? "confirmed" : "collecting",
        brief,
        missing_fields: missingFields,
        done,
        last_assistant_text: assistantText,
      });

      // Show assistant response
      setTranscript((prev) => [...prev, `Agent: ${assistantText}`]);

      // Notify parent
      onBriefUpdate?.(brief);
      if (done) {
        onStatusChange?.("confirmed");
      }

      // Clear input
      setUserInput("");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      setTranscript((prev) => [...prev, `Error: ${msg}`]);
    } finally {
      setLoading(false);
    }
  }, [userInput, sessionId, onBriefUpdate, onStatusChange]);

  const handleFinalize = useCallback(async () => {
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/voice_intake/finalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (!res.ok) {
        throw new Error(`Failed to finalize: ${res.status}`);
      }

      const { miro_board_url: miroUrl } = await res.json();

      setState((prev) => ({
        ...prev,
        status: "finalized",
        done: true,
        last_assistant_text: `Perfect! Your design brief is ready. Here's your mood board: ${miroUrl}`,
      }));

      setTranscript((prev) => [
        ...prev,
        `Agent: Perfect! Your design brief is ready. Miro board: ${miroUrl}`,
      ]);

      onStatusChange?.("finalized");
      onComplete?.(miroUrl);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to finalize";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [sessionId, onStatusChange, onComplete]);

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        gap: "1rem",
        padding: "1rem",
      }}
    >
      {/* Transcript */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          padding: "1rem",
          background: "var(--surface)",
          fontFamily: "monospace",
          fontSize: "0.875rem",
          lineHeight: "1.5",
        }}
      >
        <div>Agent: {state.last_assistant_text}</div>
        {transcript.map((line, i) => (
          <div key={i} style={{ marginTop: "0.5rem" }}>
            {line}
          </div>
        ))}
      </div>

      {/* Status */}
      <div
        style={{
          display: "flex",
          gap: "1rem",
          alignItems: "center",
          fontSize: "0.875rem",
          color: "var(--muted)",
        }}
      >
        <span>
          Status: <strong>{state.status}</strong>
        </span>
        {state.missing_fields.length > 0 && (
          <span>
            Missing: <strong>{state.missing_fields.join(", ")}</strong>
          </span>
        )}
      </div>

      {/* Error */}
      {error && (
        <div
          style={{
            padding: "0.75rem",
            background: "var(--danger)",
            color: "white",
            borderRadius: "var(--radius-md)",
            fontSize: "0.875rem",
          }}
        >
          {error}
        </div>
      )}

      {/* Input */}
      {!state.done && (
        <div style={{ display: "flex", gap: "0.5rem" }}>
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleSendMessage();
            }}
            placeholder="Type your response..."
            disabled={loading}
            style={{
              flex: 1,
              padding: "0.5rem 0.75rem",
              border: "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              fontFamily: "inherit",
            }}
          />
          <button
            onClick={handleSendMessage}
            disabled={loading || !userInput.trim()}
            style={{
              padding: "0.5rem 1rem",
              background: "var(--accent)",
              color: "white",
              border: "none",
              borderRadius: "var(--radius-md)",
              cursor: "pointer",
              opacity: loading || !userInput.trim() ? 0.5 : 1,
            }}
          >
            Send
          </button>
        </div>
      )}

      {/* Finalize button */}
      {state.status === "confirmed" && !state.done && (
        <button
          onClick={handleFinalize}
          disabled={loading}
          style={{
            padding: "0.75rem 1rem",
            background: "var(--success)",
            color: "white",
            border: "none",
            borderRadius: "var(--radius-md)",
            cursor: "pointer",
            fontWeight: "bold",
            opacity: loading ? 0.5 : 1,
          }}
        >
          {loading ? "Finalizing..." : "Generate Miro Board"}
        </button>
      )}

      {/* Miro link if finalized */}
      {state.done && (
        <div
          style={{
            padding: "1rem",
            background: "var(--success)",
            color: "white",
            borderRadius: "var(--radius-md)",
            textAlign: "center",
          }}
        >
          <p style={{ margin: "0 0 0.5rem" }}>✓ Consultation Complete!</p>
          <a
            href={state.brief.miro_board_url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: "inherit",
              textDecoration: "underline",
            }}
          >
            View Miro Board →
          </a>
        </div>
      )}
    </div>
  );
}
