"""Phoenix tracing setup for the target agent (and Phase 0 smoke test).

Pattern verified against the Arize-ai/gemini-hackathon starter (Apache-2.0):
``phoenix.otel.register(auto_instrument=True, batch=False)`` alone is enough — ``auto_instrument``
discovers the installed ``openinference-instrumentation-google-adk`` package and wires ADK + tool +
Gemini spans. No explicit ``GoogleADKInstrumentor().instrument()`` call is required.

Requires ``google-adk>=1.32`` and ``openinference-instrumentation-google-adk>=0.1.11``.
Env: ``PHOENIX_API_KEY``, ``PHOENIX_COLLECTOR_ENDPOINT`` (with /s/<space>, NOT /v1/traces),
optional ``PHOENIX_PROJECT_NAME``.
"""

from __future__ import annotations

import os
from typing import Any, Optional

_provider: Optional[Any] = None


def setup_tracing(project_name: Optional[str] = None) -> Optional[Any]:
    """Register Phoenix tracing once. Returns the provider, or ``None`` if Phoenix isn't configured."""
    global _provider
    if _provider is not None:
        return _provider
    if not (os.environ.get("PHOENIX_API_KEY") or "").strip():
        # No key configured — run untraced rather than crashing (useful for local dry runs).
        return None

    from phoenix.otel import register

    _provider = register(
        project_name=project_name or os.environ.get("PHOENIX_PROJECT_NAME", "incident-agent"),
        batch=False,
        auto_instrument=True,
        verbose=False,
    )
    return _provider
