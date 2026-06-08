"""FastAPI app serving the cockpit: two SSE endpoints over the streaming orchestrator + static UI.

Endpoints are stateless and operate ONLY on the fixed, canned demo (no request input reaches any
tool) — the demo state lives in our own Phoenix space. Secrets stay in the environment.

TODO (Phase 5 deploy): these endpoints mutate the Phoenix prompt store (reset/upsert) and call
Gemini on each request. Before exposing publicly on Cloud Run, add a simple shared-secret/header
gate or rate limit to bound abuse/cost. Fine for local dev.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from agent_sre.orchestrator import apply_stream, guard_stream, run_stream

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Agent SRE Cockpit")

# Dev: the Vite dev server runs on :5173. In production the UI is served from this same origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


async def _sse(generator):
    async for name, payload in generator():
        yield {"event": name, "data": json.dumps(payload)}


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/api/run")
async def run():
    """Stream: reset → broken output → live diagnose → measure (0/1) → proposed fix diff."""
    return EventSourceResponse(_sse(run_stream))


@app.get("/api/apply")
async def apply():
    """Stream: apply fix via MCP upsert-prompt → re-run → verify (1/1), output flips to paged."""
    return EventSourceResponse(_sse(apply_stream))


@app.get("/api/guard")
async def guard():
    """Stream: Guard (golden-set replay as a Phoenix experiment) → Prevent (MCP add-dataset-examples)."""
    return EventSourceResponse(_sse(guard_stream))


# Serve the built cockpit at / when present (single public URL for Phase 5). Mounted last so /api wins.
_DIST = Path(__file__).resolve().parents[1] / "cockpit" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="cockpit")
