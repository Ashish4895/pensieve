import { newId } from "../../lib/id";

export interface ByokSettings {
  provider: string;
  apiKey: string;
  model: string;
}

export const DEFAULT_MODELS: Record<string, string> = {
  gemini: "gemini-2.5-flash",
  openai: "gpt-4o-mini",
  openrouter: "openai/gpt-4o-mini",
};

export function loadByok(): ByokSettings {
  const provider = sessionStorage.getItem("byok_provider") || "gemini";
  return {
    provider,
    apiKey: sessionStorage.getItem("byok_api_key") || "",
    model:
      sessionStorage.getItem("byok_model") ||
      DEFAULT_MODELS[provider] ||
      "",
  };
}

export function saveByok(settings: ByokSettings) {
  sessionStorage.setItem("byok_provider", settings.provider);
  sessionStorage.setItem("byok_api_key", settings.apiKey);
  sessionStorage.setItem("byok_model", settings.model);
}

const BYOK_KEYS = [
  "byok_provider",
  "byok_api_key",
  "byok_model",
  "byok_session_id",
] as const;

export function clearByok() {
  for (const key of BYOK_KEYS) {
    sessionStorage.removeItem(key);
  }
}

export function getSessionId(): string {
  const existing = sessionStorage.getItem("byok_session_id");
  if (existing) return existing;

  const sessionId = newId();
  sessionStorage.setItem("byok_session_id", sessionId);
  return sessionId;
}
