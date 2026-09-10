import { configureStore } from "@reduxjs/toolkit";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "../../lib/accessToken";
import authReducer, { login } from "./authSlice";

describe("authSlice", () => {
  beforeEach(() => {
    setAccessToken(null);
    document.cookie = "csrftoken=csrf%20token";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          success: true,
          message: "ok",
          data: {
            access: "tok",
            user: { id: 1, email: "a@b.com", role: "user" },
          },
          errors: null,
        }),
      }),
    );
  });

  it("stores access and user on login", async () => {
    const store = configureStore({ reducer: { auth: authReducer } });
    await store.dispatch(
      login({ email: "a@b.com", password: "StrongPass123!" }),
    );

    const state = store.getState().auth;
    expect(state.access).toBe("tok");
    expect(state.user?.email).toBe("a@b.com");

    const { getAccessToken } = await import("../../lib/accessToken");
    expect(getAccessToken()).toBe("tok");

    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/auth/login/");
    expect(init?.credentials).toBe("include");
    expect(new Headers(init?.headers).get("X-CSRFToken")).toBe("csrf token");
  });

  it("rejects an unsuccessful API envelope", async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        success: false,
        message: "Invalid credentials",
        data: null,
        errors: { detail: "Invalid credentials" },
      }),
    } as Response);
    const store = configureStore({ reducer: { auth: authReducer } });

    const action = await store.dispatch(
      login({ email: "a@b.com", password: "wrong" }),
    );

    expect(action.type).toBe("auth/login/rejected");
    expect(store.getState().auth.status).toBe("failed");
  });
});
