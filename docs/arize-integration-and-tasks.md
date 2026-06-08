# Arize / Phoenix Integration & Task Tracker — Agent SRE

> Grounded in current Phoenix docs (verified June 2026). This is the doc you follow for the
> Arize-specific wiring AND for tracking build progress. Check the boxes as you go.
> Companion to `agent-sre-build-spec.md`, `CLAUDE.md`, `fixtures-and-ground-truth.md`.

---

## CRITICAL ARCHITECTURE FACT (read first)

**The Phoenix MCP server does NOT run evals or execute experiments.** Its tool surface is:
projects · traces · spans · sessions · annotations · prompts (create/list/update) ·
datasets + experiments (explore / pull results).

It **reads** observability data, **manages** prompts, and **explores** datasets/experiments —
but the *actual running* of an eval and *executing* an experiment is done with the Phoenix
**Python client + eval framework**, not through MCP.

**Therefore the SRE is HYBRID:**
- **Via Phoenix MCP (the "superpower" the hackathon requires):** query traces/spans to diagnose,
  read experiment results, create/update the target agent's prompt (the "fix"), explore/create datasets.
- **Via Phoenix Python libs (`arize-phoenix`):** run the LLM-as-judge eval, execute the
  experiment/replay over the golden set.

Frame the MCP usage as the SRE's primary action layer (it satisfies "meaningful use of MCP"),
and the Python eval libs as the measurement engine behind steps 2/4/5. Do not waste time hunting
for an MCP "run_eval" tool — it isn't there.

**UPDATE (verified live 2026-06-08, phoenix-mcp-server v1.1.0, 27 tools):** the MCP surface is
RICHER than first assumed. It DOES include dataset *writes* and experiment *reads*:
- `upsert-prompt` → **Fix (step 3)** via MCP. ✅
- `add-dataset-examples` → **Prevent (step 6) is fully doable via MCP** (no Python client needed). ✅
- `list-experiments-for-dataset`, `get-experiment-by-id`, `get-dataset-experiments` → read
  experiment *results* via MCP for **Guard (step 5)**.
- Still NO "run experiment" / "run eval" tool → executing the eval + experiment stays in the
  `arize-phoenix` Python client (steps 2/4 + running step 5). Reading their outcomes is MCP.
Full live tool list: list/get/upsert-prompt (+versions/tags), list-datasets, get-dataset,
get-dataset-examples, add-dataset-examples, get-dataset-experiments, list-experiments-for-dataset,
get-experiment-by-id, list-projects, get-project, list-traces, get-trace, get-spans,
get-span-annotations, list-sessions, get-session, list-annotation-configs, phoenix-support.

---

## Package & version reference (verified)

