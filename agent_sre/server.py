"""FastAPI app serving the cockpit: SSE endpoints over the streaming orchestrator + static UI.

Endpoints are stateless and operate ONLY on the fixed, canned demo (no request input reaches any
tool) — the demo state lives in our own Phoenix space. Secrets stay in the environment.

Public-but-unauthenticated (a hackathon requirement). Since the streams mutate one shared Phoenix
demo prompt and call Gemini, abuse is bounded with a process-global concurrency lock + an hourly cap
rather than auth: only one stream runs at a time, and over the cap callers get a single `busy` event.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from agent_sre.drift import drift_triage
from agent_sre.orchestrator import apply_stream, guard_stream, loop_stream, run_stream

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Agent SRE Cockpit")

# Dev: the Vite dev server runs on :5173. In production the UI is served from this same origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# --- Abuse guard (no auth, per hackathon's public requirement) -----------------------------------
_LOCK = asyncio.Lock()           # one mutating stream at a time (also prevents prompt clobbering)
_HOURLY_CAP = 80                 # generous for judging, bounds cost
_starts: deque[float] = deque()  # timestamps of recent stream starts


def _over_cap() -> bool:
    now = time.time()
    while _starts and now - _starts[0] > 3600:
        _starts.popleft()
    return len(_starts) >= _HOURLY_CAP


async def _guarded_sse(generator):
    """Serialize streams; emit a single `busy` event if one is in flight or the hourly cap is hit."""
    if _LOCK.locked() or _over_cap():
        yield {"event": "busy", "data": json.dumps({"reason": "another run is in progress"})}
        return
    async with _LOCK:
        _starts.append(time.time())
        async for name, payload in generator():
            yield {"event": name, "data": json.dumps(payload)}


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.get("/api/run")
async def run():
    """Stream: reset → broken output → live diagnose → measure (0/1) → proposed fix diff."""
    return EventSourceResponse(_guarded_sse(run_stream))


@app.get("/api/apply")
async def apply():
    """Stream: apply fix via MCP upsert-prompt → re-run → verify (1/1), output flips to paged."""
    return EventSourceResponse(_guarded_sse(apply_stream))


@app.get("/api/guard")
async def guard():
    """Stream: Guard (golden-set replay as a Phoenix experiment) → Prevent (MCP add-dataset-examples)."""
    return EventSourceResponse(_guarded_sse(guard_stream))


@app.get("/api/loop")
async def loop():
    """Stream the entire 6-step loop automatically (no manual gates) in one connection."""
    return EventSourceResponse(_guarded_sse(loop_stream))


# Drift triage spawns the npx MCP server (~10-15s cold), so cache it: the header resolves instantly
# and the read never competes with a run. Warmed in the background at startup.
_drift_cache: dict = {"value": None, "ts": 0.0}
_DRIFT_TTL = 300.0


async def _refresh_drift() -> dict:
    value = await run_in_threadpool(drift_triage)
    _drift_cache["value"] = value
    _drift_cache["ts"] = time.time()
    return value


@app.on_event("startup")
async def _warm_drift() -> None:
    asyncio.create_task(_refresh_drift())  # non-blocking: don't delay readiness


@app.get("/api/drift")
async def drift() -> dict:
    """Live triage of the intermittent 2nd bug (cached read of real drift-watch traces)."""
    fresh = _drift_cache["value"] is not None and time.time() - _drift_cache["ts"] <= _DRIFT_TTL
    return _drift_cache["value"] if fresh else await _refresh_drift()


# Serve the built cockpit at / when present (single public URL for Phase 5). Mounted last so /api wins.
_DIST = Path(__file__).resolve().parents[1] / "cockpit" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="cockpit")
