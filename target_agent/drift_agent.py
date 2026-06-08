"""A SECOND, intermittently-buggy target agent — breadth for the SRE's triage (diagnose-only).

Unlike the deterministic spine agent, this one has an ambiguous prompt and a non-zero temperature,
so across runs it *intermittently* makes a wrong tool-selection: sometimes it concludes without ever
calling `get_pod_logs` (skips log inspection). The randomness is isolated HERE — the demo spine stays
deterministic. The SRE surfaces this pattern from real traces but does NOT fix it live.
"""

from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.genai import types

from target_agent.fixtures import get_metrics, get_oncall, get_pod_logs, page_oncall

DRIFT_INCIDENT = "The checkout service might be degraded in production — take a quick look and report."

# Deliberately ambiguous about WHICH tools to use, so tool selection varies run to run.
DRIFT_INSTRUCTION = """\
You are a DevOps incident-triage agent. Investigate the reported incident and give a brief verdict.
You have tools to check service metrics and to read pod logs. Use whichever tools you judge
necessary — be quick and efficient. End with: VERDICT: <one sentence>.
"""


def build_drift_agent() -> Agent:
    return Agent(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        name="drift_triage_agent",
        instruction=DRIFT_INSTRUCTION,
        tools=[
            FunctionTool(func=get_metrics),
            FunctionTool(func=get_pod_logs),
            FunctionTool(func=get_oncall),
            FunctionTool(func=page_oncall),
        ],
        # Non-zero temperature => intermittent tool-selection (the 2nd bug).
        generate_content_config=types.GenerateContentConfig(temperature=0.9),
    )
