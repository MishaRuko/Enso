"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useRef, useState } from "react";
import { getSession, listSessionJobs, cancelSession } from "@/lib/backend";
import type { DesignSession, DesignJob, TraceEvent } from "@/lib/types";

const PIPELINE_STAGES = ["analyzing_floorplan", "searching", "placing", "complete"] as const;

const STEP_COLORS: Record<string, string> = {
  started: "#8888aa",
  gemini_analysis: "#66bb6a",
  parsed: "#26c6da",
  isometric_render: "#ab47bc",
  fal_upload: "#ffa726",
  trellis_room: "#ec407a",
  room_3d: "#ec407a",
  completed: "#4caf50",
  searching: "#42a5f5",
  search_done: "#66bb6a",
  placing: "#ffa726",
  complete: "#4caf50",
  error: "#ef5350",
};

function stepColor(step: string): string {
  return STEP_COLORS[step] ?? "#8888aa";
}

function statusBadgeStyle(status: string): React.CSSProperties {
  if (status === "complete" || status === "completed" || status === "placement_ready")
    return { background: "#1b5e20", color: "#a5d6a7" };
  if (status.endsWith("_failed") || status === "failed")
    return { background: "#b71c1c", color: "#ef9a9a" };
  if (
    status === "running" ||
    status === "analyzing_floorplan" ||
    status === "searching" ||
    status === "placing"
  )
    return { background: "#e65100", color: "#ffcc80", animation: "pulse 1.5s infinite" };
  if (status === "floorplan_ready" || status === "furniture_found")
    return { background: "#0d47a1", color: "#90caf9" };
  return { background: "var(--bg-muted)", color: "var(--text-3)" };
}

function formatDateTime(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString();
}

const PROCESSING = new Set([
  "analyzing_floorplan",
  "searching",
  "sourcing",
  "placing",
  "placing_furniture",
]);

interface PageProps {
  params: Promise<{ sessionId: string }>;
}

