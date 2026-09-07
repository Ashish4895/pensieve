import type { NotificationItem } from "./notificationsApi";

interface ConnectNotificationStreamOptions {
  access: string;
  lastEventId?: string;
  onEvent: (notification: NotificationItem, lastEventId: string) => void;
  onError: (error: unknown) => void;
  onOpen?: () => void;
}

export function parseNotificationEventBlock(
  block: string,
): NotificationItem {
  const dataLines = block
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart());
  const data = dataLines.length ? dataLines.join("\n") : block;

  return JSON.parse(data) as NotificationItem;
}

export function connectNotificationStream({
  access,
  lastEventId = "",
  onEvent,
  onError,
  onOpen,
}: ConnectNotificationStreamOptions) {
  const query = new URLSearchParams({ access });
  const source = new EventSource(
    `/api/v1/notifications/stream/?${query.toString()}`,
  );
  let cursor = Number(lastEventId) || 0;

  source.addEventListener("notification", (event) => {
    const message = event as MessageEvent<string>;
    const eventId = Number(message.lastEventId) || 0;
    if (eventId && eventId <= cursor) return;

    try {
      const notification = parseNotificationEventBlock(message.data);
      cursor = eventId || notification.id;
      onEvent(notification, String(cursor));
    } catch (error) {
      onError(error);
    }
  });

  // Native EventSource reconnects automatically and sends Last-Event-ID.
  source.onopen = () => onOpen?.();
  source.onerror = onError;

  return { close: () => source.close() };
}
