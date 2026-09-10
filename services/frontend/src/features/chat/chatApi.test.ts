import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "../../lib/accessToken";
import { chatApi } from "./chatApi";

describe("chatApi", () => {
  beforeEach(() => {
    sessionStorage.clear();
    setAccessToken("access-tok");
    sessionStorage.setItem("byok_provider", "gemini");
    sessionStorage.setItem("byok_api_key", "AIza-test\nkey");
    sessionStorage.setItem("byok_model", "gemini-2.5-flash");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          message: "ok",
          data: { response: "hi", sources: [], session_id: "s" },
          errors: null,
        }),
      }),
    );
  });

  it("strips invalid header characters and calls fetch", async () => {
    await chatApi.sendMessage({ message: "hello" });

    expect(fetch).toHaveBeenCalledOnce();
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/chat/");
    const headers = new Headers(init?.headers);
    expect(headers.get("X-API-Key")).toBe("AIza-testkey");
    expect(headers.get("Authorization")).toBe("Bearer access-tok");
  });
});
