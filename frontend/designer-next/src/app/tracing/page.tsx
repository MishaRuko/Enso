"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { listSessions, cancelSession, toggleDemo } from "@/lib/backend";
import type { DesignSession } from "@/lib/types";

const PROCESSING_STATUSES = new Set([
  "analyzing_floorplan",
  "searching",
  "sourcing",
  "placing",
  "placing_furniture",
]);

function isProcessing(status: string): boolean {
  return PROCESSING_STATUSES.has(status);
}

function badgeStyle(status: string): React.CSSProperties {
  if (status === "complete" || status === "placement_ready")
    return { background: "#1b5e20", color: "#a5d6a7" };
  if (status.endsWith("_failed")) return { background: "#b71c1c", color: "#ef9a9a" };
  if (isProcessing(status))
    return { background: "#e65100", color: "#ffcc80", animation: "pulse 1.5s infinite" };
  if (status === "floorplan_ready" || status === "furniture_found")
    return { background: "#0d47a1", color: "#90caf9" };
  return { background: "var(--bg-muted)", color: "var(--text-3)" };
}

function formatTime(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString();
}

function statusLabel(status: string): string {
  return status.replace(/_/g, " ");
}

export default function TracingPage() {
  const router = useRouter();
  const [sessions, setSessions] = useState<DesignSession[]>([]);
  const [loading, setLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const sessionsRef = useRef<DesignSession[]>([]);

  const demoCount = sessions.filter((s) => s.demo_selected).length;

  async function handleToggleDemo(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      const { demo_selected } = await toggleDemo(id);
      setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, demo_selected } : s)));
    } catch {
      // ignore
    }
  }

  function handleDemo() {
    router.push("/tracing/demo");
  }

  async function fetchSessions() {
    try {
      const list = await listSessions();
      setSessions(list);
      sessionsRef.current = list;
    } catch {
      // API unavailable
    } finally {
      setLoading(false);
    }
  }

  // biome-ignore lint/correctness/useExhaustiveDependencies: one-time mount
  useEffect(() => {
    fetchSessions();
    intervalRef.current = setInterval(() => {
      if (sessionsRef.current.some((s) => isProcessing(s.status))) fetchSessions();
    }, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  async function handleCancel(sessionId: string, e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    try {
      await cancelSession(sessionId);
    } catch {
      /* ignore */
    }
    fetchSessions();
  }

  return (
    <div style={styles.page}>
      <div style={styles.headerRow}>
        <h2 style={styles.heading}>Pipeline Traces</h2>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          {demoCount > 0 && (
            <button
              type="button"
              className="btn-primary"
              onClick={handleDemo}
              style={{ padding: "0.5rem 1.25rem", fontSize: "0.8125rem" }}
            >
              Demo {demoCount} selected
            </button>
          )}
          <Link href="/" style={styles.homeLink}>
            Home
          </Link>
        </div>
      </div>

      {loading && <div style={styles.empty}>Loading...</div>}
      {!loading && sessions.length === 0 && (
        <div style={styles.empty}>
          No sessions yet.{" "}
          <Link href="/" style={styles.link}>
            Create one.
          </Link>
        </div>
      )}

      {!loading && sessions.length > 0 && (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={{ ...styles.th, width: 50, textAlign: "center" }}>Demo</th>
              {["Session ID", "Client", "Created", "Status", "Floorplan", "Furniture", ""].map(
                (h) => (
                  <th key={h} style={styles.th}>
                    {h}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr
                key={s.id}
                style={{
                  ...styles.row,
                  background: s.demo_selected ? "var(--accent-subtle)" : undefined,
                }}
                onClick={() => window.location.assign(`/tracing/${s.id}`)}
              >
                <td style={{ ...styles.td, textAlign: "center", width: 50 }}>
                  <input
                    type="checkbox"
                    checked={!!s.demo_selected}
                    onChange={(e) => handleToggleDemo(s.id, e as unknown as React.MouseEvent)}
                    onClick={(e) => e.stopPropagation()}
                    style={{ cursor: "pointer", accentColor: "var(--accent)" }}
                  />
                </td>
                <td style={{ ...styles.td, fontFamily: "monospace", fontSize: "0.82rem" }}>
                  {s.id}
                </td>
                <td style={{ ...styles.td, color: "var(--text-3)", fontSize: "0.82rem" }}>
                  {s.client_name || "-"}
                </td>
                <td style={styles.td}>{formatTime(s.created_at)}</td>
                <td style={styles.td}>
                  <span style={{ ...styles.badge, ...badgeStyle(s.status) }}>
                    {statusLabel(s.status)}
                  </span>
                </td>
                <td style={styles.td}>
                  {s.floorplan_url ? (
                    <img
                      src={s.floorplan_url}
                      alt="Floorplan"
                      style={styles.thumbImg}
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <span style={{ color: "var(--text-4)" }}>-</span>
                  )}
                </td>
                <td style={{ ...styles.td, fontSize: "0.82rem" }}>
                  {s.furniture_list?.length || 0} items
                </td>
                <td style={styles.td}>
                  {isProcessing(s.status) && (
                    <button
                      type="button"
                      style={styles.cancelBtn}
                      onClick={(e) => handleCancel(s.id, e)}
                    >
                      Stop
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const styles = {
  page: { padding: 24, maxWidth: 1100, margin: "0 auto", width: "100%" } as React.CSSProperties,
  headerRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 20,
  } as React.CSSProperties,
  heading: {
    fontFamily: "var(--font-display), sans-serif",
    color: "var(--text)",
    fontSize: "1.4rem",
    fontWeight: 400,
  } as React.CSSProperties,
  homeLink: {
    color: "var(--text-3)",
    fontSize: "0.85rem",
  } as React.CSSProperties,
  empty: {
    color: "var(--text-3)",
    padding: 40,
    textAlign: "center",
  } as React.CSSProperties,
  link: { color: "var(--accent)", fontWeight: 600 } as React.CSSProperties,
  table: { width: "100%", borderCollapse: "collapse" } as React.CSSProperties,
  th: {
    textAlign: "left",
    padding: "10px 12px",
    color: "var(--text-3)",
    borderBottom: "1px solid var(--border)",
    fontSize: "0.8rem",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  } as React.CSSProperties,
  td: {
    padding: "10px 12px",
    borderBottom: "1px solid var(--bg-subtle)",
    color: "var(--text)",
    fontSize: "0.85rem",
    verticalAlign: "middle",
  } as React.CSSProperties,
  row: { cursor: "pointer", transition: "background 0.15s" } as React.CSSProperties,
  badge: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 12,
    fontSize: "0.78rem",
    textTransform: "capitalize",
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  cancelBtn: {
    background: "#b71c1c",
    color: "#ef9a9a",
    border: "none",
    borderRadius: 4,
    padding: "3px 10px",
    fontSize: "0.78rem",
    cursor: "pointer",
  } as React.CSSProperties,
  thumbImg: {
    width: 48,
    height: 48,
    objectFit: "cover",
    borderRadius: 4,
    border: "1px solid var(--border)",
  } as React.CSSProperties,
} as const;
