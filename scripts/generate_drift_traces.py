"""Generate real traces for the intermittent 2nd bug (run ONCE; the demo then reads them).

Runs the drift agent N times on the drift incident, emitting traces to the `drift-watch` Phoenix
project. Because the drift agent uses a non-zero temperature, ~some runs skip log inspection — a real
intermittent tool-selection issue the SRE later surfaces. Generating once keeps the demo stable.

Run: `make drift-seed`  (or `uv run python scripts/generate_drift_traces.py [N]`)
"""

from __future__ import annotations

import asyncio
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

from google.genai import types  # noqa: E402

from target_agent.drift_agent import DRIFT_INCIDENT, build_drift_agent  # noqa: E402
from target_agent.instrumentation import setup_tracing  # noqa: E402

DRIFT_PROJECT = "drift-watch"


async def _one_run(agent) -> list[str]:
    from google.adk.runners import InMemoryRunner

    app_name, user_id, session_id = "drift_watch", "operator", secrets.token_hex(8)
    runner = InMemoryRunner(agent=agent, app_name=app_name)
    await runner.session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    tools: list[str] = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=DRIFT_INCIDENT)]),
    ):
        for part in (getattr(event.content, "parts", None) or []) if getattr(event, "content", None) else []:
            fc = getattr(part, "function_call", None)
            if fc:
                tools.append(fc.name)
    return tools


async def main(n: int) -> None:
    setup_tracing(project_name=DRIFT_PROJECT)
    agent = build_drift_agent()
    skipped_logs = 0
    for i in range(n):
        tools = await _one_run(agent)
        inspected = "get_pod_logs" in tools
        skipped_logs += 0 if inspected else 1
        print(f"  run {i + 1:>2}/{n}: tools={tools} {'' if inspected else '<-- skipped logs'}")
    print(f"\nGenerated {n} traces in Phoenix project '{DRIFT_PROJECT}'.")
    print(f"{skipped_logs}/{n} skipped log inspection (the intermittent tool-selection issue).")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    asyncio.run(main(count))
