"""Streaming orchestration for the cockpit — turns the proven spine into ordered UI events.

Two async generators yield ``(event_name, payload)`` tuples by calling the EXISTING, already-proven
functions (no new agent logic here). The FastAPI server adapts these to SSE. Blocking sync calls
(the stdio MCP client, Phoenix prompt reads) are offloaded with ``asyncio.to_thread`` so the event
stream stays responsive.

Interactive flow (locked with user):
  run_stream()   -> reset, target_output(before), diagnose (live SRE+MCP), measure (0/1), fix_proposed
  apply_stream() -> fix_applied (MCP upsert), target_output(after), verify (1/1)
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator, Tuple

from agent_sre.eval import measure
from agent_sre.fix import FIX_RULE, apply_fix, compute_fixed_instruction, reset_to_buggy, unified_diff
from agent_sre.guard import ensure_fixed, log_experiment, replay_cases
from agent_sre.prevent import DATASET_NAME, count_examples, save_failing_case
from agent_sre.run_diagnose import diagnose
from target_agent.prompt_source import load_instruction

Event = Tuple[str, dict]


def _verdict_word(final: str) -> str:
    line = (final or "").splitlines()[-1] if final else ""
    if "paged" in line.lower():
        return "paged"
    if "healthy" in line.lower():
        return "healthy"
    return "unknown"


def _calls_list(calls) -> list[str]:
    return [f"{name}({args})" for name, args in calls]


def _measure_payload(m: dict) -> dict:
    return {
        "score": m["score"],
        "verdict": m["verdict"],
        "reason": m["reason"],
        "final": m["final"],
        "calls": _calls_list(m["calls"]),
    }


def _target_payload(m: dict, phase: str) -> dict:
    return {
        "phase": phase,
        "calls": _calls_list(m["calls"]),
        "final": m["final"],
        "verdict": _verdict_word(m["final"]),
    }


async def _wait_until(predicate, timeout: int = 20) -> bool:
    for _ in range(timeout):
        text = await asyncio.to_thread(load_instruction)
        if predicate(text):
            return True
        await asyncio.sleep(1)
    return False


async def run_stream() -> AsyncIterator[Event]:
    """Reset → run the broken agent → diagnose live → measure baseline (0/1) → propose the fix."""
    yield "step_start", {"step": "reset"}
    await asyncio.to_thread(reset_to_buggy)
    await _wait_until(lambda t: FIX_RULE not in t, timeout=20)
    yield "reset", {"ok": True}

    # One run of the broken target agent gives BOTH the left-column output and the 0/1 score.
    yield "step_start", {"step": "target_before"}
    m0 = await measure("MEASURE — baseline")
    yield "target_output", _target_payload(m0, phase="before")

    # Live, agentic diagnosis over the trace just produced (SRE = ADK + Phoenix MCP).
    yield "step_start", {"step": "diagnose"}
    d = await diagnose()
    yield "diagnose", {"tools": d["tool_calls"], "text": d["diagnosis"]}

    yield "step_start", {"step": "measure"}
    yield "measure", _measure_payload(m0)

    # Propose (but do not apply) the prompt fix.
    yield "step_start", {"step": "fix"}
    buggy = await asyncio.to_thread(load_instruction)
    fixed = compute_fixed_instruction(buggy)
    yield "fix_proposed", {"diff": unified_diff(buggy, fixed)}

    yield "done", {"phase": "run", "baseline_score": m0["score"]}


async def apply_stream() -> AsyncIterator[Event]:
    """Apply the fix via Phoenix MCP upsert-prompt, then re-run live → verify 1/1 PASS."""
    yield "step_start", {"step": "apply"}
    buggy = await asyncio.to_thread(load_instruction)
    fixed = compute_fixed_instruction(buggy)
    await asyncio.to_thread(apply_fix, fixed)
    visible = await _wait_until(lambda t: FIX_RULE in t, timeout=20)
    yield "fix_applied", {"ok": visible}

    yield "step_start", {"step": "target_after"}
    m1 = await measure("VERIFY — live re-run")
    yield "target_output", _target_payload(m1, phase="after")

    yield "step_start", {"step": "verify"}
    yield "verify", _measure_payload(m1)

    yield "done", {"phase": "apply", "verify_score": m1["score"]}


async def guard_stream() -> AsyncIterator[Event]:
    """Guard: replay the golden set (streamed per case) as a Phoenix experiment → then Prevent."""
    yield "step_start", {"step": "guard"}
    await asyncio.to_thread(ensure_fixed)
    rows: list[dict] = []
    async for r in replay_cases():
        rows.append(r)
        yield "guard_case", {
            "label": r["label"],
            "passed": r["passed"],
            "paged_team": r["paged_team"] or "no page",
        }
    url = await asyncio.to_thread(log_experiment, rows)
    yield "guard_result", {
        "all_pass": all(r["passed"] for r in rows),
        "total": len(rows),
        "passed": sum(1 for r in rows if r["passed"]),
        "url": url,
    }

    # Prevent — save the failing case as a permanent dataset example via MCP.
    yield "step_start", {"step": "prevent"}
    saved = await asyncio.to_thread(save_failing_case)
    n = await asyncio.to_thread(count_examples)
    base = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").rstrip("/")
    ds_id = (saved.get("result") or {}).get("dataset_id") if isinstance(saved.get("result"), dict) else None
    ds_url = f"{base}/datasets/{ds_id}/examples" if base and ds_id else None
    yield "prevent_saved", {"dataset": DATASET_NAME, "count": n, "url": ds_url}

    yield "done", {"phase": "guard"}


async def loop_stream() -> AsyncIterator[Event]:
    """The whole 6-step loop in one stream (no manual gates): run → apply → guard.

    Swallows the intermediate `done` events from the sub-streams so the UI sees a single terminal
    `done` at the very end.
    """
    for sub in (run_stream, apply_stream):
        async for name, payload in sub():
            if name != "done":
                yield name, payload
    async for name, payload in guard_stream():
        yield name, payload  # keep guard's final `done`
