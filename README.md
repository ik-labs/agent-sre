# Agent SRE

An autonomous reliability agent that debugs **other** AI agents by reading their **Arize Phoenix**
traces — *diagnose → measure → fix → verify → guard → prevent* — without a human touching the target
agent's code.

Built for the **Google Cloud Rapid Agent Hackathon, Arize track**. Gemini 3 via Vertex AI · Google
ADK · Arize Phoenix (tracing + evals) · Phoenix MCP (the SRE's action layer) · Cloud Run.

> **Status:** Phase 0 (setup & verification). See `docs/` for the full spec and task tracker.

## Layout

| Path | Purpose |
|---|---|
| `target_agent/` | The deliberately-broken DevOps agent the SRE debugs (Phase 1). |
| `agent_sre/` | The product — the reliability agent. `mcp_config.json` wires Phoenix MCP. |
| `cockpit/` | React + Vite UI streaming the SRE's step cards (Phase 3). |
| `scripts/` | Phase 0 verification: `model_probe.py`, `smoke_trace.py`, `mcp_smoke.py`. |
| `docs/` | Spec, fixtures/ground-truth, Arize integration tracker, Devpost skeleton. |

## Setup (Phase 0)

Prereqs: `uv`, Node (for `npx`), `gcloud`. Python is pinned to 3.12 via `.python-version`.

```bash
cp .env.example .env          # then fill in GCP + Phoenix values
uv sync                       # resolve deps on Python 3.12
```

**Interactive (needs your browser/login):**

```bash
# Phoenix Cloud: create a px_live_ key + space URL at https://app.phoenix.arize.com
# GCP:
gcloud auth login
gcloud config set project <PROJECT_ID>
gcloud auth application-default login
gcloud services enable run.googleapis.com aiplatform.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com
```

**Verify it all works:**

```bash
make model-probe   # locks GEMINI_MODEL (Gemini 3 if available, else gemini-2.5-flash)
make smoke-trace   # one ADK turn -> a trace appears in your Phoenix project
make mcp-smoke     # Phoenix MCP server starts and lists its tools
```

Phase 0 is green when all three pass and the trace is visible in the Phoenix UI.

## Credits & license

Wiring patterns (Phoenix `register(...)` instrumentation, ADK agent/tool structure, env layout)
adapted from the Apache-2.0 [`Arize-ai/gemini-hackathon`](https://github.com/Arize-ai/gemini-hackathon)
starter. Licensed under **Apache-2.0** — see `LICENSE`.
