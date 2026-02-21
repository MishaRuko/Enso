"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getSession } from "@/lib/backend";
import type { DesignSession } from "@/lib/types";

const POLL_INTERVAL_MS = 2000;

const TERMINAL_STATUSES = new Set([
  "pending",
  "floorplan_ready",
  "floorplan_failed",
  "complete",
  "searching_failed",
  "sourcing_failed",
  "placing_failed",
  "placement_failed",
  "placement_ready",
]);

export function usePolling(sessionId: string) {
  const [session, setSession] = useState<DesignSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchSession = useCallback(async () => {
    try {
      const data = await getSession(sessionId);
      setSession(data);
      setError(null);

      // Keep polling while status is in a processing state (non-terminal)
      if (!TERMINAL_STATUSES.has(data.status)) {
        timerRef.current = setTimeout(fetchSession, POLL_INTERVAL_MS);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch session");
      // Retry on error too
      timerRef.current = setTimeout(fetchSession, POLL_INTERVAL_MS);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSession();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [fetchSession]);

  const refetch = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    fetchSession();
  }, [fetchSession]);

  return { session, error, refetch };
}
