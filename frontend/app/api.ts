/** Requests are bounded; no retries that could duplicate evidence or provider calls. */
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export function apiFetch(path: string, init: RequestInit = {}) {
  return fetch(`${API_URL}${path}`, { ...init, signal: init.signal ?? AbortSignal.timeout(path.endsWith("/audio") ? 360_000 : path.endsWith("/image") ? 75_000 : 45_000) });
}
