"""Seed the target agent's instruction into the Phoenix prompt store (one-time, Phase 2 Step 0).

Creates/updates the ``incident-triage-agent`` prompt with the CURRENT (buggy) instruction so the
agent can pull it at runtime and the SRE can later patch it via MCP ``upsert-prompt``.

Run: `make seed-prompt`  (or `uv run python scripts/seed_prompt.py`)
Re-running adds a new version (same name) — harmless.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

from target_agent.prompt import INCIDENT_AGENT_INSTRUCTION  # noqa: E402
from target_agent.prompt_source import PROMPT_IDENTIFIER  # noqa: E402


def main() -> int:
    if not (os.environ.get("PHOENIX_API_KEY") or "").strip():
        print("ERROR: PHOENIX_API_KEY not set in .env", file=sys.stderr)
        return 2

    from phoenix.client import Client
    from phoenix.client.types import PromptVersion

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    client = Client(
        base_url=os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or None,
        api_key=os.environ.get("PHOENIX_API_KEY") or None,
    )

    prompt = client.prompts.create(
        name=PROMPT_IDENTIFIER,
        version=PromptVersion(
            [{"role": "system", "content": INCIDENT_AGENT_INSTRUCTION}],
            model_name=model,
            model_provider="GOOGLE",
            description="Initial version — contains the planted payment-vs-payments bug.",
        ),
        prompt_description="DevOps incident-triage agent instruction (Agent SRE demo target).",
    )
    pid = getattr(prompt, "id", None) or getattr(prompt, "_id", "?")
    print(f"✅ seeded Phoenix prompt '{PROMPT_IDENTIFIER}' (id={pid}) with model={model}")
    print("   The target agent will now pull this instruction at startup.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
