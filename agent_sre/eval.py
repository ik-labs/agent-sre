"""Measure step — the LLM-as-judge that proves the bug exists (0/1) and the fix works (1/1).

This is the part the Phoenix MCP server cannot do, so it runs in Python with the Gemini judge
pinned to temperature 0 for deterministic verdicts. The SAME judge + SAME case is used for both
the pre-fix baseline (Measure) and the post-fix re-run (Verify) — only the Phoenix prompt version
differs between them.

Rubric is the answer key from docs/fixtures-and-ground-truth.md.
"""

from __future__ import annotations

import json
import os
from typing import Optional

_JUDGE_RUBRIC = """\
You are grading a DevOps incident-triage agent's handling of an incident.
GROUND TRUTH: the "payments" service had repeated "connection refused" errors; the platform team
SHOULD have been paged with a summary mentioning the connection errors.

Given the agent's final action below, output PASS only if BOTH are true:
  (a) it identified the connection-refused errors in the payments logs, AND
  (b) it paged the "platform" team.
Otherwise output FAIL.

Return JSON only: {"verdict":"PASS|FAIL","reason":"<one sentence>"}

=== AGENT FINAL ANSWER ===
{final_answer}

=== AGENT ACTIONS (tool calls observed) ===
{actions}
"""


def judge(final_answer: str, actions: str, model: Optional[str] = None) -> dict:
    """Run the Gemini LLM-as-judge (temp 0) over one agent transcript. Returns {verdict, reason}."""
    from google import genai
    from google.genai import types

    model = model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    # Use replace (not str.format) — the rubric contains literal JSON braces.
    prompt = _JUDGE_RUBRIC.replace("{final_answer}", final_answer or "(none)").replace(
        "{actions}", actions or "(none)"
    )
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.0, response_mime_type="application/json"),
    )
    try:
        data = json.loads(resp.text)
    except Exception:
        data = {"verdict": "FAIL", "reason": f"judge returned non-JSON: {(resp.text or '')[:120]}"}
    verdict = str(data.get("verdict", "FAIL")).upper()
    return {"verdict": "PASS" if verdict == "PASS" else "FAIL", "reason": data.get("reason", "")}


def _actions_summary(calls: list[tuple[str, dict]], responses: list[str]) -> str:
    lines = [f"- {name}({args})" for name, args in calls]
    if responses:
        lines.append(f"(tool outputs included errors: {'yes' if any('connection refused' in r for r in responses) else 'no'})")
    return "\n".join(lines)


async def measure(label: str) -> dict:
    """Run the target agent once (live) on the incident and score it. 0 = FAIL, 1 = PASS."""
    from target_agent.run_incident import run as run_incident

    result = await run_incident()
    actions = _actions_summary(result["calls"], result["responses"])
    verdict = judge(result["final"], actions)
    score = 1 if verdict["verdict"] == "PASS" else 0
    return {
        "label": label,
        "score": score,
        "verdict": verdict["verdict"],
        "reason": verdict["reason"],
        "final": result["final"],
        "calls": result["calls"],
    }


def _print_card(m: dict) -> None:
    print(f"=== {m['label']} ===")
    print(f"  agent verdict line : {m['final'].splitlines()[-1] if m['final'] else '(none)'}")
    print(f"  tool calls         : {[f'{n}({a})' for n, a in m['calls']]}")
    print(f"  EVAL               : {m['score']}/1 {m['verdict']} — {m['reason']}")


if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    m = asyncio.run(measure("MEASURE (baseline, current Phoenix prompt)"))
    _print_card(m)
    raise SystemExit(0 if m["score"] == 0 else 0)  # baseline is expected to be 0/1 (the bug exists)
