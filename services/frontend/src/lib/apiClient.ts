import { getCookie } from "./csrf";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data: T;
  errors: unknown;
}

const unsafeMethods = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export async function apiClient<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const { store } = await import("../app/store");
  const access = store.getState().auth.access;
  const method = (init.method ?? "GET").toUpperCase();

  if (access) headers.set("Authorization", `Bearer ${access}`);
  if (unsafeMethods.has(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers.set("X-CSRFToken", csrfToken);
  }

  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  const envelope = (await response.json()) as ApiEnvelope<T>;

  if (!response.ok || !envelope.success) {
    throw new Error(envelope.message || `Request failed (${response.status})`);
  }

  return envelope.data;
}