export default function TraceDetailPage({ params }: PageProps) {
  const { sessionId } = use(params);
  const [session, setSession] = useState<DesignSession | null>(null);
  const [jobs, setJobs] = useState<DesignJob[]>([]);
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [expandedTexts, setExpandedTexts] = useState<Set<string>>(new Set());
  const [lightbox, setLightbox] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const didInitExpand = useRef(false);

  const fetchData = useCallback(async () => {
    try {
      const [s, j] = await Promise.all([getSession(sessionId), listSessionJobs(sessionId)]);
      setSession(s);
      setJobs(j);
      if (j.length > 0 && !didInitExpand.current) {
        didInitExpand.current = true;
        setExpandedJobs(new Set([j[0].id]));
      }
    } catch {
      // ignore
    }
  }, [sessionId]);

  useEffect(() => {
    fetchData();
    intervalRef.current = setInterval(() => {
      fetchData();
    }, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData]);

  useEffect(() => {
    if (session && !PROCESSING.has(session.status) && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, [session]);

  function toggleJob(id: string) {
    setExpandedJobs((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  }

  function toggleEvent(key: string) {
    setExpandedEvents((s) => {
      const n = new Set(s);
      n.has(key) ? n.delete(key) : n.add(key);
      return n;
    });
  }

  function toggleText(key: string) {
    setExpandedTexts((s) => {
      const n = new Set(s);
      n.has(key) ? n.delete(key) : n.add(key);
      return n;
    });
  }

  const TEXT_TRUNCATE = 500;

  function renderText(text: string, key: string) {
    const isExpanded = expandedTexts.has(key);
    const needsTruncation = text.length > TEXT_TRUNCATE;
    const displayed = !isExpanded && needsTruncation ? `${text.slice(0, TEXT_TRUNCATE)}...` : text;
    return (
      <div>
        <pre style={styles.promptBlock}>{displayed}</pre>
        {needsTruncation && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              toggleText(key);
            }}
            style={styles.showMoreBtn}
          >
            {isExpanded ? "Collapse" : `Show full (${text.length} chars)`}
          </button>
        )}
      </div>
    );
  }

  const isRunning = session ? PROCESSING.has(session.status) : false;

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <Link href="/tracing" style={styles.backLink}>
            &larr; All sessions
          </Link>
          <h2 style={styles.title}>
            Session: <span style={styles.mono}>{sessionId}</span>
          </h2>
        </div>
        <div style={styles.headerRight}>
          {isRunning && (
            <button
              type="button"
              style={styles.cancelBtn}
              onClick={() => cancelSession(sessionId).then(fetchData)}
            >
              Stop Pipeline
            </button>
          )}
          {session && (
            <span style={{ ...styles.statusBadge, ...statusBadgeStyle(session.status) }}>
              {session.status.replace(/_/g, " ")}
            </span>
          )}
          <span
            style={{
              fontSize: "0.75rem",
              color: isRunning ? "#66bb6a" : "var(--text-3)",
            }}
          >
            {isRunning ? "\u25CF Live" : "Idle"}
          </span>
        </div>
      </div>

      {/* Stage chips */}
      {session && (
        <div style={styles.stageBar}>
          {PIPELINE_STAGES.map((stage) => {
            const stageIdx = PIPELINE_STAGES.indexOf(stage);
            const currentIdx = PIPELINE_STAGES.indexOf(
              session.status as (typeof PIPELINE_STAGES)[number],
            );
            const isDone = currentIdx > stageIdx || session.status === "complete";
            const isActive = session.status === stage;
            return (
              <div
                key={stage}
                style={{
                  ...styles.chip,
                  background: isActive ? "var(--bg-active)" : "var(--bg-subtle)",
                  color: isActive ? "var(--text)" : isDone ? "#4caf50" : "var(--text-3)",
                }}
              >
                <span
                  style={{
                    ...styles.chipDot,
                    background: isDone ? "#4caf50" : isActive ? "#e65100" : "var(--text-4)",
                    animation: isActive ? "pulse 1.5s infinite" : "none",
                  }}
                />
                {stage.replace(/_/g, " ")}
              </div>
            );
          })}
        </div>
      )}

      {/* Session images row */}
      {session && (
        <div style={styles.imagesRow}>
          {session.floorplan_url && (
            <div style={styles.imageCard}>
              <div style={styles.imageLabel}>Floorplan</div>
              <img
                src={session.floorplan_url}
                alt="Floorplan"
                style={styles.imageThumb}
                onClick={() => setLightbox(session.floorplan_url)}
              />
            </div>
          )}
          {session.room_glb_url && (
            <div style={styles.imageCard}>
              <div style={styles.imageLabel}>Room GLB</div>
              <div style={styles.glbInfo}>
                <a
                  href={session.room_glb_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.glbLink}
                  onClick={(e) => e.stopPropagation()}
                >
                  View 3D Model &rarr;
                </a>
              </div>
            </div>
          )}
          {session.room_data && (
            <div style={styles.imageCard}>
              <div style={styles.imageLabel}>Room Data</div>
              <pre style={styles.jsonBlock}>
                {JSON.stringify(session.room_data, null, 2).slice(0, 400)}
              </pre>
            </div>
          )}
          {session.preferences && Object.keys(session.preferences).length > 0 && (
            <div style={styles.imageCard}>
              <div style={styles.imageLabel}>Preferences</div>
              <pre style={styles.jsonBlock}>
                {JSON.stringify(session.preferences, null, 2).slice(0, 400)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Furniture items (thumbnails) */}
      {session?.furniture_list && session.furniture_list.length > 0 && (
        <div style={styles.furnitureSection}>
          <div style={styles.sectionLabel}>Furniture ({session.furniture_list.length} items)</div>
          <div style={styles.furnitureGrid}>
            {session.furniture_list.map((item) => (
              <div key={item.id} style={styles.furnitureCard}>
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={item.name}
                    style={styles.furnitureImg}
                    onClick={() => setLightbox(item.image_url)}
                  />
                ) : (
                  <div style={styles.furnitureImgPlaceholder}>No image</div>
                )}
                <div style={styles.furnitureName}>{item.name}</div>
                <div style={styles.furniturePrice}>
                  {item.price > 0 ? `${item.price} ${item.currency}` : "-"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Jobs timeline */}
      <div style={styles.sectionLabel}>Jobs ({jobs.length})</div>
      <div style={styles.timeline}>
        {jobs.length === 0 && <div style={styles.empty}>No jobs yet for this session.</div>}
        {jobs.map((job) => (
          <div key={job.id} style={styles.jobEntry}>
            <div style={styles.jobHeader} onClick={() => toggleJob(job.id)}>
              <span style={styles.jobId}>{job.id}</span>
              <span style={styles.jobPhase}>{job.phase.replace(/_/g, " ")}</span>
              <span
                style={{
                  ...styles.statusBadge,
                  ...statusBadgeStyle(job.status),
                  fontSize: "0.75rem",
                  padding: "1px 8px",
                }}
              >
                {job.status}
              </span>
              <span style={styles.jobTime}>{formatDateTime(job.created_at)}</span>
              <span style={styles.expandToggle}>
                {expandedJobs.has(job.id) ? "\u25BC" : "\u25B6"}
              </span>
            </div>

            {expandedJobs.has(job.id) && (
              <div style={styles.jobDetail}>
                {(!job.trace || job.trace.length === 0) && (
                  <div style={{ ...styles.empty, padding: 20 }}>No trace events.</div>
                )}
                {job.trace?.map((evt: TraceEvent, i: number) => {
                  const evtKey = `${job.id}-${i}`;
                  const hasDetails = !!(
                    evt.input_prompt ||
                    evt.output_text ||
                    evt.input_image ||
                    evt.output_image ||
                    evt.model ||
                    evt.data
                  );
                  const isEvtExpanded = expandedEvents.has(evtKey);
                  return (
                    <div key={evtKey} style={styles.traceEntryWrapper}>
                      <div
                        style={{
                          ...styles.traceEntry,
                          cursor: hasDetails ? "pointer" : "default",
                        }}
                        onClick={() => hasDetails && toggleEvent(evtKey)}
                      >
                        <span
                          style={{
                            ...styles.stepBadge,
                            background: `${stepColor(evt.step)}20`,
                            color: stepColor(evt.step),
                            borderColor: stepColor(evt.step),
                          }}
                        >
                          {evt.step.replace(/_/g, " ")}
                        </span>
                        <span style={styles.traceMessage}>{evt.message}</span>
                        {evt.model && (
                          <span style={styles.modelTag}>{evt.model.split("/").pop()}</span>
                        )}
                        {evt.duration_ms != null && (
                          <span style={styles.duration}>
                            {evt.duration_ms < 1000
                              ? `${evt.duration_ms.toFixed(0)}ms`
                              : `${(evt.duration_ms / 1000).toFixed(1)}s`}
                          </span>
                        )}
                        {evt.image_url && (
                          <img
                            src={evt.image_url}
                            alt="trace"
                            style={styles.traceThumb}
                            onClick={(e) => {
                              e.stopPropagation();
                              setLightbox(evt.image_url!);
                            }}
                          />
                        )}
                        {evt.error && (
                          <span style={{ color: "#ef5350", fontSize: "0.78rem", fontWeight: 600 }}>
                            ERR: {evt.error}
                          </span>
                        )}
                        {hasDetails && (
                          <span style={styles.evtToggle}>
                            {isEvtExpanded ? "\u25BC" : "\u25B6"}
                          </span>
                        )}
                      </div>

                      {isEvtExpanded && (
                        <div style={styles.evtDetail}>
                          {evt.input_image && (
                            <div style={styles.evtSection}>
                              <div style={styles.evtLabel}>Input Image</div>
                              <img
                                src={evt.input_image}
                                alt="input"
                                style={styles.evtImage}
                                onClick={() => setLightbox(evt.input_image!)}
                              />
                            </div>
                          )}
                          {evt.input_prompt && (
                            <div style={styles.evtSection}>
                              <div style={styles.evtLabel}>Prompt</div>
                              {renderText(evt.input_prompt, `${evtKey}-prompt`)}
                            </div>
                          )}
                          {evt.output_text && (
                            <div style={styles.evtSection}>
                              <div style={styles.evtLabel}>Response</div>
                              {renderText(evt.output_text, `${evtKey}-output`)}
                            </div>
                          )}
                          {evt.output_image && (
                            <div style={styles.evtSection}>
                              <div style={styles.evtLabel}>Output Image</div>
                              <img
                                src={evt.output_image}
                                alt="output"
                                style={styles.evtImage}
                                onClick={() => setLightbox(evt.output_image!)}
                              />
                            </div>
                          )}
                          {evt.data && (
                            <div style={styles.evtSection}>
                              <div style={styles.evtLabel}>Data</div>
                              <pre style={styles.promptBlock}>
                                {JSON.stringify(evt.data, null, 2)}
                              </pre>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div style={styles.lightboxOverlay} onClick={() => setLightbox(null)}>
          <img
            src={lightbox}
            alt="Preview"
            style={styles.lightboxImg}
            onClick={(e) => e.stopPropagation()}
          />
          <button type="button" style={styles.lightboxClose} onClick={() => setLightbox(null)}>
            Close
          </button>
        </div>
      )}
    </div>
  );
}

const styles = {
  page: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    overflow: "hidden",
    width: "100%",
  } as React.CSSProperties,
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "16px 24px",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
  } as React.CSSProperties,
  headerLeft: { display: "flex", alignItems: "center", gap: 16 } as React.CSSProperties,
  headerRight: { display: "flex", alignItems: "center", gap: 12 } as React.CSSProperties,
  backLink: { color: "var(--text-3)", fontSize: "0.85rem" } as React.CSSProperties,
  title: {
    fontSize: "1.1rem",
    color: "var(--text)",
    fontWeight: 600,
  } as React.CSSProperties,
  mono: { fontFamily: "monospace", fontSize: "0.95rem" } as React.CSSProperties,
  cancelBtn: {
    background: "#b71c1c",
    color: "#ef9a9a",
    border: "none",
    borderRadius: 6,
    padding: "6px 14px",
    fontSize: "0.82rem",
    cursor: "pointer",
    fontWeight: 600,
  } as React.CSSProperties,
  statusBadge: {
    padding: "3px 12px",
    borderRadius: 12,
    fontSize: "0.8rem",
    textTransform: "capitalize",
  } as React.CSSProperties,
  stageBar: {
    display: "flex",
    gap: 8,
    padding: "12px 24px",
    borderBottom: "1px solid var(--border)",
    overflowX: "auto",
    flexShrink: 0,
  } as React.CSSProperties,
  chip: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "4px 12px",
    borderRadius: 16,
    fontSize: "0.78rem",
    whiteSpace: "nowrap",
    transition: "all 0.3s",
  } as React.CSSProperties,
  chipDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    flexShrink: 0,
  } as React.CSSProperties,
  imagesRow: {
    display: "flex",
    gap: 12,
    padding: "12px 24px",
    borderBottom: "1px solid var(--border)",
    overflowX: "auto",
    flexShrink: 0,
  } as React.CSSProperties,
  imageCard: {
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
    gap: 4,
  } as React.CSSProperties,
  imageLabel: {
    fontSize: "0.72rem",
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  } as React.CSSProperties,
  imageThumb: {
    width: 140,
    height: 100,
    objectFit: "cover",
    borderRadius: 6,
    border: "1px solid var(--border)",
    cursor: "pointer",
  } as React.CSSProperties,
  glbInfo: {
    width: 140,
    height: 100,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--bg-subtle)",
    borderRadius: 6,
    border: "1px solid var(--border)",
  } as React.CSSProperties,
  glbLink: {
    color: "var(--accent)",
    fontSize: "0.8rem",
    fontWeight: 500,
  } as React.CSSProperties,
  jsonBlock: {
    width: 200,
    maxHeight: 100,
    overflow: "auto",
    background: "var(--bg-code)",
    border: "1px solid var(--border)",
    borderRadius: 4,
    padding: 8,
    fontFamily: "monospace",
    fontSize: "0.68rem",
    lineHeight: 1.4,
    color: "var(--text-3)",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
  } as React.CSSProperties,
  furnitureSection: {
    padding: "12px 24px",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
  } as React.CSSProperties,
  sectionLabel: {
    fontSize: "0.75rem",
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    padding: "12px 24px 4px",
    flexShrink: 0,
  } as React.CSSProperties,
  furnitureGrid: {
    display: "flex",
    gap: 10,
    overflowX: "auto",
    paddingTop: 8,
    paddingBottom: 4,
  } as React.CSSProperties,
  furnitureCard: {
    flexShrink: 0,
    width: 100,
    display: "flex",
    flexDirection: "column",
    gap: 4,
  } as React.CSSProperties,
  furnitureImg: {
    width: 100,
    height: 80,
    objectFit: "cover",
    borderRadius: 4,
    border: "1px solid var(--border)",
    cursor: "pointer",
  } as React.CSSProperties,
  furnitureImgPlaceholder: {
    width: 100,
    height: 80,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--bg-subtle)",
    borderRadius: 4,
    border: "1px solid var(--border)",
    fontSize: "0.7rem",
    color: "var(--text-4)",
  } as React.CSSProperties,
  furnitureName: {
    fontSize: "0.72rem",
    color: "var(--text)",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  } as React.CSSProperties,
  furniturePrice: {
    fontSize: "0.68rem",
    color: "var(--text-3)",
  } as React.CSSProperties,
  timeline: {
    flex: 1,
    overflowY: "auto",
    padding: "8px 24px 24px",
  } as React.CSSProperties,
  empty: {
    color: "var(--text-3)",
    textAlign: "center",
    padding: 40,
    fontSize: "0.9rem",
  } as React.CSSProperties,
  jobEntry: {
    marginBottom: 6,
    borderRadius: 6,
    background: "var(--bg-glass)",
    border: "1px solid var(--border)",
  } as React.CSSProperties,
  jobHeader: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    padding: "10px 12px",
    cursor: "pointer",
    fontSize: "0.85rem",
  } as React.CSSProperties,
  jobId: {
    fontFamily: "monospace",
    fontSize: "0.78rem",
    color: "var(--text-3)",
    flexShrink: 0,
  } as React.CSSProperties,
  jobPhase: {
    fontWeight: 500,
    textTransform: "capitalize",
    flexShrink: 0,
  } as React.CSSProperties,
  jobTime: {
    color: "var(--text-3)",
    fontSize: "0.78rem",
    marginLeft: "auto",
    flexShrink: 0,
  } as React.CSSProperties,
  expandToggle: {
    color: "var(--text-4)",
    fontSize: "0.7rem",
    width: 14,
    textAlign: "center",
  } as React.CSSProperties,
  jobDetail: {
    padding: "8px 12px 12px",
    borderTop: "1px solid var(--border)",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  } as React.CSSProperties,
  traceEntryWrapper: {
    borderRadius: 4,
    overflow: "hidden",
  } as React.CSSProperties,
  traceEntry: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "4px 8px",
    borderRadius: 4,
    fontSize: "0.82rem",
  } as React.CSSProperties,
  stepBadge: {
    padding: "2px 8px",
    borderRadius: 10,
    fontSize: "0.72rem",
    border: "1px solid",
    flexShrink: 0,
    textTransform: "capitalize",
  } as React.CSSProperties,
  traceMessage: {
    color: "var(--text-2)",
  } as React.CSSProperties,
  duration: {
    color: "#e65100",
    fontSize: "0.75rem",
    marginLeft: "auto",
    flexShrink: 0,
  } as React.CSSProperties,
  traceThumb: {
    width: 40,
    height: 40,
    objectFit: "cover",
    borderRadius: 4,
    cursor: "pointer",
    border: "1px solid var(--border)",
  } as React.CSSProperties,
  modelTag: {
    background: "#1a237e",
    color: "#9fa8da",
    fontSize: "0.68rem",
    padding: "1px 8px",
    borderRadius: 8,
    flexShrink: 0,
    fontFamily: "monospace",
  } as React.CSSProperties,
  evtToggle: {
    color: "var(--text-4)",
    fontSize: "0.65rem",
    width: 12,
    textAlign: "center",
    flexShrink: 0,
    marginLeft: 4,
  } as React.CSSProperties,
  evtDetail: {
    padding: "8px 12px 12px 28px",
    display: "flex",
    flexDirection: "column",
    gap: 10,
    borderTop: "1px solid var(--border)",
    background: "var(--bg-subtle)",
  } as React.CSSProperties,
  evtSection: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  } as React.CSSProperties,
  evtLabel: {
    fontSize: "0.68rem",
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    fontWeight: 600,
  } as React.CSSProperties,
  evtImage: {
    maxWidth: 240,
    maxHeight: 180,
    objectFit: "contain",
    borderRadius: 4,
    border: "1px solid var(--border)",
    cursor: "pointer",
    background: "#fff",
  } as React.CSSProperties,
  promptBlock: {
    background: "var(--bg-code)",
    border: "1px solid var(--border)",
    borderRadius: 4,
    padding: 8,
    fontFamily: "monospace",
    fontSize: "0.72rem",
    lineHeight: 1.5,
    color: "var(--text-2)",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    maxHeight: 300,
    overflowY: "auto",
    margin: 0,
  } as React.CSSProperties,
  showMoreBtn: {
    background: "none",
    border: "none",
    color: "var(--accent)",
    fontSize: "0.72rem",
    cursor: "pointer",
    padding: "2px 0",
    fontWeight: 500,
  } as React.CSSProperties,
  lightboxOverlay: {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100vw",
    height: "100vh",
    background: "rgba(0,0,0,0.85)",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  } as React.CSSProperties,
  lightboxImg: {
    maxWidth: "90vw",
    maxHeight: "80vh",
    borderRadius: 6,
    border: "2px solid var(--accent)",
  } as React.CSSProperties,
  lightboxClose: {
    marginTop: 16,
    background: "var(--bg-glass)",
    border: "1px solid var(--border)",
    color: "var(--text)",
    fontSize: "0.85rem",
    padding: "6px 20px",
    borderRadius: 100,
    cursor: "pointer",
  } as React.CSSProperties,
} as const;
