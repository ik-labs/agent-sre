"""Load the target agent's system instruction from the Phoenix prompt store.

This is what makes the SRE's "Fix" LIVE: the agent pulls its instruction from a Phoenix-managed
prompt (``incident-triage-agent``) at startup, so when the SRE applies a fix via ``upsert-prompt``
(a new version), the very next run picks it up. If Phoenix is unreachable (no key / offline), we
fall back to the local buggy constant so the agent still runs.

The fetched prompt text is treated strictly as DATA used as an LLM system instruction — never
executed or evaluated.
"""

from __future__ import annotations

import os

# NOTE: separator-free, lowercase. The Phoenix MCP `upsert-prompt` tool normalizes names by
# stripping hyphens/underscores (e.g. "incident-triage-agent" -> "incidenttriageagent"), while the
# Python client preserves them. Using a canonical alphanumeric name keeps the prompt the agent reads
# and the prompt the SRE patches identical across BOTH paths.
PROMPT_IDENTIFIER = "incidenttriageagent"


def _phoenix_client():
    from phoenix.client import Client

    base_url = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").strip() or None
    api_key = (os.environ.get("PHOENIX_API_KEY") or "").strip() or None
    return Client(base_url=base_url, api_key=api_key)


def _extract_text(prompt) -> str:
    """Pull the instruction text out of a Phoenix Prompt, tolerant of template shape."""
    # Preferred: format() returns a provider-shaped dict with a "messages" list.
    try:
        formatted = prompt.format()
        messages = formatted.get("messages") if isinstance(formatted, dict) else None
        if messages:
            return _text_from_messages(messages)
    except Exception:
        pass
    # Fallback: read the raw template.
    template = getattr(prompt, "_template", None)
    if isinstance(template, dict) and template.get("messages"):
        return _text_from_messages(template["messages"])
    return ""


def _text_from_messages(messages) -> str:
    parts: list[str] = []
    for msg in messages:
        content = msg.get("content") if isinstance(msg, dict) else None
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for piece in content:
                if isinstance(piece, dict) and piece.get("text"):
                    parts.append(piece["text"])
                elif isinstance(piece, str):
                    parts.append(piece)
    return "\n".join(p for p in parts if p).strip()


def load_instruction() -> str:
    """Return the agent instruction from Phoenix, or the local buggy constant on any failure."""
    from target_agent.prompt import INCIDENT_AGENT_INSTRUCTION

    if not (os.environ.get("PHOENIX_API_KEY") or "").strip():
        return INCIDENT_AGENT_INSTRUCTION
    try:
        prompt = _phoenix_client().prompts.get(prompt_identifier=PROMPT_IDENTIFIER)
        text = _extract_text(prompt)
        if text:
            return text
        print(f"[prompt_source] Phoenix prompt '{PROMPT_IDENTIFIER}' had no extractable text; using local fallback.")
    except Exception as e:  # noqa: BLE001
        print(f"[prompt_source] could not load Phoenix prompt ({e!r}); using local fallback.")
    return INCIDENT_AGENT_INSTRUCTION
