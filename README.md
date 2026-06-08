# Agent SRE

An autonomous reliability agent that debugs **other** AI agents by reading their **Arize Phoenix**
traces — *diagnose → measure → fix → verify → guard → prevent* — without a human touching the target
agent's code.

Built for the **Google Cloud Rapid Agent Hackathon, Arize track**. Gemini via Vertex AI · Google
ADK · Arize Phoenix (tracing + evals) · Phoenix MCP (the SRE's action layer) · Cloud Run.

> **🔗 Live demo:** https://agent-sre-389498242223.us-central1.run.app — **password: `admin2000`**
> Click **Run incident** once → watch the whole loop run autonomously: the broken agent fails, the
> SRE diagnoses it via Phoenix MCP, proves the bug (0/1), patches the prompt, re-runs live to **1/1**
> (`healthy ❌ → paged ✅`), then Guard 4/4 and Prevent. (The password is a light bot-deterrent —
> remove it by unsetting `APP_PASSWORD`.)

## What it does (the six-step loop)

1. **Diagnose** — an ADK agent reads the target's Phoenix traces via the **Phoenix MCP server**,
   walks the spans, and pinpoints the bad tool argument.
2. **Measure** — a Gemini LLM-judge proves the failure with a **0/1** baseline eval.
3. **Fix** — patches the target's prompt live via the MCP `upsert-prompt` tool.
4. **Verify** — re-runs the same case live; the eval flips **0/1 → 1/1** and the output flips
   `healthy ❌ → paged ✅`.
5. **Guard** — replays a golden set as a **Phoenix experiment** → no regressions (4/4).
6. **Prevent** — saves the failure as a permanent dataset example via MCP `add-dataset-examples`.

Plus a **live Drift watch**: the SRE triages a second, intermittently-buggy agent from real traces.

## Architecture

```
 Browser ── React cockpit (SSE) ──► FastAPI (agent_sre/server.py) on Cloud Run
                                       │
                 ┌─────────────────────┼──────────────────────────┐
                 ▼                     ▼                            ▼
        Target agent (ADK)      Agent SRE (ADK)            arize-phoenix (Python)
        Gemini via Vertex   ──► Phoenix MCP toolset  ◄──   evals + experiments
        instrumented ───────►  (npx @arizeai/phoenix-mcp)
                 │                     │  reads traces/spans, upsert-prompt,
                 ▼                     ▼  add-dataset-examples
            Arize Phoenix Cloud  ◄─────┘  (traces · prompts · datasets · experiments)
```

The **SRE's toolset is the Phoenix MCP server** (Diagnose/Fix/Prevent). The eval + experiment
*execution* runs in the `arize-phoenix` Python client (what MCP can't do).

## Layout

| Path | Purpose |
|---|---|
| `target_agent/` | The deliberately-broken DevOps agent the SRE debugs (+ a 2nd intermittent-bug agent). |
| `agent_sre/` | The product — the reliability agent: MCP toolset, eval, fix, guard, prevent, drift, server. |
| `cockpit/` | React + Vite UI streaming the SRE's step cards over SSE. |
| `scripts/` | Setup/verification + `deploy_cloud_run.sh`. |
| `docs/` | Spec, fixtures/ground-truth, Arize integration tracker, Devpost writeup. |

## Run it

Prereqs: `uv`, Node (for `npx`), `gcloud`. Python is pinned to 3.12. Copy `.env.example` → `.env` and
fill in GCP + Phoenix values, then `make setup`. Auth: `gcloud auth login` + `gcloud auth
application-default login`.

```bash
make spine      # CLI: the live spine — Measure → Fix (MCP) → Verify (0/1 → 1/1)
make guard      # golden-set replay as a Phoenix experiment (4/4)
make prevent    # save the failing case via MCP add-dataset-examples
make drift-seed # generate the 2nd-bug traces (run once)

make server     # cockpit backend on :8000   (open http://localhost:8000 once built)
make cockpit    # cockpit dev server on :5173 (proxies /api → :8000)
```

## Deploy (Cloud Run)

One command builds the Python+Node container (the cockpit + the npx Phoenix MCP server), stores the
Phoenix key in Secret Manager, grants the runtime SA Vertex access, and deploys a public service:

```bash
make deploy     # scripts/deploy_cloud_run.sh -> prints the live URL
```

## Demo video — ~3-min shot list

1. Open the live URL; read the broken agent's `healthy ❌` answer (wrong service name in the trace).
2. **Diagnose** card: the SRE calls Phoenix MCP (`list-traces`/`get-spans`) and names the bad arg.
3. **Measure** card: `0/1 FAIL` baseline (the bug is proven, not asserted).
4. Click **Apply Fix** → the prompt diff is applied via MCP `upsert-prompt`.
5. **Verify** card: live re-run flips `0/1 → 1/1` and `healthy ❌ → paged ✅` (the climax).
6. Click **Guard & Prevent**: golden set `4/4` (Phoenix experiment link) + failure saved via MCP.
7. Point at the **Drift watch** line: live triage of a 2nd intermittent bug. Close on the Phoenix UI.

## Credits & license

Wiring patterns (Phoenix `register(...)` instrumentation, ADK agent/tool structure, env layout)
adapted from the Apache-2.0 [`Arize-ai/gemini-hackathon`](https://github.com/Arize-ai/gemini-hackathon)
starter. Licensed under **Apache-2.0** — see `LICENSE`.
