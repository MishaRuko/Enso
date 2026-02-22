"use client";

import { use, useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { usePolling } from "@/hooks/use-polling";
import { RoomViewer, preloadRoomGlb } from "@/components/room-viewer";
import { FurnitureSidebar } from "@/components/furniture-sidebar";
import { FloorplanUpload } from "@/components/floorplan-upload";
import { StatusBar } from "@/components/status-bar";
import { EnsoSpinner } from "@/components/enso-logo";
import { createSession, runPipeline, listSessionJobs, savePlacements } from "@/lib/backend";
import type {
  DesignJob,
  DesignSession,
  FurniturePlacement,
  RoomData,
  TraceEvent,
} from "@/lib/types";

export default function SessionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const { session, error, refetch } = usePolling(id);

  // If the session doesn't exist (404), create a new one and redirect
  useEffect(() => {
    if (error?.includes("404")) {
      createSession().then(({ session_id }) => {
        router.replace(`/session/${session_id}`);
      });
    }
  }, [error, router]);
  const [pipelineStarting, setPipelineStarting] = useState(false);
  const [localPlacements, setLocalPlacements] = useState<FurniturePlacement[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [viewPhase, setViewPhase] = useState<number | null>(null);

  function handlePhaseClick(idx: number) {
    setViewPhase((prev) => (prev === idx ? null : idx));
  }

  // Sync local placements when session placements change (e.g. pipeline completes)
  const serverPlacements = session?.placements?.placements;
  useEffect(() => {
    if (serverPlacements) {
      setLocalPlacements(serverPlacements);
    }
  }, [serverPlacements]);

  const hasUnsavedChanges =
    localPlacements != null &&
    serverPlacements != null &&
    JSON.stringify(localPlacements) !== JSON.stringify(serverPlacements);

  async function handleSaveLayout() {
    if (!localPlacements) return;
    setSaving(true);
    try {
      await savePlacements(id, { placements: localPlacements });
      refetch();
    } catch (err) {
      console.error("Failed to save layout:", err);
    } finally {
      setSaving(false);
    }
  }

  // Dynamic tab title based on pipeline phase
  const status = session?.status;
  useEffect(() => {
    const labels: Record<string, string> = {
      pending: "Upload Floorplan",
      consulting: "Consultation",
      analyzing_floorplan: "Analyzing...",
      floorplan_ready: "Floorplan Ready",
      searching: "Curating Furniture...",
      furniture_found: "Furniture Found",
      sourcing: "Sourcing Models...",
      placing: "Placing Furniture...",
      placing_furniture: "Placing...",
      complete: "Design Complete",
      placement_ready: "Design Complete",
    };
    const label = status ? labels[status] || status.replace(/_/g, " ") : "Loading";
    document.title = `${label} | Enso`;
    return () => {
      document.title = "Enso \u2014 your space, complete.";
    };
  }, [status]);

  if (error && !session) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          gap: "1rem",
          animation: "fadeUp 0.6s ease-out",
        }}
      >
        <div
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            background: "var(--error-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg
            width="28"
            height="28"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--error)"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <div style={{ color: "var(--error)", fontWeight: 600, fontSize: "1.125rem" }}>
          Something went wrong
        </div>
        <div style={{ color: "var(--muted)", fontSize: "0.875rem" }}>{error}</div>
      </div>
    );
  }

  if (!session) {
    return (
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100vh",
          gap: "1rem",
        }}
      >
        <EnsoSpinner size={48} />
        <div
          style={{
            color: "var(--muted)",
            fontSize: "0.875rem",
            letterSpacing: "0.02em",
            animation: "progressPulse 2s ease-in-out infinite",
          }}
        >
          Loading session...
        </div>
      </div>
    );
  }

  // Preload GLB as soon as the URL is available (even while still processing)
  preloadRoomGlb(session.room_glb_url);

  // After early returns, session is guaranteed — narrow status to string
  const currentStatus = status!;
  const rooms = session.room_data?.rooms;
  const roomData =
    rooms && rooms.length > 0
      ? rooms.reduce((a, b) => ((a.area_sqm ?? 0) >= (b.area_sqm ?? 0) ? a : b))
      : undefined;
  const placements = session.placements?.placements;
  const hasFurniture = session.furniture_list && session.furniture_list.length > 0;
  const isFailed = currentStatus.endsWith("_failed");
  const isProcessing = [
    "analyzing_floorplan",
    "searching",
    "sourcing",
    "placing",
    "placing_furniture",
  ].includes(currentStatus);
  const isComplete = currentStatus === "complete" || currentStatus === "placement_ready" || currentStatus === "checkout";
  const canRunPipeline = currentStatus === "floorplan_ready" || currentStatus === "consulting";

  async function handleRunPipeline() {
    setPipelineStarting(true);
    try {
      await runPipeline(id);
      refetch();
    } catch (err) {
      console.error("Pipeline start failed:", err);
    } finally {
      setPipelineStarting(false);
    }
  }

  async function handleRetry() {
    await handleRunPipeline();
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <StatusBar
        currentPhase={currentStatus}
        onPhaseClick={handlePhaseClick}
        viewPhase={viewPhase}
      />

      {session.miro_board_url && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            padding: "0.5rem 1.5rem",
            background: "var(--surface)",
            borderBottom: "1px solid var(--border)",
            fontSize: "0.8125rem",
          }}
        >
          <svg
            width="14"
            height="14"
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
          <span style={{ color: "var(--muted)", fontWeight: 600 }}>Vision Board</span>
          <a
            href={session.miro_board_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              color: "var(--accent)",
              textDecoration: "none",
              fontWeight: 500,
              display: "inline-flex",
              alignItems: "center",
              gap: "0.25rem",
            }}
          >
            Open in Miro
            <svg
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>
        </div>
      )}

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Main content area */}
        <div style={{ flex: 1, position: "relative" }}>
          {/* "Back to live" chip when viewing a past phase */}
          {viewPhase !== null && (
            <div
              style={{
                position: "absolute",
                top: "1rem",
                left: "50%",
                transform: "translateX(-50%)",
                zIndex: 20,
                animation: "fadeUp 0.3s ease-out",
              }}
            >
              <button
                type="button"
                onClick={() => setViewPhase(null)}
                style={{
                  background: "rgba(250,249,247,0.95)",
                  backdropFilter: "blur(12px)",
                  border: "1px solid var(--border-hover)",
                  borderRadius: "var(--radius-full)",
                  padding: "0.375rem 1rem",
                  fontSize: "0.8125rem",
                  color: "var(--text)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.375rem",
                  boxShadow: "var(--shadow-md)",
                }}
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="15 18 9 12 15 6" />
                </svg>
                Back to live view
              </button>
            </div>
          )}

          {/* Phase-specific view when a StatusBar phase is clicked */}
          {viewPhase !== null ? (
            <PhaseView
              phase={viewPhase}
              session={session}
              roomData={roomData}
              rooms={rooms}
              localPlacements={localPlacements}
              placements={placements}
              setLocalPlacements={setLocalPlacements}
            />
          ) : (
            <>
              {/* pending -- show floorplan upload */}
              {currentStatus === "pending" && (
                <div style={{ animation: "fadeUp 0.6s ease-out" }}>
                  <FloorplanUpload sessionId={id} onUploaded={refetch} />
                </div>
              )}

              {/* consulting -- preferences saved, vision board generating, show upload */}
              {currentStatus === "consulting" && (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    height: "100%",
                    animation: "fadeUp 0.6s ease-out",
                  }}
                >
                  {!session.miro_board_url && (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "0.75rem",
                        padding: "0.75rem 1.5rem",
                        background: "var(--accent-subtle)",
                        borderBottom: "1px solid var(--border)",
                        fontSize: "0.8125rem",
                      }}
                    >
                      <span
                        style={{
                          width: "12px",
                          height: "12px",
                          border: "2px solid var(--border)",
                          borderTopColor: "var(--accent)",
                          borderRadius: "50%",
                          flexShrink: 0,
                          animation: "spin 0.8s linear infinite",
                          display: "inline-block",
                        }}
                      />
                      <span style={{ color: "var(--text-secondary)" }}>
                        Generating your vision board in the background — it will appear above when ready
                        (2–4 min).
                      </span>
                    </div>
                  )}
                  <FloorplanUpload sessionId={id} onUploaded={refetch} />
                </div>
              )}

              {/* analyzing_floorplan -- live progress */}
              {currentStatus === "analyzing_floorplan" && (
                <CenterMessage>
                  <PipelineProgress sessionId={id} phase="Analyzing floorplan" />
                </CenterMessage>
              )}

              {/* floorplan_ready -- show 3D room preview + run pipeline button */}
              {canRunPipeline && currentStatus === "floorplan_ready" && (
                <div
                  style={{
                    width: "100%",
                    height: "100%",
                    position: "relative",
                    animation: "fadeUp 0.6s ease-out",
                  }}
                >
                  <RoomViewer
                    roomData={roomData}
                    roomGlbUrl={session.room_glb_url}
                    allRooms={rooms}
                    placements={undefined}
                    furnitureItems={undefined}
                    floorplanUrl={session.floorplan_url}
                  />
                  <div
                    style={{
                      position: "absolute",
                      bottom: "5rem",
                      left: 0,
                      right: 0,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      gap: "0.75rem",
                      zIndex: 10,
                      animation: "fadeUp 0.6s ease-out 0.3s both",
                    }}
                  >
                    <p
                      style={{
                        fontSize: "0.875rem",
                        color: "var(--text-2)",
                        background: "rgba(250,249,247,0.9)",
                        backdropFilter: "blur(12px)",
                        padding: "0.375rem 1rem",
                        borderRadius: "var(--radius-full)",
                        border: "1px solid rgba(236,230,219,0.5)",
                      }}
                    >
                      {roomData
                        ? `${roomData.name} — ${roomData.width_m}m \u00D7 ${roomData.length_m}m`
                        : "Room preview"}
                    </p>
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={handleRunPipeline}
                      disabled={pipelineStarting}
                      style={{
                        fontSize: "1rem",
                        boxShadow: "0 6px 32px rgba(219,80,74,0.3)",
                      }}
                    >
                      {pipelineStarting ? "Starting..." : "Begin Design"}
                    </button>
                  </div>
                </div>
              )}

              {/* processing states -- live progress */}
              {isProcessing && currentStatus !== "analyzing_floorplan" && (
                <CenterMessage>
                  <PipelineProgress
                    sessionId={id}
                    phase={
                      currentStatus === "searching"
                        ? "Curating furniture"
                        : currentStatus === "sourcing"
                          ? "Sourcing 3D models"
                          : "Computing placement"
                    }
                  />
                </CenterMessage>
              )}

              {/* failed states -- show error with retry */}
              {isFailed && (
                <CenterMessage>
                  <div
                    style={{
                      width: "56px",
                      height: "56px",
                      borderRadius: "50%",
                      background: "var(--error-subtle)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      marginBottom: "1.25rem",
                      animation: "fadeInScale 0.3s ease-out",
                    }}
                  >
                    <svg
                      width="28"
                      height="28"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--error)"
                      strokeWidth="2"
                    >
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </div>
                  <p
                    style={{
                      fontSize: "1.25rem",
                      fontWeight: 600,
                      color: "var(--error)",
                      marginBottom: "0.375rem",
                    }}
                  >
                    {currentStatus.replace(/_/g, " ").replace("failed", "Failed")}
                  </p>
                  <p style={{ color: "var(--muted)", marginBottom: "2rem", fontSize: "0.9375rem" }}>
                    Something went wrong. You can try again.
                  </p>
                  <button type="button" className="btn-primary" onClick={handleRetry}>
                    Try Again
                  </button>
                </CenterMessage>
              )}

              {/* complete -- show 3D viewer */}
              {isComplete && (
                <div style={{ width: "100%", height: "100%", animation: "fadeUp 0.6s ease-out" }}>
                  <RoomViewer
                    roomData={roomData}
                    roomGlbUrl={session.room_glb_url}
                    allRooms={rooms}
                    placements={localPlacements ?? placements}
                    furnitureItems={session.furniture_list}
                    floorplanUrl={session.floorplan_url}
                    onPlacementChange={setLocalPlacements}
                  />
                  {hasUnsavedChanges && (
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={handleSaveLayout}
                      disabled={saving}
                      style={{
                        position: "absolute",
                        top: "1rem",
                        right: "1rem",
                        zIndex: 10,
                        fontSize: "0.875rem",
                        padding: "0.5rem 1.25rem",
                        boxShadow: "0 4px 20px rgba(219,80,74,0.25)",
                        animation: "fadeUp 0.3s ease-out",
                      }}
                    >
                      {saving ? "Saving..." : "Save Layout"}
                    </button>
                  )}
                </div>
              )}

              {/* furniture_found */}
              {currentStatus === "furniture_found" && (
                <CenterMessage>
                  <PipelineProgress sessionId={id} phase="Pieces selected" />
                </CenterMessage>
              )}
            </>
          )}
        </div>

        {/* Sidebar -- show when complete with furniture, or when viewing furniture/placement phases */}
        {((isComplete && hasFurniture) ||
          (viewPhase !== null && viewPhase >= 2 && hasFurniture)) && (
          <div
            style={{
              width: "340px",
              flexShrink: 0,
              animation: "slideInRight 0.4s ease-out",
            }}
          >
            <FurnitureSidebar sessionId={id} items={session.furniture_list} />
          </div>
        )}
      </div>
    </div>
  );
}

