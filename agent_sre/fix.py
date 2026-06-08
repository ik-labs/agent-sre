"""Fix step — derive the corrected instruction and apply it via the Phoenix `upsert-prompt` MCP tool.

Deterministic transform of the buggy instruction (so the spine is reproducible):
  1. the misleading internal-label note: `payment` -> `payments` (both backtick and quoted forms)
  2. append a guard rule: empty logs + a HIGH error rate must NOT be read as "healthy".

The resulting template is written to Phoenix as a NEW version of `incident-triage-agent`, which the
target agent picks up on its next run (see target_agent/agent.py:build_agent).
"""

from __future__ import annotations

import difflib
import os

from agent_sre.mcp_client import PhoenixMCP
from target_agent.prompt_source import PROMPT_IDENTIFIER

FIX_RULE = (
    "If the logs come back empty BUT the metrics show a high error rate, do NOT conclude the system "
    "is healthy — recheck the service name against the operator's reported service and retry before "
    "concluding. Empty logs together with a LOW error rate genuinely indicate health (do not page)."
)


def compute_fixed_instruction(buggy: str) -> str:
    """Apply the deterministic corrections to the buggy instruction text."""
    fixed = buggy.replace("`payment`", "`payments`")  # the misleading internal-label note (backtick)
    fixed = fixed.replace('"payment"', '"payments"')  # ...and its quoted form
    if FIX_RULE not in fixed:
        fixed = fixed.rstrip() + "\n\nIMPORTANT: " + FIX_RULE + "\n"
    return fixed


def unified_diff(buggy: str, fixed: str) -> str:
    return "".join(
        difflib.unified_diff(
            buggy.splitlines(keepends=True),
            fixed.splitlines(keepends=True),
            fromfile="incident-triage-agent (buggy)",
            tofile="incident-triage-agent (fixed)",
        )
    )


def _upsert(template: str, description: str) -> dict:
    """Create a new version of the target's prompt via the Phoenix `upsert-prompt` MCP tool."""
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    with PhoenixMCP() as mcp:
        return mcp.call(
            "upsert-prompt",
            {
                "name": PROMPT_IDENTIFIER,
                "template": template,
                "model_provider": "GOOGLE",
                "model_name": model,
                "temperature": 0.0,
                "description": description,
            },
        )


def apply_fix(fixed_instruction: str) -> dict:
    """Upsert the fixed instruction as a new Phoenix prompt version via MCP. Returns the MCP result."""
    return _upsert(fixed_instruction, "SRE fix: payment->payments + empty-output-is-not-healthy rule.")


def reset_to_buggy() -> dict:
    """Re-seed the original buggy instruction so the demo baseline is always 0/1 (repeatability)."""
    from target_agent.prompt import INCIDENT_AGENT_INSTRUCTION

    return _upsert(INCIDENT_AGENT_INSTRUCTION, "Reset to buggy baseline (demo repeatability).")
