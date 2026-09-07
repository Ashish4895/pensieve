export function resolveWsBaseUrl(): string {
  const configured = import.meta.env.VITE_WS_BASE_URL as string | undefined;
  if (configured && configured.trim()) {
    return configured.replace(/\/$/, "");
  }
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}`;
}

export function createChatSocket(
  access: string,
  baseWsUrl: string = resolveWsBaseUrl(),
): WebSocket {
  const url = new URL("ws/v1/chat/", `${baseWsUrl}/`);
  url.searchParams.set("token", access);
  return new WebSocket(url.toString());
}

export function sendPing(socket: WebSocket): void {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "ping" }));
  }
}
