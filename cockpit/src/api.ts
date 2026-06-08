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
  "done",
];

/**
 * Open an SSE stream and dispatch named events to `onEvent`. The caller closes the returned
 * EventSource on the terminal `done` event; we also close on error to avoid reconnect loops.
 */
export function streamSSE(path: string, onEvent: SSEHandler): EventSource {
  const es = new EventSource(path);
  for (const name of EVENTS) {
    es.addEventListener(name, (e) => onEvent(name, JSON.parse((e as MessageEvent).data)));
  }
  es.onerror = () => es.close();
  return es;
}
