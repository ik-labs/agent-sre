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

# Pull the instruction from the Phoenix prompt store so the SRE's Fix (upsert-prompt) is LIVE.
# Falls back to the local buggy constant if Phoenix is unreachable. See prompt_source.py.
root_agent = Agent(
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
