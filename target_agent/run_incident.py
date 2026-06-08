"""Run the incident once (traced) and print the observed tool-call chain + final verdict.

This is how we prove the bug WITHOUT eyeballing Phoenix: it extracts the function calls from the
ADK event stream and checks the expected broken chain:
    get_metrics("payments") -> error_rate 0.38   (correct)
    get_pod_logs("payment") -> "no logs found"    (the bug / cause span)
    VERDICT: healthy                              (false / symptom span)

Run: `make incident`  (or `uv run python -m target_agent.run_incident`)
"""

from __future__ import annotations

import asyncio
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

from google.genai import types  # noqa: E402

from target_agent.agent import build_agent  # noqa: E402  (also runs setup_tracing)
from target_agent.prompt import INCIDENT_INPUT  # noqa: E402


async def run() -> dict:
    from google.adk.runners import InMemoryRunner

    # Rebuild per run so a freshly-applied Phoenix prompt fix takes effect immediately.
    agent = build_agent()
    app_name, user_id, session_id = "incident_triage", "operator", secrets.token_hex(8)
    runner = InMemoryRunner(agent=agent, app_name=app_name)
    await runner.session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    calls: list[tuple[str, dict]] = []
    responses: list[str] = []
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=INCIDENT_INPUT)]),
    ):
        for part in (getattr(event.content, "parts", None) or []) if getattr(event, "content", None) else []:
            fc = getattr(part, "function_call", None)
            if fc:
                calls.append((fc.name, dict(fc.args or {})))
            fr = getattr(part, "function_response", None)
            if fr:
                responses.append(str(getattr(fr, "response", "")))
            if getattr(part, "text", None):
                final_text = part.text

    return {"calls": calls, "responses": responses, "final": final_text.strip()}


def main() -> int:
    print(f"INCIDENT: {INCIDENT_INPUT}\n")
    result = asyncio.run(run())

    print("Tool-call sequence:")
    for name, args in result["calls"]:
        print(f"  - {name}({args})")
    print(f"\nFinal:\n  {result['final']}\n")

    # --- assert the broken chain (deterministic spine) ---
    calls = result["calls"]
    args_by_tool = {name: args for name, args in calls}
    checks = {
        "metrics queried 'payments'": args_by_tool.get("get_metrics", {}).get("service") == "payments",
        "logs queried 'payment' (the bug)": args_by_tool.get("get_pod_logs", {}).get("service") == "payment",
        "no page was sent": "page_oncall" not in args_by_tool,
        "verdict is 'healthy' (false)": "verdict: healthy" in result["final"].lower(),
    }
    print("Failure-chain checks:")
    ok = True
    for label, passed in checks.items():
        print(f"  [{'x' if passed else ' '}] {label}")
        ok = ok and passed
    print(f"\n{'✅ Bug reproduced deterministically.' if ok else '⚠️  Chain did not match — inspect above.'}")
    print("-> trace in Phoenix project 'incident-agent' (verify the cause span via MCP).")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
