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
import type { DesignJob, FurniturePlacement, TraceEvent } from "@/lib/types";

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
  const isComplete = currentStatus === "complete" || currentStatus === "placement_ready";
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

  function handleApprove(selectedIds: string[]) {
    console.log("Approved furniture:", selectedIds);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      <StatusBar currentPhase={currentStatus} />

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
        </div>

        {/* Sidebar -- show when complete with furniture */}
        {isComplete && hasFurniture && (
          <div
            style={{
              width: "340px",
              flexShrink: 0,
              animation: "slideInRight 0.4s ease-out",
            }}
          >
            <FurnitureSidebar
              sessionId={id}
              items={session.furniture_list}
              onApprove={handleApprove}
            />
          </div>
        )}
      </div>
    </div>
  );
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
  searching_ikea: "Searching IKEA catalog",
  search_done: "Search complete",
  gemini_attempt_1: "Computing placement",
  gemini_response_1: "Placement computed",
  error: "Error",
};

function PipelineProgress({ sessionId, phase }: { sessionId: string; phase: string }) {
  const [jobs, setJobs] = useState<DesignJob[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());
  const [lightbox, setLightbox] = useState<string | null>(null);

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

  const completedSteps = allEvents.filter((e) => e.duration_ms != null && e.step !== "started");
  const lastEvent = allEvents[allEvents.length - 1];
  const lastImageEvt = [...allEvents].reverse().find((e) => e.image_url || e.output_image);
  const lastImage = lastImageEvt?.image_url || lastImageEvt?.output_image;

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

      {completedSteps.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%" }}>
          {completedSteps.map((evt, i) => (
            <div
              key={`${evt.step}-${i}`}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: 8,
                background: "rgba(250,249,247,0.7)",
                backdropFilter: "blur(8px)",
                border: "1px solid rgba(236,230,219,0.5)",
                animation: "fadeUp 0.3s ease-out",
                fontSize: "0.8125rem",
              }}
            >
              <span style={{ color: "var(--sage)", fontSize: "0.875rem", flexShrink: 0 }}>
                {"\u2713"}
              </span>
              <span style={{ color: "var(--text)", flex: 1 }}>
                {STEP_LABELS[evt.step] || evt.message || evt.step.replace(/_/g, " ")}
              </span>
              {evt.duration_ms != null && (
                <span style={{ color: "var(--muted)", fontSize: "0.75rem", flexShrink: 0 }}>
                  {evt.duration_ms < 1000
                    ? `${evt.duration_ms.toFixed(0)}ms`
                    : `${(evt.duration_ms / 1000).toFixed(1)}s`}
                </span>
              )}
            </div>
          ))}
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
