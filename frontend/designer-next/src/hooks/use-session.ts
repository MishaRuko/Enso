"use client";

import { useCallback, useEffect, useState } from "react";
import { getSession } from "@/lib/backend";
import type { DesignSession } from "@/lib/types";

/**
 * Fetch a design session once (no polling).
 * Use `refetch()` to manually refresh.
 */
export function useSession(sessionId: string) {
  const [session, setSession] = useState<DesignSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSession = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getSession(sessionId);
      setSession(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch session");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  return { session, loading, error, refetch: fetchSession };
}
