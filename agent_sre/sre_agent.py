"""Agent SRE — an ADK agent whose toolset is the Arize Phoenix MCP server.

This is the "meaningful MCP use" the Arize track scores: the SRE reads the target agent's traces
and spans through Phoenix MCP to diagnose a failure, and (Step 3) patches the target's prompt via
the ``upsert-prompt`` MCP tool. Measurement (the eval) lives in Python (see eval.py) — that's the
part MCP can't do.

Domain-agnostic by design: DevOps is just the demo fixture. The SRE only knows "a Phoenix project
and a complaint", and reasons from the trace.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioConnectionParams,
    StdioServerParameters,
)
from google.genai import types

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Tools the SRE is allowed to use. Diagnose = reads; Fix (Step 3) = upsert-prompt + prompt reads.
_DIAGNOSE_TOOLS = ["list-projects", "list-traces", "get-trace", "get-spans"]
_FIX_TOOLS = ["get-latest-prompt", "get-prompt", "upsert-prompt"]

DIAGNOSE_INSTRUCTION = """\
You are Agent SRE, a reliability engineer that debugs OTHER AI agents by reading their Arize
Phoenix traces. You are given a Phoenix project name and a complaint about the target agent.

Find the root cause using ONLY your Phoenix tools. Follow this procedure exactly:

1. Call `list-traces` for the given project (limit 1) to get the most recent trace's id.
2. Call `get-spans` for that project with span_kinds=["TOOL"] and trace_ids=[that id] to list the
   tool calls with their input arguments and outputs.
3. Inspect each TOOL span: the tool name, its input argument value (look at `tool.parameters.*`,
   `input.value`, or `tool_call_args`), and its output (`tool_response` / `output.value`).
4. Find the defect: a tool was called with an argument that does NOT match the service named in the
   complaint and the metrics, so it returned empty/misleading data, which led the agent to a wrong
   final conclusion. The cause span (the bad tool call) is DIFFERENT from the symptom (the wrong
   final answer).

Then output your diagnosis in EXACTLY this format and nothing else:

ROOT CAUSE: <one sentence naming the wrong argument>
CAUSE SPAN: <the tool span name>
BAD ARGUMENT: <tool>(<param>="<wrong value>") — should be "<correct value>"
IMPACT: <one sentence: how the empty result produced the wrong final answer>
PROPOSED FIX: <one sentence describing the prompt change that would correct it>

Do not page anyone and do not modify anything. Diagnosis only.
"""


def _phoenix_mcp_toolset(tool_filter: list[str]) -> MCPToolset:
    """A Phoenix MCP toolset over stdio (npx). Secrets come from env at runtime, not hardcoded."""
    base_url = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT", "")
    api_key = os.environ.get("PHOENIX_API_KEY", "")
    return MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command="npx",
                # Keep the API key OUT of argv (it would otherwise show in `ps`). The phoenix-mcp
                # server reads PHOENIX_API_KEY from the environment; we pass it via env= below.
                args=["-y", "@arizeai/phoenix-mcp@latest", "--baseUrl", base_url],
                env={**os.environ, "PHOENIX_API_KEY": api_key},
            ),
            # npx may cold-start the server; give it room beyond the 5s default.
            timeout=60.0,
        ),
        tool_filter=tool_filter,
    )


def build_sre_agent(*, include_fix_tools: bool = False) -> LlmAgent:
    """Construct the SRE agent. Diagnose-only by default; add fix tools for Step 3."""
    tools = list(_DIAGNOSE_TOOLS) + (list(_FIX_TOOLS) if include_fix_tools else [])
    return LlmAgent(
        model=_MODEL,
        name="agent_sre",
        instruction=DIAGNOSE_INSTRUCTION,
        tools=[_phoenix_mcp_toolset(tools)],
        generate_content_config=types.GenerateContentConfig(temperature=0.0),
    )


# Exported for ADK (`adk run agent_sre` / deploy). Diagnose-only by default.
root_agent = build_sre_agent()
