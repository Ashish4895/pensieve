import { beforeEach, describe, expect, it } from "vitest";

import { getSessionId, loadByok, saveByok } from "./byok";

describe("BYOK session storage", () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
  });

  it("round-trips settings without writing the API key to localStorage", () => {
    saveByok({
      provider: "gemini",
      apiKey: "sk-test",
      model: "gemini-2.5-flash",
    });

    expect(loadByok()).toEqual({
      provider: "gemini",
      apiKey: "sk-test",
      model: "gemini-2.5-flash",
    });
    expect(localStorage.getItem("byok_api_key")).toBeNull();
  });

  it("creates and reuses a session id", () => {
    const sessionId = getSessionId();

    expect(sessionId).toBeTruthy();
    expect(getSessionId()).toBe(sessionId);
    expect(sessionStorage.getItem("byok_session_id")).toBe(sessionId);
  });
});
