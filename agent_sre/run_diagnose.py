"""Run the SRE's Diagnose step against the target agent's Phoenix traces.

Prints which Phoenix MCP tools the SRE called (proof of meaningful MCP use) and its structured
diagnosis. The SRE's own work is traced to the 'agent-sre' Phoenix project.

Run: `make diagnose`  (or `uv run python -m agent_sre.run_diagnose`)
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

from target_agent.instrumentation import setup_tracing  # noqa: E402

TARGET_PROJECT = "incident-agent"
DIAGNOSE_TASK = (
    f"Target agent project: '{TARGET_PROJECT}'. Complaint: the agent investigated the 'payments' "
    "service, concluded it was healthy, and paged no one — but payments is actually failing in "
    "production with 500s. Diagnose the root cause from the most recent trace."
)


async def diagnose() -> dict:
    from google.adk.runners import InMemoryRunner

    from agent_sre.sre_agent import build_sre_agent

    agent = build_sre_agent()
    app_name, user_id, session_id = "agent_sre", "sre", secrets.token_hex(8)
    runner = InMemoryRunner(agent=agent, app_name=app_name)
    await runner.session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )

    tool_calls: list[str] = []
    final_text = ""
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=DIAGNOSE_TASK)]),
        ):
            for part in (getattr(event.content, "parts", None) or []) if getattr(event, "content", None) else []:
                fc = getattr(part, "function_call", None)
                if fc:
                    tool_calls.append(fc.name)
                if getattr(part, "text", None):
                    final_text = part.text
    finally:
        # Close the MCP stdio subprocess so the process exits cleanly.
        for tool in agent.tools:
            close = getattr(tool, "close", None)
            if close:
                try:
                    await close()
                except Exception:
                    pass

    return {"tool_calls": tool_calls, "diagnosis": final_text.strip()}


def main() -> int:
    setup_tracing(project_name="agent-sre")  # the SRE is itself observable
    print("Agent SRE — DIAGNOSE\n")
    print(f"Task: {DIAGNOSE_TASK}\n")
    result = asyncio.run(diagnose())

    print(f"Phoenix MCP tools the SRE called: {result['tool_calls'] or '(none)'}\n")
    print("Diagnosis:\n" + (result["diagnosis"] or "(empty)"))

    diag = result["diagnosis"].lower()
    ok = ("payment" in diag) and ("get_pod_logs" in diag) and ("payments" in diag)
    print(f"\n{'✅ SRE located the bad argument via MCP.' if ok else '⚠️  Diagnosis did not clearly name the bad arg — inspect above.'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
