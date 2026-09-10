import { apiClient } from "../../lib/apiClient";
import { getSessionId, loadByok } from "./byok";

export interface ChatSource {
  source?: string;
  score?: number;
}

export interface ChatResponse {
  response: string;
  sources: ChatSource[];
  session_id: string;
}

/** Header values must be byte-string; pasted keys sometimes include newlines. */
function headerValue(value: string) {
  return value.replace(/[^\x20-\x7E]/g, "").trim();
}

function byokHeaders() {
  const { provider, apiKey, model } = loadByok();
  const key = headerValue(apiKey);
  if (!key) {
    throw new Error("Add your API key in Chat settings.");
  }
  return {
    "Content-Type": "application/json",
    "X-Provider": headerValue(provider) || "gemini",
    "X-API-Key": key,
    "X-Model": headerValue(model),
  };
}

const CHAT_TIMEOUT_MS = 90_000;

function chatSignal() {
  if (typeof AbortSignal !== "undefined" && "timeout" in AbortSignal) {
    return AbortSignal.timeout(CHAT_TIMEOUT_MS);
  }
  return undefined;
}

export const chatApi = {
  sendMessage: (payload: { message: string }) =>
    apiClient<ChatResponse>("/chat/", {
      method: "POST",
      headers: byokHeaders(),
      body: JSON.stringify({ ...payload, session_id: getSessionId() }),
      signal: chatSignal(),
    }),
  clearSession: () =>
    apiClient<{ deleted: number; session_id: string }>("/chat/clear/", {
      method: "POST",
      headers: byokHeaders(),
      body: JSON.stringify({ session_id: getSessionId() }),
      signal: chatSignal(),
    }),
};
