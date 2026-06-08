"""The target DevOps incident-triage agent (ADK ``root_agent``).

Minimal by design — it's the fixture the Agent SRE debugs, not the star. Deterministic: temperature
0 + a fixed procedure prompt + canned tools => same incident input yields the same trace.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.genai import types

# Make `adk run target_agent` / `adk deploy` load local env + tracing the same way a script does.
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from target_agent.fixtures import get_metrics, get_oncall, get_pod_logs, page_oncall
from target_agent.instrumentation import setup_tracing
from target_agent.prompt_source import load_instruction

setup_tracing()

_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def build_agent() -> Agent:
    """Construct the agent, pulling its instruction from Phoenix at THIS moment.

    Rebuilding per run is what makes the SRE's Fix verifiable live: after `upsert-prompt` creates a
    new prompt version, the next `build_agent()` picks it up — even within the same process.
    """
    return Agent(
        model=_MODEL,
        name="incident_triage_agent",
        instruction=load_instruction(),
        tools=[
            FunctionTool(func=get_metrics),
            FunctionTool(func=get_pod_logs),
            FunctionTool(func=get_oncall),
            FunctionTool(func=page_oncall),
        ],
        # Pin determinism for the demo spine (stable tool args + stable verdict).
        generate_content_config=types.GenerateContentConfig(temperature=0.0),
    )


# Exported for ADK (`adk run target_agent` / deploy). Scripts use build_agent() for a fresh pull.
root_agent = build_agent()
