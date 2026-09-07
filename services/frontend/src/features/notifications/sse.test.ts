import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  connectNotificationStream,
  parseNotificationEventBlock,
} from "./sse";

class MockEventSource {
  static instances: MockEventSource[] = [];

  readonly listeners = new Map<string, EventListener>();
  readonly url: string;
  onerror: ((event: Event) => void) | null = null;
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListener) {
    this.listeners.set(type, listener);
  }

  emit(type: string, event: Event) {
    this.listeners.get(type)?.(event);
  }
}

describe("notification SSE", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    vi.stubGlobal("EventSource", MockEventSource);
  });

  it("parses multiline notification event blocks", () => {
    expect(
      parseNotificationEventBlock(
        'id: 7\nevent: notification\ndata: {"id":7,\ndata: "title":"Ready"}\n\n',
      ),
    ).toEqual({ id: 7, title: "Ready" });
  });

  it("connects with the access token and forwards notification events", () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    const connection = connectNotificationStream({
      access: "token with spaces",
      lastEventId: "6",
      onEvent,
      onError,
    });
    const source = MockEventSource.instances[0];

    expect(source.url).toBe(
      "/api/v1/notifications/stream/?access=token+with+spaces",
    );

    source.emit(
      "notification",
      new MessageEvent("notification", {
        data: '{"id":7,"title":"Ready","body":"","kind":"info","created_at":"2026-09-07T09:00:00Z","read_at":null}',
        lastEventId: "7",
      }),
    );
    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({ id: 7, title: "Ready" }),
      "7",
    );

    source.onerror?.(new Event("error"));
    expect(onError).toHaveBeenCalledOnce();

    connection.close();
    expect(source.close).toHaveBeenCalledOnce();
  });

  it("ignores replayed events at or before the supplied event id", () => {
    const onEvent = vi.fn();
    connectNotificationStream({
      access: "token",
      lastEventId: "7",
      onEvent,
      onError: vi.fn(),
    });

    MockEventSource.instances[0].emit(
      "notification",
      new MessageEvent("notification", {
        data: '{"id":7}',
        lastEventId: "7",
      }),
    );

    expect(onEvent).not.toHaveBeenCalled();
  });
});
