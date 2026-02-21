"use client";

import { useCallback, useState } from "react";
import { uploadFloorplan } from "@/lib/backend";

interface FloorplanUploadProps {
  sessionId: string;
  onUploaded?: () => void;
}

export function FloorplanUpload({ sessionId, onUploaded }: FloorplanUploadProps) {
  const [dragging, setDragging] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.type.startsWith("image/")) {
        setError("Please upload an image file");
        return;
      }

      setPreview(URL.createObjectURL(file));
      setUploading(true);
      setError(null);

      try {
        await uploadFloorplan(sessionId, file);
        onUploaded?.();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setUploading(false);
      }
    },
    [sessionId, onUploaded],
  );

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: "100%",
        padding: "2rem",
        animation: "fadeUp 0.6s ease-out",
      }}
    >
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        style={{
          width: "100%",
          maxWidth: "520px",
          aspectRatio: "4 / 3",
          border: `2px dashed ${dragging ? "#1a1a38" : "rgba(26,26,56,0.12)"}`,
          borderRadius: "var(--radius-xl)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "1rem",
          padding: "2rem",
          transition: "all var(--transition-slow)",
          background: dragging ? "rgba(26,26,56,0.03)" : "rgba(255,255,255,0.95)",
          backdropFilter: "blur(20px)",
          boxShadow: "var(--shadow-lg)",
          cursor: "pointer",
          position: "relative",
          overflow: "hidden",
        }}
        onClick={() => document.getElementById("floorplan-input")?.click()}
      >
        {preview ? (
          <img
            src={preview}
            alt="Floorplan preview"
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              objectFit: "contain",
              opacity: uploading ? 0.4 : 1,
              transition: "opacity var(--transition-base)",
            }}
          />
        ) : (
          <>
            <div
              style={{
                width: "64px",
                height: "64px",
                borderRadius: "50%",
                background: "rgba(26,26,56,0.05)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                transition: "transform var(--transition-base)",
                transform: dragging ? "scale(1.1)" : "scale(1)",
              }}
            >
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#1a1a38"
                strokeWidth="1.5"
                strokeLinecap="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  fontWeight: 600,
                  fontSize: "0.9375rem",
                  marginBottom: "0.25rem",
                  letterSpacing: "0.01em",
                }}
              >
                {dragging ? "Drop your floorplan here" : "Upload floorplan image"}
              </div>
              <div style={{ fontSize: "0.8125rem", color: "var(--muted)" }}>
                Drag and drop or click to browse
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--muted)",
                  opacity: 0.6,
                  marginTop: "0.5rem",
                }}
              >
                PNG, JPG, or SVG
              </div>
            </div>
          </>
        )}

        {uploading && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              gap: "1rem",
              background: "rgba(255,255,255,0.85)",
              backdropFilter: "blur(8px)",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                border: "3px solid rgba(26,26,56,0.1)",
                borderTopColor: "#1a1a38",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }}
            />
            <span
              style={{
                color: "#1a1a38",
                fontWeight: 500,
                fontSize: "0.875rem",
                letterSpacing: "0.02em",
                animation: "progressPulse 2s ease-in-out infinite",
              }}
            >
              Uploading and analyzing...
            </span>
          </div>
        )}

        <input
          id="floorplan-input"
          type="file"
          accept="image/*"
          onChange={handleChange}
          style={{ display: "none" }}
        />
      </div>

      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "0.625rem 1rem",
            borderRadius: "var(--radius-full)",
            background: "var(--error-subtle)",
            border: "1px solid rgba(239,68,68,0.15)",
            color: "var(--error)",
            fontSize: "0.8125rem",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            animation: "fadeUp 0.3s ease-out",
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          {error}
        </div>
      )}
    </div>
  );
}
