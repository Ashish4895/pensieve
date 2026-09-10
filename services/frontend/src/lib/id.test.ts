import { describe, expect, it, vi } from "vitest";

import { newId } from "./id";

describe("newId", () => {
  it("falls back when randomUUID is unavailable (http non-secure context)", () => {
    vi.stubGlobal("crypto", {
      randomUUID: undefined,
      getRandomValues: crypto.getRandomValues.bind(crypto),
    });

    const id = newId();
    expect(id).toMatch(/^id-/);
  });
});
