"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listDemoSessions } from "@/lib/backend";
import type { DesignSession } from "@/lib/types";

function badgeStyle(status: string): React.CSSProperties {
  if (status === "complete" || status === "placement_ready")
    return { background: "#1b5e20", color: "#a5d6a7" };
  if (status.endsWith("_failed")) return { background: "#b71c1c", color: "#ef9a9a" };
  return { background: "var(--bg-muted)", color: "var(--text-3)" };
}

export default function DemoPage() {
  const [sessions, setSessions] = useState<DesignSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeIdx, setActiveIdx] = useState(0);

  useEffect(() => {
    listDemoSessions()
      .then(setSessions)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={styles.center}>
        <p style={{ color: "var(--muted)", animation: "progressPulse 2s ease-in-out infinite" }}>
          Loading sessions...
        </p>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div style={styles.center}>
        <p style={{ color: "var(--muted)" }}>No demo sessions selected.</p>
        <Link href="/tracing" style={{ color: "var(--accent)", marginTop: "1rem" }}>
          Select sessions in traces
        </Link>
      </div>
    );
  }

  const current = sessions[activeIdx];

  return (
    <div style={styles.page}>
      <div style={styles.headerRow}>
        <h2 style={styles.heading}>Demo View</h2>
        <Link href="/tracing" style={styles.backLink}>
          Back to traces
        </Link>
      </div>

      {/* Session tabs */}
      {sessions.length > 1 && (
        <div style={styles.tabs}>
          {sessions.map((s, i) => (
            <button
              key={s.id}
              type="button"
              onClick={() => setActiveIdx(i)}
              style={{
                ...styles.tab,
                background: i === activeIdx ? "var(--accent)" : "var(--bg)",
                color: i === activeIdx ? "#fff" : "var(--text-2)",
                borderColor: i === activeIdx ? "var(--accent)" : "var(--border)",
              }}
            >
              {s.client_name || s.id.slice(0, 8)}
            </button>
          ))}
        </div>
      )}

      {current && (
        <div style={{ animation: "fadeUp 0.4s ease-out" }}>
          <div style={styles.card}>
            <div style={styles.cardHeader}>
              <div>
                <span
                  style={{ fontFamily: "monospace", fontSize: "0.82rem", color: "var(--text-3)" }}
                >
                  {current.id}
                </span>
                {current.client_name && (
                  <span style={{ marginLeft: "0.75rem", fontWeight: 600 }}>
                    {current.client_name}
                  </span>
                )}
              </div>
              <span style={{ ...styles.badge, ...badgeStyle(current.status) }}>
                {current.status.replace(/_/g, " ")}
              </span>
            </div>

            <div style={styles.grid}>
              <div style={styles.section}>
                <p style={styles.label}>Floorplan</p>
                {current.floorplan_url ? (
                  <img src={current.floorplan_url} alt="Floorplan" style={styles.thumb} />
                ) : (
                  <p style={styles.muted}>Not uploaded</p>
                )}
              </div>

              <div style={styles.section}>
                <p style={styles.label}>Room</p>
                {current.room_data?.rooms?.length ? (
                  <div>
                    {current.room_data.rooms.map((r, i) => (
                      <p
                        key={`${r.name}-${i}`}
                        style={{ fontSize: "0.875rem", marginBottom: "0.25rem" }}
                      >
                        {r.name} — {r.width_m}m × {r.length_m}m ({r.area_sqm}m²)
                      </p>
                    ))}
                  </div>
                ) : (
                  <p style={styles.muted}>Not analyzed</p>
                )}
              </div>

              <div style={styles.section}>
                <p style={styles.label}>Furniture</p>
                <p style={{ fontSize: "0.875rem" }}>
                  {current.furniture_list?.length || 0} items
                  {current.total_price != null && (
                    <span style={{ color: "var(--accent)", marginLeft: "0.5rem", fontWeight: 600 }}>
                      €{current.total_price.toFixed(0)}
                    </span>
                  )}
                </p>
                {current.furniture_list?.length > 0 && (
                  <div style={styles.miniGrid}>
                    {current.furniture_list.slice(0, 6).map((item) => (
                      <div key={item.id} style={styles.miniCard}>
                        {item.image_url && (
                          <img src={item.image_url} alt={item.name} style={styles.miniImg} />
                        )}
                        <p style={{ fontSize: "0.6875rem", lineHeight: 1.2 }}>{item.name}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div style={{ marginTop: "1.5rem", display: "flex", gap: "0.75rem" }}>
              <Link
                href={`/session/${current.id}`}
                className="btn-primary"
                style={{
                  fontSize: "0.875rem",
                  padding: "0.625rem 1.5rem",
                  textDecoration: "none",
                }}
              >
                Open Session
              </Link>
              {activeIdx > 0 && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setActiveIdx(activeIdx - 1)}
                  style={{ fontSize: "0.875rem", padding: "0.625rem 1.25rem" }}
                >
                  Previous
                </button>
              )}
              {activeIdx < sessions.length - 1 && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setActiveIdx(activeIdx + 1)}
                  style={{ fontSize: "0.875rem", padding: "0.625rem 1.25rem" }}
                >
                  Next
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  page: { padding: 24, maxWidth: 900, margin: "0 auto", width: "100%" } as React.CSSProperties,
  center: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "80vh",
    textAlign: "center",
  } as React.CSSProperties,
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
  backLink: { color: "var(--text-3)", fontSize: "0.85rem" } as React.CSSProperties,
  tabs: {
    display: "flex",
    gap: "0.5rem",
    marginBottom: "1.5rem",
    flexWrap: "wrap",
  } as React.CSSProperties,
  tab: {
    padding: "0.375rem 1rem",
    borderRadius: "var(--radius-full)",
    border: "1px solid var(--border)",
    fontSize: "0.8125rem",
    fontWeight: 500,
    cursor: "pointer",
    transition: "all var(--transition-base)",
  } as React.CSSProperties,
  card: {
    background: "var(--bg)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-lg)",
    padding: "1.5rem",
    boxShadow: "var(--shadow-sm)",
  } as React.CSSProperties,
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "1.25rem",
    paddingBottom: "1rem",
    borderBottom: "1px solid var(--border)",
  } as React.CSSProperties,
  badge: {
    display: "inline-block",
    padding: "2px 10px",
    borderRadius: 12,
    fontSize: "0.78rem",
    textTransform: "capitalize",
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "1.5rem",
  } as React.CSSProperties,
  section: {} as React.CSSProperties,
  label: {
    fontSize: "0.75rem",
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: "0.5rem",
  } as React.CSSProperties,
  muted: { color: "var(--text-4)", fontSize: "0.875rem" } as React.CSSProperties,
  thumb: {
    width: "100%",
    maxWidth: 200,
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border)",
  } as React.CSSProperties,
  miniGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(3, 1fr)",
    gap: "0.5rem",
    marginTop: "0.5rem",
  } as React.CSSProperties,
  miniCard: {
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border)",
    overflow: "hidden",
    background: "var(--bg)",
  } as React.CSSProperties,
  miniImg: {
    width: "100%",
    height: 48,
    objectFit: "cover",
  } as React.CSSProperties,
} as const;
