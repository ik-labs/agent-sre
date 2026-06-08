import type { SSEHandler } from "./types";

const EVENTS = [
  "step_start",
  "reset",
  "target_output",
  "diagnose",
  "measure",
  "fix_proposed",
  "fix_applied",
  "verify",
  "guard_case",
  "guard_result",
  "prevent_saved",
  "busy",
  "unauthorized",
  "done",
];

// Optional shared password (entered in the Gate). Appended as ?key= since EventSource can't set headers.
let authKey = sessionStorage.getItem("demo_key") || "";

export function setAuthKey(key: string) {
  authKey = key;
  sessionStorage.setItem("demo_key", key);
}

export function withKey(path: string): string {
  if (!authKey) return path;
  return path + (path.includes("?") ? "&" : "?") + "key=" + encodeURIComponent(authKey);
}

/** Returns {gated, ok}. If gated and key omitted/invalid, ok is false. */
export async function checkAuth(key?: string): Promise<{ gated: boolean; ok: boolean }> {
  const url = key ? `/api/check?key=${encodeURIComponent(key)}` : "/api/check";
  try {
    return await (await fetch(url)).json();
  } catch {
    return { gated: false, ok: true };
  }
}

/**
 * Open an SSE stream and dispatch named events to `onEvent`. The caller closes the returned
 * EventSource on the terminal `done` event; we also close on error to avoid reconnect loops.
 */
export function streamSSE(path: string, onEvent: SSEHandler): EventSource {
  const es = new EventSource(withKey(path));
  for (const name of EVENTS) {
    es.addEventListener(name, (e) => onEvent(name, JSON.parse((e as MessageEvent).data)));
  }
  es.onerror = () => es.close();
  return es;
}
