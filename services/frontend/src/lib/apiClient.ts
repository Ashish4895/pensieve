import { getAccessToken } from "./accessToken";
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
  const access = getAccessToken();
  const method = (init.method ?? "GET").toUpperCase();

  if (access) headers.set("Authorization", `Bearer ${access}`);
  if (unsafeMethods.has(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers.set("X-CSRFToken", csrfToken);
  }

  // Don't forward caller AbortSignal twice via spread after we may wrap it.
  const { signal: callerSignal, ...rest } = init;

  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      ...rest,
      credentials: "include",
      headers,
      signal: callerSignal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "TimeoutError") {
      throw new Error("Request timed out. Try again.");
    }
    if (error instanceof Error && error.name === "AbortError") {
      throw new Error("Request timed out. Try again.");
    }
    throw error;
  }

  const envelope = (await response.json()) as ApiEnvelope<T>;

  if (!response.ok || !envelope.success) {
    throw new Error(envelope.message || `Request failed (${response.status})`);
  }

  return envelope.data;
}