```
# Tracing (target agent + SRE)
pip install openinference-instrumentation-google-adk google-adk arize-phoenix-otel
# Evals + experiments engine (the SRE's measurement)
pip install arize-phoenix
# Phoenix MCP server (the SRE's action layer) — Node, run via npx
npx -y @arizeai/phoenix-mcp@latest --baseUrl <phoenix-url> --apiKey <key>
```
- `openinference-instrumentation-google-adk` ~0.1.10+ (auto-instruments ADK agent + tool + Gemini calls).
- `@arizeai/phoenix-mcp` ~4.0.8 — **Elastic License 2.0** (source-available; fine for hackathon use,
  NOT MIT — don't mislabel in the writeup). Your own repo stays MIT/Apache-2.0.
- Phoenix Cloud free tier OR self-host via Docker (`arizephoenix/phoenix`). Cloud is faster to set up;
  use it unless you need offline.

---

## Tracing wiring (verified, with the Agent Engine gotcha)

### Local / Cloud Run (simplest)
```python
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

tracer_provider = register(
    project_name="incident-agent",   # the TARGET agent's project
    auto_instrument=True,
)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
# target agent code here -> all ADK/tool/Gemini calls now stream to Phoenix
```
Env:
```
export PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/<your-space>/v1/traces"
export PHOENIX_API_KEY="<key>"
export GOOGLE_GENAI_USE_VERTEXAI=1     # use Vertex, not AI Studio (scored requirement)
```

### IF deploying the target agent to Vertex Agent Engine (only if you go that route)
**Gotcha — get this wrong and traces silently drop:**
```python
tracer_provider = register(
    project_name="incident-agent",
    batch=False,                       # sync export: Agent Engine pauses CPU after requests
    set_global_tracer_provider=False,  # Vertex manages global OTEL state; avoid the conflict
)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
```
- Instrumentation MUST live INSIDE the remote agent module passed to `agent_engines.create(...)`,
  NOT in the local driver script. Local instrumentation does not propagate to the remote runtime.
- Add to `requirements`: `arize-phoenix-otel`, `openinference-instrumentation-google-adk`.

**Recommendation:** for a 3-day build, run the target agent on **Cloud Run** (simpler tracing),
not Agent Engine, unless you specifically want the Agent Engine story. The local register() block
above is enough. Decide Day 1, don't waffle.

---

## The two Phoenix projects

Use separate `project_name`s so the SRE's own traces don't pollute the target's:
- `incident-agent` — the target agent's traces (what the SRE reads/diagnoses).
- `agent-sre` — the SRE's own traces (nice-to-have; shows the SRE is itself observable).

---

## SRE → Phoenix MCP client wiring

The SRE consumes `@arizeai/phoenix-mcp` as an MCP client. In ADK, register it as an MCP toolset
pointed at your Phoenix instance. Tools the SRE will actually call:
- list/query projects, traces, spans  → **Diagnose** (step 1)
- get prompt / update prompt           → **Fix** (step 3)
- create dataset / add examples        → **Prevent** (step 6) and golden-set setup
- pull experiment results              → **Guard** (step 5, reading the replay outcome)

Verify the exact MCP tool names at build time with the phoenix-docs MCP server or the repo README
(`Arize-ai/phoenix/js/packages/phoenix-mcp`). Tool names may differ slightly from the labels above.

---

## Eval + experiment engine (Python, behind steps 2/4/5)

The measurement the MCP server can't do. Use `arize-phoenix` eval framework:
- **Step 2 (Measure):** define the LLM-as-judge from `fixtures-and-ground-truth.md`, run it over the
  failing span(s), assert a **0/1 FAIL baseline**.
- **Step 4 (Verify):** after the prompt fix, re-run the same case, run the same eval → **1/1 PASS**.
- **Step 5 (Guard):** build a dataset of the golden-set incidents, run an experiment replaying them
  through the patched agent, score with the eval, assert all PASS.
- Pin judge model + temperature 0 for deterministic verdicts (see determinism checklist in fixtures doc).

---

## GCP — setup & deployment (the hackathon REQUIRES Google Cloud)

Everything runs on GCP: Gemini via Vertex AI, and the agents hosted on Cloud Run. This section is
the end-to-end path. **Recommended host = Cloud Run** (one-command deploy, simplest tracing).
Agent Engine and GKE are heavier and unnecessary for a 3-day demo.

### One-time GCP project setup (Phase 0)
```bash
# Install + auth
gcloud auth login
gcloud config set project PROJECT_ID
gcloud auth application-default login      # ADC — lets ADK authenticate to Vertex locally

# Enable the APIs you need
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com
```
IAM roles you need on the project (ask admin if not owner):
- `roles/run.sourceDeveloper` (deploy to Cloud Run)
- `roles/aiplatform.user` (call Vertex/Gemini)

Credits: the $100 GCP credit form closed June 4 — credits now first-come while supplies last.
The no-cost Vertex trial still works. A 3-day demo's Gemini + Cloud Run spend is small; the real
exposure is the hosted endpoint running through judging (June 22 – July 6) — keep it deployed but
low-traffic.

### Environment variables (Vertex, not AI Studio — scored)
```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=PROJECT_ID
GOOGLE_CLOUD_LOCATION=us-central1     # or your chosen supported region — pick one, don't switch
```
Note: this differs from the AI-Studio path (`GOOGLE_GENAI_USE_VERTEXAI=0` + `GOOGLE_API_KEY`).
We are on Vertex, so use the project/location form above.

### Deploy to Cloud Run — the one-command path
ADK has a built-in deploy command that packages the agent, builds the container, pushes to
Artifact Registry, and deploys to Cloud Run in one step (no hand-written Dockerfile needed):
```bash
adk deploy cloud_run \
  --project=PROJECT_ID \
  --region=us-central1 \
  --service_name=incident-agent \
  --with_ui \
  ./target_agent           # path to the agent package (folder with root_agent defined)
```
- `--with_ui` bundles the ADK dev UI with the API server — handy for judges to poke at the target agent.
- The command outputs a public Cloud Run URL. That URL (or the cockpit's URL) is your hackathon
  "hosted project" submission requirement.
- `root_agent` must be the exported entry point in the package — ADK's deploy looks for it.

### What gets deployed (three services, or fold into fewer)
- `target_agent` — the broken DevOps agent (Cloud Run service, instrumented → traces to Phoenix).
- `agent_sre` + `cockpit` — the SRE backend + React cockpit. Simplest: serve the cockpit static
  build from the SRE's FastAPI/Cloud Run service so there's ONE public URL judges visit.
- The Phoenix MCP server runs as a client-side process the SRE spawns (npx) — it does NOT need its
  own Cloud Run service. Phoenix itself = Phoenix Cloud (free tier), no deploy needed.

### Deploy gotchas
- **Tracing on Cloud Run:** the simple `register(...)` block (top of this doc) works as-is. You do
  NOT need the Agent Engine `batch=False` / `set_global_tracer_provider=False` workaround on Cloud
  Run — that's Agent-Engine-only. Don't copy it where it isn't needed.
- **Secrets:** never hardcode `PHOENIX_API_KEY` or keys in the image. Pass as Cloud Run env vars /
  Secret Manager at deploy time.
- **Region consistency:** keep Vertex `GOOGLE_CLOUD_LOCATION` and the Cloud Run `--region` aligned
  to avoid cross-region latency and confusion. Pick `us-central1` and stick to it.
- **Unauthenticated access:** judges need to reach it without your creds — allow unauthenticated
  invocations on the public service (unless org policy forbids, in which case use Testing-private-services).
- **Cold starts:** Cloud Run scales to zero; first hit after idle is slow. For the demo + judging
  window, set `--min-instances=1` on the public service so it's warm.

---

## TASK TRACKER

### Phase 0 — Setup & verification (Day 1 morning) — ✅ GREEN (2026-06-08)
- [x] Clone `Arize-ai/gemini-hackathon` starter; confirm it exists + matches assumptions.
      (Inspected via `gh api`; wiring patterns reused. Apache-2.0.)
- [x] Create Phoenix Cloud account; grab space endpoint + API key.
      (Space `phx-jp`; JWT-format key — not `px_live_`, both are valid.)
- [x] GCP: `gcloud auth login`, set project, `gcloud auth application-default login` (ADC).
      (Project `agent-sre-hk` #389498242223; ADC quota project aligned.)
- [x] GCP: enable run / aiplatform / artifactregistry / cloudbuild APIs (see GCP section).
- [~] GCP: confirm IAM roles `run.sourceDeveloper` + `aiplatform.user`.
      (`aiplatform.user` confirmed — Vertex calls succeed. `run.sourceDeveloper` deferred to deploy.)
- [x] Confirm Vertex AI access + Gemini model in your region; set Vertex env vars.
      (**Locked `gemini-2.5-flash` in `us-central1`** — pinned for determinism. Gemini 3 IDs 404 in
      this project on both regional + `global` endpoints; `-latest` aliases avoided (non-deterministic).
      One-line `.env` swap if Gemini 3 becomes available.)
- [x] `pip install` the Python deps (`uv sync`); `npx` the MCP server; confirm it lists tools.
      (**27 tools**; `list-projects` reaches space; `incident-agent` project created by smoke trace.)
- [x] Lock host = Cloud Run; region `us-central1`.
- [x] Init fresh repo, Apache-2.0 license, first commit (`59960d6`). **TODO:** push to a *public*
      GitHub remote before submission (license must be detectable in GitHub "About").

### Phase 1 — Target agent + tracing (Day 1) — ✅ DONE (2026-06-08)
- [x] Build minimal DevOps incident agent in `target_agent/` with 4 mock tools (`fixtures.py`).
- [x] Inject the wrong-arg bug (`payment` vs `payments`) per fixtures doc.
      (Bug lives in `prompt.py` — step 2 hardcodes `get_pod_logs("payment")` — so Phase-2 Fix can
      patch it via `upsert-prompt`. Determinism: `temperature=0`.)
- [x] Wire `register()` (auto_instrument); run the incident; confirm traces in Phoenix.
      (`make incident` reproduces the chain deterministically: metrics("payments")=0.38 ->
      pod_logs("payment")="no logs found" -> no page -> `VERDICT: healthy`.)
- [x] Confirm the failing trace shows the cause span ≠ symptom span.
      (Verified via MCP `get-spans span_kinds=[TOOL]` on trace `2ad7fd4d…`: span
      `execute_tool get_pod_logs` carries `tool.parameters.service="payment"` +
      `tool_response={"result":"no logs found"}` — distinct from the LLM "healthy" conclusion span.
      This is the exact attribute the SRE's Diagnose step will read.)

### Phase 2 — SRE spine: Diagnose → Measure → Fix → Verify (Day 2) — ✅ PROVEN (2026-06-08)
- [x] SRE connects to Phoenix MCP; **Diagnose**: queries traces, walks spans, outputs root cause + bad arg.
      (`agent_sre/sre_agent.py` ADK LlmAgent + MCPToolset; `make diagnose` → calls list-traces +
      get-spans, names `get_pod_logs(service="payment")` as cause span.)
- [x] **Measure**: Gemini LLM-judge (temp 0), runs it → **0/1 FAIL baseline** (`agent_sre/eval.py`).
- [x] **Fix**: SRE proposes prompt diff, applies via MCP **`upsert-prompt`** (`agent_sre/fix.py`).
- [x] **Verify**: re-run the same case LIVE → eval flips **1/1 PASS**; output flips `healthy ❌`→`paged ✅`.
      (`agent_sre/run_spine.py`, `make spine` — fully reproducible, resets to buggy baseline first.)
- [x] ⭐ The non-fakeable beat works end-to-end. Foundation for prereqs:
  - **Step 0** (`prompt_source.py`): agent loads its instruction from the Phoenix prompt store and
    `build_agent()` rebuilds per run, so the fix takes effect on the very next run (even same-process).
  - **GOTCHA recorded:** Phoenix MCP `upsert-prompt` **strips separators from the prompt name**
    (`incident-triage-agent` → `incidenttriageagent`) while the Python client preserves them. Use a
    separator-free lowercase identifier (`incidenttriageagent`) so the prompt the agent READS and the
    prompt the SRE PATCHES are the same object. This silently broke Verify until fixed.

### Phase 3 — Cockpit UI (Day 2, parallel) — ✅ DONE (2026-06-08)
- [x] React+Vite+TS, two-column layout (`cockpit/`), flat/legible, no UI lib.
- [x] Stream Diagnose/Measure/Fix/Verify cards live (SSE via `EventSource`).
- [x] Verify card: eval bar `0/1→1/1` + `healthy ❌ → paged ✅` output flip, made unmissable.
- [x] Fix card: prompt diff (colored) + **Apply Fix** button (interactive pause for human approval).
- Backend: `agent_sre/server.py` (FastAPI, `GET /api/run` + `GET /api/apply` SSE) over
  `agent_sre/orchestrator.py` (async generators reusing the proven spine functions). Single public
  URL: FastAPI serves `cockpit/dist` at `/` (verified: static + API coexist on :8000).
  Run dev: `make server` + `make cockpit`; or build (`cd cockpit && npm run build`) and open
  http://localhost:8000. **TODO (Phase 5):** add an auth/rate-limit gate before public deploy
  (endpoints mutate the Phoenix prompt + call Gemini per request).

### Phase 4 — Depth: Guard + Prevent (Day 3) — ✅ DONE LIVE (2026-06-08)
- [x] **Guard**: `golden-incidents` dataset + Phoenix **experiment** replay through the patched
      agent → **4/4 PASS** (`agent_sre/guard.py`, `make guard`). Experiment URL surfaced + readable
      via MCP. Deterministic rule evaluator (`agent_sre/golden.py`).
- [x] **Prevent**: save the failing case as a permanent example via MCP **`add-dataset-examples`**
      into `sre-regressions` (`agent_sre/prevent.py`, `make prevent`).
- [x] 2nd bug (intermittent tool-selection) is **LIVE, not shown**: `target_agent/drift_agent.py`
      (temp 0.9) + `make drift-seed` emits ~14 real traces to a `drift-watch` project;
      `agent_sre/drift.py` triages them via MCP (diagnose-only).
- [x] "Drift" tab is **live** (`/api/drift` → "N/14 traces skipped log inspection").
- Cockpit shows the full 6-step loop: Diagnose · Measure · Fix · Verify · Guard · Prevent, with a
  "Guard & Prevent" button after Verify. SSE: `/api/guard`, `/api/drift`.
- **Two gotchas recorded:**
  1. Guard exposed that a payments-hardcoded prompt makes the golden set meaningless → **generalized
     the target prompt** (triage the reported service; bug = payments-specific internal-label note)
     and made `FIX_RULE` contradiction-conditional (empty logs + HIGH error rate ≠ healthy).
  2. Tracing project routing: importing the `target_agent` package eagerly imported `agent.py` →
     `setup_tracing(incident-agent)`, and the global tracer singleton then ignored the drift script's
     `drift-watch` registration. Fixed by exposing `root_agent` lazily via `__getattr__`.

### Phase 5 — Ship (Day 3 afternoon/evening)
- [ ] Deploy to Cloud Run via `adk deploy cloud_run ... --with_ui --min-instances=1` (see GCP section).
- [ ] Allow unauthenticated access; confirm public URL works for a cold visitor (not just you).
- [ ] Record 3-min demo video (script in build spec); upload to YouTube/Vimeo, subtitle if needed.
- [ ] Fill the 3 open sections of `devpost-writeup-skeleton.md`.
- [ ] Repo public, license detectable in GitHub "About", README with run instructions.
- [ ] Select Arize track; submit Devpost form WITH BUFFER before June 11, 2:00 PM PDT.

---

## Risk log (update as you hit things)
- [ ] MCP tool names differ from assumptions → verify via phoenix-docs MCP / README, adjust calls.
- [ ] Gemini 3 model string / Vertex region issues → confirm Day 1.
- [ ] Agent Engine drops traces → use Cloud Run, or apply the `batch=False`+`set_global_tracer_provider=False` fix.
- [ ] Eval verdict non-deterministic → pin model + temperature 0.
- [ ] Live re-run too slow on camera → stream partial card results; pre-warm one run for tempo (never fake).

---

## Verify-before-trust note
Package versions and MCP tool names were accurate as of June 2026 research but this ecosystem
churns fast (100 commits/month on the Phoenix monorepo). Re-confirm the MCP tool list and the
ADK instrumentation snippet against live docs in Phase 0 before building on them.
