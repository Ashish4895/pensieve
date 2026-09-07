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

function byokHeaders() {
  const { provider, apiKey, model } = loadByok();
  return {
    "Content-Type": "application/json",
    "X-Provider": provider,
    "X-API-Key": apiKey,
    "X-Model": model,
  };
}

export const chatApi = {
  sendMessage: (payload: { message: string }) =>
    apiClient<ChatResponse>("/chat/", {
      method: "POST",
      headers: byokHeaders(),
      body: JSON.stringify({ ...payload, session_id: getSessionId() }),
    }),
  clearSession: () =>
    apiClient<{ deleted: number; session_id: string }>("/chat/clear/", {
      method: "POST",
      headers: byokHeaders(),
      body: JSON.stringify({ session_id: getSessionId() }),
    }),
};
