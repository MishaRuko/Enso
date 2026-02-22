/**
 * REST API client for the HomeDesigner backend.
 */

import type { DesignJob, DesignSession, PlacementResult } from "./types";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

// --- Sessions ---

export function createSession(): Promise<{ session_id: string }> {
  return apiFetch("/api/sessions", { method: "POST" });
}

export function getSession(id: string): Promise<DesignSession> {
  return apiFetch(`/api/sessions/${id}`);
}

export async function listSessions(): Promise<DesignSession[]> {
  const data = await apiFetch<DesignSession[] | { sessions: DesignSession[] }>("/api/sessions");
  return Array.isArray(data) ? data : data.sessions;
}

export async function listDemoSessions(): Promise<DesignSession[]> {
  const data = await apiFetch<DesignSession[] | { sessions: DesignSession[] }>(
    "/api/demo-sessions",
  );
  return Array.isArray(data) ? data : data.sessions;
}

export function toggleDemo(sessionId: string): Promise<{ demo_selected: boolean }> {
  return apiFetch(`/api/sessions/${sessionId}/demo`, { method: "PATCH" });
}

// --- Floorplan ---

export function uploadFloorplan(
  sessionId: string,
  file: File,
  mode: "fast" | "pro" = "fast",
): Promise<{ room_data: unknown }> {
  const formData = new FormData();
  formData.append("file", file);
  return apiFetch(`/api/sessions/${sessionId}/floorplan?mode=${mode}`, {
    method: "POST",
    body: formData,
  });
}

// --- Pipeline ---

export function runPipeline(
  sessionId: string,
  mode: "fast" | "pro" = "fast",
): Promise<{ status: string; mode: string }> {
  return apiFetch(`/api/sessions/${sessionId}/pipeline?mode=${mode}`, { method: "POST" });
}

// --- Jobs ---

export function getJob(jobId: string): Promise<DesignJob> {
  return apiFetch(`/api/jobs/${jobId}`);
}

export function listSessionJobs(sessionId: string): Promise<DesignJob[]> {
  return apiFetch(`/api/sessions/${sessionId}/jobs`);
}

// --- Placements ---

export function savePlacements(
  sessionId: string,
  placements: PlacementResult,
): Promise<{ status: string }> {
  return apiFetch(`/api/sessions/${sessionId}/placements`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(placements),
  });
}

// --- Cancel ---

export function cancelSession(sessionId: string): Promise<{ status: string }> {
  return apiFetch(`/api/sessions/${sessionId}/cancel`, { method: "POST" });
}

// --- Stubs for frontend components (endpoints not yet wired) ---

export function selectFurniture(
  sessionId: string,
  itemIds: string[],
): Promise<{ selected: number; total: number }> {
  return apiFetch(`/api/sessions/${sessionId}/select-furniture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

export function createCheckout(sessionId: string): Promise<{ payment_link: string }> {
  return apiFetch(`/api/sessions/${sessionId}/checkout`, { method: "POST" });
}

export function generateMiroBoard(
  sessionId: string,
): Promise<{ miro_board_url: string; board_id: string }> {
  return apiFetch(`/api/sessions/${sessionId}/miro`, { method: "POST" });
}

export function addMiroItem(
  sessionId: string,
  boardId: string,
  label: string,
  value: string,
): Promise<{ ok: boolean; item_id: string }> {
  return apiFetch(`/api/sessions/${sessionId}/miro/item`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ board_id: boardId, label, value }),
  });
}

// --- Voice Intake ---

export function createVoiceSession(): Promise<{ session_id: string }> {
  return apiFetch("/backend-session/new", { method: "POST" });
}

export function getVoiceSession(sessionId: string): Promise<any> {
  return apiFetch(`/backend-session/${sessionId}`);
}

export function getVoiceSessionToken(sessionId: string): Promise<any> {
  return apiFetch(`/voice/session_token?session_id=${sessionId}`, { method: "POST" });
}

export function voiceIntakeTurn(sessionId: string, userText: string): Promise<any> {
  return apiFetch("/voice_intake/turn", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, user_text: userText }),
  });
}

export function voiceIntakeFinalize(sessionId: string): Promise<any> {
  return apiFetch("/voice_intake/finalize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
}
