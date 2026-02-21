"use client";

import { use, useState } from "react";
import { usePolling } from "@/hooks/use-polling";
import { RoomViewer } from "@/components/room-viewer";
import { FurnitureSidebar } from "@/components/furniture-sidebar";
import { FloorplanUpload } from "@/components/floorplan-upload";
import { StatusBar } from "@/components/status-bar";
import { runPipeline } from "@/lib/backend";

export default function SessionPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { session, error, refetch } = usePolling(id);
  const [pipelineStarting, setPipelineStarting] = useState(false);

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
        <div
          style={{
            width: "48px",
            height: "48px",
            border: "3px solid rgba(26,26,56,0.08)",
            borderTopColor: "#1a1a38",
            borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
          }}
        />
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

  const status = session.status;
  const roomData = session.room_data?.rooms?.[0];
  const placements = session.placements?.placements;
  const hasFurniture = session.furniture_list && session.furniture_list.length > 0;
  const isFailed = status.endsWith("_failed");
  const isProcessing = [
    "analyzing_floorplan",
    "searching",
    "sourcing",
    "placing",
    "placing_furniture",
  ].includes(status);
  const isComplete = status === "complete" || status === "placement_ready";
  const canRunPipeline = status === "floorplan_ready" || status === "consulting";

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
      <StatusBar currentPhase={status} />

      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Main content area */}
        <div style={{ flex: 1, position: "relative" }}>
          {/* pending -- show floorplan upload */}
          {status === "pending" && (
            <div style={{ animation: "fadeUp 0.6s ease-out" }}>
              <FloorplanUpload sessionId={id} onUploaded={refetch} />
            </div>
          )}

          {/* consulting -- preferences saved, show upload */}
          {status === "consulting" && (
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                height: "100%",
                animation: "fadeUp 0.6s ease-out",
              }}
            >
              <FloorplanUpload sessionId={id} onUploaded={refetch} />
            </div>
          )}

          {/* analyzing_floorplan -- processing floorplan */}
          {status === "analyzing_floorplan" && (
            <CenterMessage>
              <PipelineSpinner
                label="Analyzing floorplan"
                sublabel="AI is identifying room dimensions, doors, and windows..."
              />
            </CenterMessage>
          )}

          {/* floorplan_ready -- show run pipeline button */}
          {canRunPipeline && status === "floorplan_ready" && (
            <CenterMessage>
              <div
                style={{
                  width: "56px",
                  height: "56px",
                  borderRadius: "50%",
                  background: "rgba(34,197,94,0.08)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "1.25rem",
                  animation: "fadeInScale 0.4s ease-out",
                }}
              >
                <svg
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="var(--success)"
                  strokeWidth="2"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <p
                style={{
                  fontSize: "1.25rem",
                  fontWeight: 600,
                  marginBottom: "0.5rem",
                  letterSpacing: "0.01em",
                }}
              >
                Floorplan Analyzed
              </p>
              <p style={{ color: "var(--muted)", marginBottom: "2rem", fontSize: "0.9375rem" }}>
                {roomData
                  ? `${roomData.name} — ${roomData.width_m}m x ${roomData.length_m}m (${roomData.area_sqm}m\u00B2)`
                  : "Room data ready"}
              </p>
              <button
                type="button"
                onClick={handleRunPipeline}
                disabled={pipelineStarting}
                style={{
                  background: "#1a1a38",
                  color: "#fff",
                  padding: "12px 32px",
                  borderRadius: "var(--radius-full)",
                  fontWeight: 500,
                  fontSize: "1rem",
                  letterSpacing: "0.02em",
                  cursor: pipelineStarting ? "not-allowed" : "pointer",
                  opacity: pipelineStarting ? 0.6 : 1,
                  transition: "all var(--transition-slow)",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.5rem",
                }}
              >
                {pipelineStarting && (
                  <span
                    style={{
                      width: "14px",
                      height: "14px",
                      border: "2px solid rgba(255,255,255,0.3)",
                      borderTopColor: "#fff",
                      borderRadius: "50%",
                      animation: "spin 0.6s linear infinite",
                      display: "inline-block",
                    }}
                  />
                )}
                {pipelineStarting ? "Starting..." : "Run Design Pipeline"}
              </button>
            </CenterMessage>
          )}

          {/* processing states -- show spinner with phase info */}
          {isProcessing && status !== "analyzing_floorplan" && (
            <CenterMessage>
              <PipelineSpinner
                label={
                  status === "searching"
                    ? "Searching for furniture"
                    : status === "sourcing"
                      ? "Sourcing 3D models"
                      : "Computing placement"
                }
                sublabel={
                  status === "searching"
                    ? "AI is browsing retailers for the perfect pieces..."
                    : status === "sourcing"
                      ? "Downloading and converting 3D furniture models..."
                      : "Calculating optimal furniture arrangement..."
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
                {status.replace(/_/g, " ").replace("failed", "Failed")}
              </p>
              <p style={{ color: "var(--muted)", marginBottom: "2rem", fontSize: "0.9375rem" }}>
                Something went wrong. You can try again.
              </p>
              <button
                type="button"
                onClick={handleRetry}
                style={{
                  background: "#1a1a38",
                  color: "#fff",
                  padding: "12px 28px",
                  borderRadius: "var(--radius-full)",
                  fontWeight: 500,
                  cursor: "pointer",
                  transition: "all var(--transition-slow)",
                }}
              >
                Retry Pipeline
              </button>
            </CenterMessage>
          )}

          {/* complete -- show 3D viewer */}
          {isComplete && (
            <div style={{ width: "100%", height: "100%", animation: "fadeUp 0.6s ease-out" }}>
              <RoomViewer
                roomData={roomData}
                roomGlbUrl={session.room_glb_url}
                placements={placements}
                furnitureItems={session.furniture_list}
              />
            </div>
          )}

          {/* furniture_found */}
          {status === "furniture_found" && (
            <CenterMessage>
              <PipelineSpinner label="Furniture found" sublabel="Continuing pipeline..." />
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

function PipelineSpinner({ label, sublabel }: { label: string; sublabel: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1.5rem" }}>
      {/* Simple elegant spinner */}
      <div
        style={{
          width: "48px",
          height: "48px",
          border: "3px solid rgba(26,26,56,0.08)",
          borderTopColor: "#1a1a38",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <div>
        <p
          style={{
            fontSize: "1.125rem",
            fontWeight: 600,
            marginBottom: "0.5rem",
            letterSpacing: "0.01em",
          }}
        >
          {label}
        </p>
        <p
          style={{
            color: "var(--muted)",
            fontSize: "0.875rem",
            animation: "progressPulse 2s ease-in-out infinite",
          }}
        >
          {sublabel}
        </p>
      </div>
    </div>
  );
}
