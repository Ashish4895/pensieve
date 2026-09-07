import { afterEach, describe, expect, it, vi } from "vitest";

import { createChatSocket, resolveWsBaseUrl } from "./wsClient";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("wsClient", () => {
  it("builds an authenticated chat socket URL", () => {
    const sockets: Array<{ url: string }> = [];
    vi.stubGlobal(
      "WebSocket",
      class {
        readyState = 0;
        url: string;
        constructor(url: string) {
          this.url = url;
          sockets.push(this);
        }
        send() {}
        close() {}
      },
    );

    createChatSocket("tok-123", "ws://127.0.0.1:8001");
    expect(sockets[0]?.url).toBe("ws://127.0.0.1:8001/ws/v1/chat/?token=tok-123");
  });

  it("defaults ws base to current host", () => {
    expect(resolveWsBaseUrl()).toMatch(/^wss?:\/\//);
  });
});
