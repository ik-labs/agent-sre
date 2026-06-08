"""Probe which Gemini model is callable via Vertex AI in this GCP project/region.

Prefers a Gemini 3 model; falls back to gemini-2.5-flash so the demo spine is never blocked.
Prints the first model that returns text — copy it into .env as GEMINI_MODEL.

Run: `make model-probe`  (or `uv run python scripts/model_probe.py`)
Auth: Application Default Credentials (`gcloud auth application-default login`).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Candidates in preference order. Override/extend with GEMINI_MODEL_CANDIDATES (comma-separated).
_DEFAULT_CANDIDATES = [
    "gemini-3-pro-preview",
    "gemini-3-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]


def _candidates() -> list[str]:
    env = (os.environ.get("GEMINI_MODEL_CANDIDATES") or "").strip()
    if env:
        return [m.strip() for m in env.split(",") if m.strip()]
    forced = (os.environ.get("GEMINI_MODEL") or "").strip()
    return [forced, *_DEFAULT_CANDIDATES] if forced else _DEFAULT_CANDIDATES


def main() -> int:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if not project:
        print("ERROR: GOOGLE_CLOUD_PROJECT not set in .env", file=sys.stderr)
        return 2

    from google import genai

    client = genai.Client(vertexai=True, project=project, location=location)
    print(f"Vertex project={project} location={location}\n")

    winner = None
    for model in _candidates():
        try:
            resp = client.models.generate_content(model=model, contents="Reply with exactly: OK")
            text = (resp.text or "").strip()
            print(f"  ✅ {model:<24} -> {text!r}")
            if winner is None:
                winner = model
        except Exception as e:  # noqa: BLE001 — probe: any failure means "not available here"
            msg = str(e).splitlines()[0][:140]
            print(f"  ❌ {model:<24} -> {msg}")

    if winner:
        print(f"\nUse this in .env:\n  GEMINI_MODEL={winner}")
        return 0
    print("\nNo Gemini model was callable. Check Vertex API enablement, region, and ADC auth.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
