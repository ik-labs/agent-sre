"""Drift triage — the SRE surfaces the intermittent 2nd bug from real traces (diagnose-only).

Reads the `drift-watch` project's TOOL spans via Phoenix MCP, groups them by trace, and counts how
many traces skipped log inspection (called no `get_pod_logs`). No fix is applied — this demonstrates
the SRE handling a realistic, noisy backlog beyond the single clean spine bug.
"""

from __future__ import annotations

from collections import defaultdict

from agent_sre.mcp_client import PhoenixMCP

DRIFT_PROJECT = "drift-watch"


def _tool_name(span: dict) -> str:
    attrs = span.get("attributes", {}) if isinstance(span, dict) else {}
    return attrs.get("tool.name") or attrs.get("gen_ai.tool.name") or span.get("name", "")


def drift_triage() -> dict:
    """Return {n_traces, n_affected, summary} for the intermittent tool-selection issue."""
    with PhoenixMCP() as mcp:
        data = mcp.call(
            "get-spans",
            {"project_identifier": DRIFT_PROJECT, "span_kinds": ["TOOL"], "limit": 500},
        )

    spans = data.get("spans", []) if isinstance(data, dict) else []
    by_trace: dict[str, set[str]] = defaultdict(set)
    for s in spans:
        tid = (s.get("context") or {}).get("trace_id")
        if tid:
            by_trace[tid].add(_tool_name(s))

    total = len(by_trace)
    affected = sum(1 for tools in by_trace.values() if not any("get_pod_logs" in t for t in tools))
    summary = (
        f"intermittent tool-selection: {affected}/{total} traces concluded without inspecting logs"
        if total
        else "no drift traces found — run `make drift-seed` first"
    )
    return {"n_traces": total, "n_affected": affected, "summary": summary}


if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    r = drift_triage()
    print("=== DRIFT WATCH (triage only) ===")
    print(f"  {r['summary']}")
