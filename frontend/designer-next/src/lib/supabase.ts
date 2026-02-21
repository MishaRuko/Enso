import { createClient } from "@supabase/supabase-js";
import type { DesignJob, DesignSession } from "./types";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
);

export { supabase };

// --- Design Sessions ---

export async function getSessionFromDb(id: string): Promise<DesignSession | null> {
  const { data, error } = await supabase.from("design_sessions").select("*").eq("id", id).single();

  if (error) {
    console.error("[supabase] getSession failed:", error.message);
    return null;
  }
  return data;
}

// --- Design Jobs ---

export async function getJobFromDb(id: string): Promise<DesignJob | null> {
  const { data, error } = await supabase.from("design_jobs").select("*").eq("id", id).single();

  if (error) {
    console.error("[supabase] getJob failed:", error.message);
    return null;
  }
  return data;
}

export async function getJobsForSession(sessionId: string): Promise<DesignJob[]> {
  const { data, error } = await supabase
    .from("design_jobs")
    .select("*")
    .eq("session_id", sessionId)
    .order("created_at", { ascending: false });

  if (error) {
    console.error("[supabase] getJobsForSession failed:", error.message);
    return [];
  }
  return data ?? [];
}