function PhaseView({
  phase,
  session,
  roomData,
  rooms,
  localPlacements,
  placements,
  setLocalPlacements,
}: {
  phase: number;
  session: DesignSession;
  roomData: RoomData | undefined;
  rooms: RoomData[] | undefined;
  localPlacements: FurniturePlacement[] | null;
  placements: FurniturePlacement[] | undefined;
  setLocalPlacements: (p: FurniturePlacement[]) => void;
}) {
  if (phase === 0) {
    return (
      <CenterMessage>
        {session.floorplan_url ? (
          <div style={{ animation: "fadeUp 0.4s ease-out" }}>
            <img
              src={session.floorplan_url}
              alt="Uploaded floorplan"
              style={{
                maxWidth: "80%",
                maxHeight: "70vh",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                boxShadow: "var(--shadow-md)",
              }}
            />
            <p style={{ color: "var(--muted)", marginTop: "1rem", fontSize: "0.875rem" }}>
              Uploaded floorplan
            </p>
          </div>
        ) : (
          <p style={{ color: "var(--muted)" }}>No floorplan uploaded yet</p>
        )}
      </CenterMessage>
    );
  }

  if (phase === 1) {
    if (!session.room_glb_url && !roomData) {
      return (
        <CenterMessage>
          <p style={{ color: "var(--muted)" }}>Room analysis not available yet</p>
        </CenterMessage>
      );
    }
    return (
      <div style={{ width: "100%", height: "100%", animation: "fadeUp 0.4s ease-out" }}>
        <RoomViewer
          roomData={roomData}
          roomGlbUrl={session.room_glb_url}
          allRooms={rooms}
          placements={undefined}
          furnitureItems={undefined}
          floorplanUrl={session.floorplan_url}
        />
        {roomData && (
          <div
            style={{
              position: "absolute",
              bottom: "2rem",
              left: "50%",
              transform: "translateX(-50%)",
              background: "rgba(250,249,247,0.9)",
              backdropFilter: "blur(12px)",
              padding: "0.375rem 1rem",
              borderRadius: "var(--radius-full)",
              border: "1px solid rgba(236,230,219,0.5)",
              fontSize: "0.875rem",
              color: "var(--text-2)",
              zIndex: 10,
            }}
          >
            {roomData.name} — {roomData.width_m}m × {roomData.length_m}m
          </div>
        )}
      </div>
    );
  }

  if (phase === 2 || phase === 3) {
    const items = session.furniture_list;
    if (!items || items.length === 0) {
      return (
        <CenterMessage>
          <p style={{ color: "var(--muted)" }}>No furniture found yet</p>
        </CenterMessage>
      );
    }
    return (
      <div
        style={{
          padding: "2rem",
          overflowY: "auto",
          height: "100%",
          animation: "fadeUp 0.4s ease-out",
        }}
      >
        <h3
          style={{
            fontFamily: "var(--font-display), sans-serif",
            fontWeight: 400,
            fontSize: "1.125rem",
            marginBottom: "1rem",
            color: "var(--text)",
          }}
        >
          {phase === 2 ? "Curated Furniture" : "Sourced 3D Models"} ({items.length} items)
        </h3>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
            gap: "1rem",
          }}
        >
          {items.map((item) => (
            <div
              key={item.id}
              style={{
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border)",
                background: "var(--bg)",
                overflow: "hidden",
              }}
            >
              {item.image_url && (
                <img
                  src={item.image_url}
                  alt={item.name}
                  style={{ width: "100%", height: 140, objectFit: "cover" }}
                />
              )}
              <div style={{ padding: "0.75rem" }}>
                <p
                  style={{
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    marginBottom: "0.25rem",
                    lineHeight: 1.3,
                  }}
                >
                  {item.name}
                </p>
                <div
                  style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}
                >
                  <span style={{ fontSize: "0.8125rem", color: "var(--accent)", fontWeight: 600 }}>
                    {item.currency === "EUR" ? "€" : item.currency}
                    {item.price}
                  </span>
                  {phase === 3 && (
                    <span
                      style={{
                        fontSize: "0.6875rem",
                        padding: "2px 6px",
                        borderRadius: "var(--radius-full)",
                        background: item.glb_url ? "var(--sage-glow)" : "var(--error-subtle)",
                        color: item.glb_url ? "var(--sage)" : "var(--error)",
                      }}
                    >
                      {item.glb_url ? "3D ready" : "No 3D"}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (phase === 4 || phase === 5) {
    return (
      <div style={{ width: "100%", height: "100%", animation: "fadeUp 0.4s ease-out" }}>
        <RoomViewer
          roomData={roomData}
          roomGlbUrl={session.room_glb_url}
          allRooms={rooms}
          placements={localPlacements ?? placements}
          furnitureItems={session.furniture_list}
          floorplanUrl={session.floorplan_url}
          onPlacementChange={setLocalPlacements}
        />
      </div>
    );
  }

  return null;
}

function CenterMessage({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        padding: "2rem",
        textAlign: "center",
        animation: "fadeUp 0.6s ease-out",
      }}
    >
      {children}
    </div>
  );
}

const STEP_LABELS: Record<string, string> = {
  started: "Starting pipeline",
  gemini_analysis: "Analyzing floorplan with Gemini",
  parsed: "Room analysis complete",
  isometric_render: "Generating 3D render",
  fal_upload: "Uploading to cloud",
  trellis_room: "Building 3D room model",
  room_3d: "Building 3D room model",
  completed: "Done",
  shopping_list: "Generating furniture list",
  search_done: "Search complete",
  gemini_attempt_1: "Computing placement",
  gemini_response_1: "Placement computed",
  downloading_floorplan: "Downloading floorplan",
  render_binary: "Rendering binary floorplan",
  nano_banana: "Coloring rooms",
  grid_building: "Building placement grid",
  grid_ready: "Placement grid built",
  furniture_specs: "Generating furniture list",
  searching_ikea: "Searching IKEA catalog",
  constraints: "Generating placement constraints",
  optimizing: "Running Gurobi optimizer",
  trellis_3d: "Generating 3D models",
  error: "Error",
};

function PipelineProgress({ sessionId, phase }: { sessionId: string; phase: string }) {
  const [jobs, setJobs] = useState<DesignJob[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());
  const [lightbox, setLightbox] = useState<string | null>(null);
  const [expandedStep, setExpandedStep] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const j = await listSessionJobs(sessionId);
      setJobs(j);
    } catch {
      // ignore
    }
  }, [sessionId]);

  useEffect(() => {
    fetchJobs();
    const jobInterval = setInterval(fetchJobs, 2000);
    const tickInterval = setInterval(() => setElapsed(Date.now() - startRef.current), 500);
    return () => {
      clearInterval(jobInterval);
      clearInterval(tickInterval);
    };
  }, [fetchJobs]);

  const allEvents: TraceEvent[] = [];
  for (const job of jobs) {
    if (job.trace) {
      for (const evt of job.trace) allEvents.push(evt);
    }
  }

  const rawCompleted = allEvents.filter((e) => e.duration_ms != null && e.step !== "started");

  // Group consecutive steps with the same base name (e.g. search_item_0, search_item_1 → search_item)
  type StepGroup = { events: TraceEvent[]; baseStep: string };
  const stepGroups: StepGroup[] = [];
  for (const evt of rawCompleted) {
    const base = evt.step.replace(/_\d+$/, "");
    const last = stepGroups[stepGroups.length - 1];
    if (last && last.baseStep === base) {
      last.events.push(evt);
    } else {
      stepGroups.push({ events: [evt], baseStep: base });
    }
  }
  const lastEvent = allEvents[allEvents.length - 1];
  const allImages = allEvents
    .map((e) => e.image_url || e.output_image)
    .filter((url): url is string => !!url);
  const lastImage = allImages[allImages.length - 1];

  const elapsedSec = Math.floor(elapsed / 1000);
  const mins = Math.floor(elapsedSec / 60);
  const secs = elapsedSec % 60;
  const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "1.5rem",
        maxWidth: 420,
        maxHeight: "80vh",
        overflowY: "auto",
      }}
    >
      <EnsoSpinner size={48} />

      <div style={{ textAlign: "center" }}>
        <p
          style={{
            fontSize: "1.125rem",
            fontWeight: 600,
            marginBottom: "0.25rem",
            letterSpacing: "0.01em",
          }}
        >
          {phase}
        </p>
        <p style={{ color: "var(--muted)", fontSize: "0.8125rem" }}>{timeStr} elapsed</p>
      </div>

      {lastImage && (
        <img
          src={lastImage}
          alt="Progress"
          onClick={() => setLightbox(lastImage)}
          style={{
            width: 200,
            height: 140,
            objectFit: "cover",
            borderRadius: 8,
            border: "1px solid rgba(26,26,56,0.08)",
            cursor: "pointer",
            animation: "fadeUp 0.4s ease-out",
          }}
        />
      )}

      {stepGroups.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%" }}>
          {stepGroups.map((group, gi) => {
            if (group.events.length > 1) {
              const groupKey = `group-${gi}`;
              const isExpanded = expandedStep === groupKey;
              const totalMs = group.events.reduce((s, e) => s + (e.duration_ms ?? 0), 0);
              const foundCount = group.events.filter(
                (e) => e.message && !e.message.includes("\u2192 0 found"),
              ).length;
              const label =
                STEP_LABELS[group.baseStep] || group.baseStep.replace(/_/g, " ");
              return (
                <div key={groupKey} style={{ animation: "fadeUp 0.3s ease-out" }}>
                  <div
                    onClick={() => setExpandedStep(isExpanded ? null : groupKey)}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "6px 12px",
                      borderRadius: isExpanded ? "8px 8px 0 0" : 8,
                      background: "rgba(250,249,247,0.7)",
                      backdropFilter: "blur(8px)",
                      border: "1px solid rgba(236,230,219,0.5)",
                      borderBottom: isExpanded
                        ? "1px dashed rgba(236,230,219,0.5)"
                        : undefined,
                      fontSize: "0.8125rem",
                      cursor: "pointer",
                    }}
                  >
                    <span
                      style={{ color: "var(--sage)", fontSize: "0.875rem", flexShrink: 0 }}
                    >
                      {"\u2713"}
                    </span>
                    <span style={{ color: "var(--text)", flex: 1 }}>
                      {label}{" "}
                      <span style={{ color: "var(--muted)" }}>
                        \u00D7{group.events.length}
                      </span>
                      {foundCount > 0 && (
                        <span style={{ color: "var(--muted)", marginLeft: 4 }}>
                          \u2014 {foundCount} found
                        </span>
                      )}
                    </span>
                    <span
                      style={{ color: "var(--muted)", fontSize: "0.75rem", flexShrink: 0 }}
                    >
                      {totalMs < 1000
                        ? `${totalMs.toFixed(0)}ms`
                        : `${(totalMs / 1000).toFixed(1)}s`}
                    </span>
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--muted)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      style={{
                        flexShrink: 0,
                        transition: "transform 0.2s",
                        transform: isExpanded ? "rotate(180deg)" : "rotate(0)",
                      }}
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  </div>
                  {isExpanded && (
                    <div
                      style={{
                        padding: "6px 12px",
                        borderRadius: "0 0 8px 8px",
                        background: "rgba(246,244,240,0.9)",
                        border: "1px solid rgba(236,230,219,0.5)",
                        borderTop: "none",
                        fontSize: "0.75rem",
                        display: "flex",
                        flexDirection: "column",
                        gap: 4,
                        maxHeight: 240,
                        overflowY: "auto",
                      }}
                    >
                      {group.events.map((evt, j) => (
                        <div
                          key={`${group.baseStep}-${j}`}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: 6,
                            padding: "2px 0",
                          }}
                        >
                          <span style={{ color: "var(--sage)", fontSize: "0.75rem" }}>
                            {"\u2713"}
                          </span>
                          <span style={{ color: "var(--text-2)", flex: 1 }}>
                            {evt.message || evt.step.replace(/_/g, " ")}
                          </span>
                          <span style={{ color: "var(--muted)", fontSize: "0.6875rem" }}>
                            {evt.duration_ms != null &&
                              (evt.duration_ms < 1000
                                ? `${evt.duration_ms.toFixed(0)}ms`
                                : `${(evt.duration_ms / 1000).toFixed(1)}s`)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            }

            const evt = group.events[0];
            const stepKey = `${evt.step}-${gi}`;
            const isExpanded = expandedStep === stepKey;
            const hasDetails =
              evt.input_prompt ||
              evt.output_text ||
              evt.input_image ||
              evt.image_url ||
              evt.model;
            return (
              <div key={stepKey} style={{ animation: "fadeUp 0.3s ease-out" }}>
                <div
                  onClick={
                    hasDetails
                      ? () => setExpandedStep(isExpanded ? null : stepKey)
                      : undefined
                  }
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    padding: "6px 12px",
                    borderRadius: isExpanded ? "8px 8px 0 0" : 8,
                    background: "rgba(250,249,247,0.7)",
                    backdropFilter: "blur(8px)",
                    border: "1px solid rgba(236,230,219,0.5)",
                    borderBottom: isExpanded
                      ? "1px dashed rgba(236,230,219,0.5)"
                      : undefined,
                    fontSize: "0.8125rem",
                    cursor: hasDetails ? "pointer" : "default",
                  }}
                >
                  <span
                    style={{ color: "var(--sage)", fontSize: "0.875rem", flexShrink: 0 }}
                  >
                    {"\u2713"}
                  </span>
                  <span style={{ color: "var(--text)", flex: 1 }}>
                    {STEP_LABELS[evt.step] ||
                      evt.message ||
                      evt.step.replace(/_/g, " ")}
                  </span>
                  {evt.image_url && (
                    <img
                      src={evt.image_url}
                      alt=""
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: 4,
                        objectFit: "cover",
                        flexShrink: 0,
                      }}
                    />
                  )}
                  {evt.duration_ms != null && (
                    <span
                      style={{ color: "var(--muted)", fontSize: "0.75rem", flexShrink: 0 }}
                    >
                      {evt.duration_ms < 1000
                        ? `${evt.duration_ms.toFixed(0)}ms`
                        : `${(evt.duration_ms / 1000).toFixed(1)}s`}
                    </span>
                  )}
                  {hasDetails && (
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="var(--muted)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      style={{
                        flexShrink: 0,
                        transition: "transform 0.2s",
                        transform: isExpanded ? "rotate(180deg)" : "rotate(0)",
                      }}
                    >
                      <polyline points="6 9 12 15 18 9" />
                    </svg>
                  )}
                </div>
                {isExpanded && (
                  <div
                    style={{
                      padding: "8px 12px",
                      borderRadius: "0 0 8px 8px",
                      background: "rgba(246,244,240,0.9)",
                      border: "1px solid rgba(236,230,219,0.5)",
                      borderTop: "none",
                      fontSize: "0.75rem",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.5rem",
                      maxHeight: 320,
                      overflowY: "auto",
                    }}
                  >
                    {evt.model && (
                      <div
                        style={{
                          color: "var(--muted)",
                          fontFamily: "monospace",
                          fontSize: "0.6875rem",
                        }}
                      >
                        Model: {evt.model}
                      </div>
                    )}
                    {evt.input_image && (
                      <div>
                        <div
                          style={{
                            color: "var(--muted)",
                            marginBottom: 4,
                            fontWeight: 600,
                          }}
                        >
                          Input
                        </div>
                        <img
                          src={evt.input_image}
                          alt="Input"
                          onClick={() => setLightbox(evt.input_image!)}
                          style={{
                            maxWidth: "100%",
                            maxHeight: 120,
                            borderRadius: 6,
                            cursor: "pointer",
                            border: "1px solid var(--border)",
                          }}
                        />
                      </div>
                    )}
                    {evt.input_prompt && (
                      <div>
                        <div
                          style={{
                            color: "var(--muted)",
                            marginBottom: 4,
                            fontWeight: 600,
                          }}
                        >
                          Prompt
                        </div>
                        <pre
                          style={{
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            margin: 0,
                            color: "var(--text-2)",
                            lineHeight: 1.4,
                            fontFamily: "monospace",
                            fontSize: "0.6875rem",
                          }}
                        >
                          {evt.input_prompt}
                        </pre>
                      </div>
                    )}
                    {evt.image_url && (
                      <div>
                        <div
                          style={{
                            color: "var(--muted)",
                            marginBottom: 4,
                            fontWeight: 600,
                          }}
                        >
                          Output Image
                        </div>
                        <img
                          src={evt.image_url}
                          alt="Output"
                          onClick={() => setLightbox(evt.image_url!)}
                          style={{
                            maxWidth: "100%",
                            maxHeight: 160,
                            borderRadius: 6,
                            cursor: "pointer",
                            border: "1px solid var(--border)",
                          }}
                        />
                      </div>
                    )}
                    {evt.output_text && (
                      <div>
                        <div
                          style={{
                            color: "var(--muted)",
                            marginBottom: 4,
                            fontWeight: 600,
                          }}
                        >
                          Output
                        </div>
                        <pre
                          style={{
                            whiteSpace: "pre-wrap",
                            wordBreak: "break-word",
                            margin: 0,
                            color: "var(--text-2)",
                            lineHeight: 1.4,
                            fontFamily: "monospace",
                            fontSize: "0.6875rem",
                          }}
                        >
                          {evt.output_text.length > 2000
                            ? `${evt.output_text.slice(0, 2000)}\u2026`
                            : evt.output_text}
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

      {lastEvent && !lastEvent.duration_ms && lastEvent.step !== "started" && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 12px",
            borderRadius: 8,
            background: "rgba(250,249,247,0.7)",
            backdropFilter: "blur(8px)",
            border: "1px solid rgba(236,230,219,0.5)",
            width: "100%",
            fontSize: "0.8125rem",
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "var(--accent)",
              flexShrink: 0,
              animation: "progressPulse 1.5s ease-in-out infinite",
            }}
          />
          <span
            style={{ color: "var(--text)", animation: "progressPulse 2s ease-in-out infinite" }}
          >
            {STEP_LABELS[lastEvent.step] || lastEvent.message || lastEvent.step.replace(/_/g, " ")}
            ...
          </span>
        </div>
      )}

      {lightbox && (
        <div
          style={{
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
          }}
          onClick={() => setLightbox(null)}
        >
          <img
            src={lightbox}
            alt="Preview"
            style={{
              maxWidth: "90vw",
              maxHeight: "80vh",
              borderRadius: 6,
              border: "2px solid rgba(255,255,255,0.2)",
            }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
}
