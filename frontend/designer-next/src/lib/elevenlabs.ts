/**
 * ElevenLabs realtime client for voice-based intake conversation.
 *
 * Supports:
 * 1. Realtime voice (when ElevenLabs config available)
 * 2. Fallback to text-based API (voice_intake/turn endpoint)
 */

import {
  getVoiceSessionToken,
  voiceIntakeTurn,
  voiceIntakeFinalize,
  getVoiceSession,
} from "./backend";

export interface ElevenLabsConfig {
  agent_id: string;
  backend_url: string;
  tool_endpoint_base: string;
  session_id: string;
  token?: string;
}

export interface ConversationCallbacks {
  onTranscript?: (text: string) => void;
  onAssistantText?: (text: string) => void;
  onMiroReady?: (miroUrl: string) => void;
  onError?: (error: Error) => void;
}

let currentSessionId: string | null = null;
let currentConfig: ElevenLabsConfig | null = null;
let currentCallbacks: ConversationCallbacks | null = null;

/**
 * Start a voice conversation using ElevenLabs realtime or fallback to text.
 */
export async function startCall(
  sessionId: string,
  callbacks: ConversationCallbacks = {}
): Promise<void> {
  currentSessionId = sessionId;
  currentCallbacks = callbacks;

  try {
    // Fetch session config from backend
    const config = await getVoiceSessionToken(sessionId);

    currentConfig = config as ElevenLabsConfig;

    // TODO: If full SDK support, initialize ElevenLabs realtime here
    // For now, log that we have the config
    console.log("ElevenLabs realtime config ready:", currentConfig);

    // In a real implementation:
    // - Initialize ElevenLabs SDK with currentConfig
    // - Set up WebSocket connection
    // - Register tool handlers for /tool/* endpoints
    // - Forward transcripts/responses to callbacks

    // For demo: text-based fallback is ready
    console.log("Voice call started (text fallback mode)");
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    console.error("Failed to start call:", err);
    callbacks.onError?.(err);
  }
}

/**
 * Stop the current voice call.
 */
export async function stopCall(): Promise<void> {
  currentSessionId = null;
  currentConfig = null;
  currentCallbacks = null;
  console.log("Voice call stopped");
}

/**
 * Process one turn of conversation (user text input).
 * Call this when user submits text via UI.
 */
export async function processTurn(
  userText: string,
  callbacks?: ConversationCallbacks
): Promise<{
  assistantText: string;
  done: boolean;
  missingFields: string[];
}> {
  if (!currentSessionId) {
    throw new Error("No active session");
  }

  if (callbacks) {
    currentCallbacks = callbacks;
  }

  try {
    // Use text-based endpoint
    const response = await voiceIntakeTurn(currentSessionId, userText);

    const {
      assistant_text: assistantText,
      done,
      missing_fields: missingFields,
    } = response;

    currentCallbacks?.onTranscript?.(userText);
    currentCallbacks?.onAssistantText?.(assistantText);

    return {
      assistantText,
      done,
      missingFields,
    };
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    console.error("Turn failed:", err);
    currentCallbacks?.onError?.(err);
    throw err;
  }
}

/**
 * Finalize the session and get Miro board URL.
 */
export async function finalizeBrief(): Promise<string> {
  if (!currentSessionId) {
    throw new Error("No active session");
  }

  try {
    const response = await voiceIntakeFinalize(currentSessionId);

    const { miro_board_url: miroUrl } = response;
    currentCallbacks?.onMiroReady?.(miroUrl);
    return miroUrl;
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    console.error("Finalize failed:", err);
    currentCallbacks?.onError?.(err);
    throw err;
  }
}

/**
 * Get current session status for debugging.
 */
export async function getSessionStatus(): Promise<any> {
  if (!currentSessionId) {
    throw new Error("No active session");
  }

  try {
    return await getVoiceSession(currentSessionId);
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error));
    console.error("Failed to get session status:", err);
    throw err;
  }
}
