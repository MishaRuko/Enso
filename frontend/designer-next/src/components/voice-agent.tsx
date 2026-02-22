"use client";

import { useConversation } from "@elevenlabs/react";
import { useCallback, useRef, useState } from "react";

interface VoiceAgentProps {
  agentId: string;
  sessionId: string;
  onComplete: () => void;
}

export default function VoiceAgent({ agentId, sessionId, onComplete }: VoiceAgentProps) {
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  // Ref so handleStop always reads the latest transcript (no stale closure).
  const transcriptRef = useRef<string[]>([]);

  const conversation = useConversation({
    onConnect: () => {
      setError(null);
      const line = "[Connected to AI consultant]";
      setTranscript((prev) => [...prev, line]);
      transcriptRef.current = [...transcriptRef.current, line];
    },
    onDisconnect: () => {
      const line = "[Consultation ended]";
      setTranscript((prev) => [...prev, line]);
      transcriptRef.current = [...transcriptRef.current, line];
    },
    onError: (message: string) => setError(message),
    onMessage: (props: { message: string; role: "user" | "agent" }) => {
      const prefix = props.role === "user" ? "You" : "AI";
      const line = `${prefix}: ${props.message}`;
      setTranscript((prev) => [...prev, line]);
      transcriptRef.current = [...transcriptRef.current, line];
    },
  });

  const handleStart = useCallback(async () => {
    setError(null);
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      await conversation.startSession({ agentId, connectionType: "webrtc" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start conversation");
    }
  }, [agentId, conversation]);

  const handleStop = useCallback(async () => {
    try {
      await conversation.endSession();
    } catch {
      // ignore
    }
    setSaving(true);
    try {
      await fetch(`/api/sessions/${sessionId}/extract-preferences`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: transcriptRef.current }),
      });
    } catch {
      // navigate even if extraction fails
    }
    setSaving(false);
    onComplete();
  }, [conversation, sessionId, onComplete]);

  const isConnected = conversation.status === "connected";
  const isSpeaking = conversation.isSpeaking;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", height: "100%" }}>
      {/* Status */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          padding: "0.5rem 0.75rem",
          borderRadius: "var(--radius-md)",
          background: "var(--surface)",
          border: "1px solid var(--border)",
        }}
      >
        <div
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: saving
              ? "var(--accent)"
              : isConnected
                ? isSpeaking
                  ? "var(--accent)"
                  : "var(--success)"
                : "var(--muted)",
            boxShadow:
              isConnected && !saving
                ? `0 0 8px ${isSpeaking ? "var(--accent-glow)" : "var(--success-glow)"}`
                : saving
                  ? "0 0 8px var(--accent-glow)"
                  : "none",
            transition: "all var(--transition-slow)",
            animation: saving ? "progressPulse 1s ease-in-out infinite" : "none",
          }}
        />
        <span style={{ fontSize: "0.8125rem", color: "var(--muted)", flex: 1 }}>
          {saving && "Analysing conversation…"}
          {!saving && !isConnected && "Ready to connect"}
          {!saving && isConnected && isSpeaking && "AI is speaking…"}
          {!saving && isConnected && !isSpeaking && "Listening…"}
        </span>
        {isConnected && !saving && (
          <div
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: "var(--success)",
              animation: "progressPulse 2s ease-in-out infinite",
            }}
          />
        )}
      </div>

      {/* Waveform */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100px",
          borderRadius: "var(--radius-lg)",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        {isConnected && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: isSpeaking
                ? "radial-gradient(ellipse at center, rgba(59,130,246,0.06), transparent)"
                : "radial-gradient(ellipse at center, rgba(34,197,94,0.04), transparent)",
              transition: "background var(--transition-slow)",
            }}
          />
        )}
        {isConnected ? (
          <div style={{ display: "flex", alignItems: "center", gap: "3px", height: "70px", position: "relative" }}>
            {Array.from({ length: 32 }).map((_, i) => (
              <div
                key={i}
                style={{
                  width: "2.5px",
                  borderRadius: "var(--radius-full)",
                  background: isSpeaking
                    ? "linear-gradient(to top, var(--accent), var(--gradient-mid))"
                    : "var(--success)",
                  animation: `waveBar 0.8s ease-in-out ${i * 0.04}s infinite alternate`,
                  height: isSpeaking ? "100%" : "30%",
                  transition: "height var(--transition-slow)",
                  opacity: 0.6 + (i % 3) * 0.15,
                }}
              />
            ))}
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.5rem" }}>
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--muted)"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ opacity: 0.6 }}
            >
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
            <span style={{ fontSize: "0.75rem", color: "var(--muted)", opacity: 0.6 }}>
              Click below to start
            </span>
          </div>
        )}
      </div>

      {/* Start / End button */}
      <button
        onClick={isConnected ? handleStop : handleStart}
        disabled={saving}
        type="button"
        style={{
          padding: "0.875rem 1.5rem",
          borderRadius: "var(--radius-md)",
          fontSize: "1rem",
          fontWeight: 600,
          background: saving
            ? "var(--surface)"
            : isConnected
              ? "var(--error)"
              : "linear-gradient(135deg, var(--accent), var(--gradient-mid))",
          color: saving ? "var(--muted)" : "#fff",
          border: saving ? "1px solid var(--border)" : "none",
          transition: "all var(--transition-base)",
          boxShadow: !saving && !isConnected ? "var(--shadow-glow)" : "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.5rem",
          opacity: saving ? 0.8 : 1,
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
            Analysing conversation…
          </>
        ) : isConnected ? (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="1" />
            </svg>
            End Consultation
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            </svg>
            Start Voice Consultation
          </>
        )}
      </button>

      {error && (
        <div
          style={{
            padding: "0.75rem 1rem",
            borderRadius: "var(--radius-md)",
            background: "var(--error-subtle)",
            border: "1px solid rgba(239,68,68,0.2)",
            color: "var(--error)",
            fontSize: "0.8125rem",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}

      {/* Transcript */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          overflowY: "auto",
          borderRadius: "var(--radius-lg)",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          padding: "1rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
        }}
      >
        <span
          style={{
            fontSize: "0.6875rem",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            color: "var(--muted)",
            marginBottom: "0.25rem",
            display: "flex",
            alignItems: "center",
            gap: "0.375rem",
          }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Transcript
        </span>
        {transcript.length === 0 ? (
          <span style={{ color: "var(--muted)", fontSize: "0.8125rem", fontStyle: "italic" }}>
            Start the consultation to see the transcript here…
          </span>
        ) : (
          transcript.map((line, i) => (
            <p
              key={`t-${i}`}
              style={{
                fontSize: "0.8125rem",
                color: line.startsWith("You:") ? "var(--text)" : line.startsWith("[") ? "var(--muted)" : "#93c5fd",
                margin: 0,
                lineHeight: 1.5,
                padding: "0.25rem 0",
                animation: "fadeIn 0.3s ease-out",
                borderBottom: i < transcript.length - 1 ? "1px solid rgba(255,255,255,0.03)" : "none",
              }}
            >
              {line.startsWith("You:") && (
                <span style={{ fontWeight: 600, color: "var(--accent)", marginRight: "0.375rem" }}>You:</span>
              )}
              {line.startsWith("AI:") && (
                <span style={{ fontWeight: 600, color: "#93c5fd", marginRight: "0.375rem" }}>AI:</span>
              )}
              {line.startsWith("You:") || line.startsWith("AI:")
                ? line.substring(line.indexOf(":") + 2)
                : line}
            </p>
          ))
        )}
      </div>
    </div>
  );
}
