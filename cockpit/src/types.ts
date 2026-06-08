// Event payload shapes emitted by the backend SSE endpoints (agent_sre/orchestrator.py).

export interface TargetOutput {
  phase: "before" | "after";
  calls: string[];
  final: string;
  verdict: "healthy" | "paged" | "unknown";
}

export interface DiagnoseResult {
  tools: string[];
  text: string;
  url?: string | null;
}

export interface MeasureResult {
  score: 0 | 1;
  verdict: "PASS" | "FAIL";
  reason: string;
  final: string;
  calls: string[];
}

export interface FixProposed {
  diff: string;
}

export interface GuardCase {
  label: string;
  passed: boolean;
  paged_team: string;
}

export interface GuardResult {
  all_pass: boolean;
  total: number;
  passed: number;
  url: string | null;
}

export interface PreventSaved {
  dataset: string;
  count: number;
  url?: string | null;
}

export type SSEHandler = (event: string, data: unknown) => void;
