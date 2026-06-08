"""Phase 0 smoke test: prove ADK -> Gemini(Vertex) -> Phoenix tracing works end-to-end.

This is a THROWAWAY agent (a single trivial tool), NOT the real target agent (that's Phase 1).
A successful run produces a trace in the Phoenix project named by PHOENIX_PROJECT_NAME with an
LLM span and a tool span.

Run: `make smoke-trace`  (or `uv run python scripts/smoke_trace.py "your message"`)
"""

from __future__ import annotations

import asyncio
import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

from target_agent.instrumentation import setup_tracing  # noqa: E402


def ping(message: str) -> str:
    """Echo a short acknowledgement for a given message (smoke-test tool)."""
    return f"pong: {message}"


async def run_turn(user_text: str) -> None:
    provider = setup_tracing()
    if provider is None:
        print("WARNING: PHOENIX_API_KEY not set — running untraced. No trace will appear.", file=sys.stderr)

    from google.adk.agents import Agent
    from google.adk.runners import InMemoryRunner
    from google.adk.tools import FunctionTool
    from google.genai import types

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    agent = Agent(
        model=model,
        name="phase0_smoke_agent",
        instruction="You are a smoke test. When asked, call the `ping` tool, then reply briefly.",
        tools=[FunctionTool(func=ping)],
    )

    app_name, user_id, session_id = "phase0_smoke", "local_user", secrets.token_hex(8)
    runner = InMemoryRunner(agent=agent, app_name=app_name)
    await runner.session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    final = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(role="user", parts=[types.Part(text=user_text)]),
    ):
        if getattr(event, "content", None) and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final = part.text

    print(f"model={model}")
    print(f"agent final: {final.strip()!r}")
    print(f"-> check Phoenix project {os.environ.get('PHOENIX_PROJECT_NAME', 'incident-agent')!r} for the trace")


def main() -> None:
    msg = sys.argv[1] if len(sys.argv) > 1 else "Please ping the message 'hello phoenix'."
    asyncio.run(run_turn(msg))


if __name__ == "__main__":
    main()
