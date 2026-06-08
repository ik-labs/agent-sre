# CLAUDE.md — Agent SRE

Persistent operating context for this project. Read this before every session.
Full design rationale lives in `agent-sre-build-spec.md`. This file is the *how we work*.

---

## What we're building (one line)

An autonomous reliability agent ("Agent SRE") that debugs **other** AI agents by reading their
Arize Phoenix traces — diagnose → measure → fix → verify → guard → prevent — without a human
touching the target agent's code.

Hackathon: Google Cloud Rapid Agent Hackathon, **Arize track**. Deadline **June 11, 2026, 2pm PDT**.

---

## The two agents — never confuse them

- **Target agent** = the fixture being debugged. A *minimal* DevOps incident-triage agent with
  **mock tools and canned data**. It is a stage prop. Keep it small and deliberately broken.
- **Agent SRE** = the product, the star. Domain-agnostic. Its toolset is the **Phoenix MCP server**.
  This is where real engineering effort goes.

If a task seems to be making the target agent bigger/more realistic, stop — that's scope creep.

---

## Non-negotiable guardrails

1. **New work only.** Fresh repo, fresh commits, contest period. No code copied from prior projects.
2. **No real infrastructure.** Target agent tools return canned data. Never stand up real k8s, real
   logs, real metrics, or external infra. Mock everything.
3. **The bug is a FACT, never a judgment.** The spine bug = wrong tool argument (`payment` vs
   `payments`) causing a false "all-clear". Verifiable from the trace in one second. Never introduce
   a bug whose "correct answer" is an opinion.
4. **The fix→verify re-run is LIVE.** The Eval Author step must establish a **0/1 FAIL baseline
   BEFORE the fix**. Then the fix is applied and the same case re-runs live to 1/1 PASS. This is the
   whole demo. Never fake it, never screenshot it.
5. **Gemini via Vertex AI** (not AI Studio). **Phoenix MCP consumed as a client.** Both are scored.
6. **The SRE is the star.** Always frame it as domain-agnostic; DevOps is just the demo fixture.

---

## Stack

- Language: Python (ADK), React + Vite (cockpit).
- Agent runtime: Google ADK, code-owned (Arize track forbids visual-Agent-Builder-only).
- Model: Gemini 3 via Vertex AI.
- Tracing: `openinference-instrumentation-google-adk` + `phoenix.otel.register` → Phoenix Cloud (free tier).
- SRE → observability: Arize Phoenix MCP server (`@arizeai/phoenix-mcp`), consumed by the SRE as an MCP client.
- Hosting: Cloud Run, public URL.
- License: MIT or Apache-2.0, detectable in GitHub "About".

**Day-1 verification (do before coding):** clone `Arize-ai/gemini-hackathon` starter, confirm it
exists and its wiring matches assumptions. Verify current OpenInference/ADK package names and the
Phoenix MCP client setup against live Phoenix docs — these package names churn.

---

## The SRE's six-step policy (implement as orchestration)

1. **Diagnose** — pull traces, walk spans backward from the wrong final answer, locate the bad span + bad arg.
2. **Measure** — synthesize an eval for this failure class, run it, get a **0/1 FAIL baseline**.
3. **Fix** — propose prompt patch (show diff), apply via Phoenix prompt-update MCP tool.
4. **Verify** — re-run the failing case LIVE, eval flips to 1/1 PASS, output flips `healthy ❌` → `paged ✅`.
5. **Guard** — replay golden set as a Phoenix experiment; confirm no regressions.
6. **Prevent** — save the failing case as a permanent dataset example.

**Live vs shown:** steps 3+4 must be live (the spine). Steps 2,5,6 live if time allows; 5 and 6 may
degrade to "shown" (pre-computed) if behind. Steps 1+3+4 alone are a complete winning demo.

---

## Build order

- **Day 1:** scaffold from starter; build target agent + mock tools + inject wrong-arg bug; confirm
  traces flow; wire SRE→Phoenix MCP; get Diagnose returning a real root cause.
- **Day 2:** Measure + Fix + Verify (the live spine). Build cockpit, stream the spine cards. If the
  day ends here, you can still submit and win.
- **Day 3:** Guard + Prevent (drop to "shown" if behind); add 2nd bug to triage list for breadth;
  deploy to Cloud Run; record 3-min video; Devpost writeup; submit with buffer.

---

## Cockpit (React)

Two columns. Left: target agent input + its wrong output. Right: SRE step cards streamed live
(Diagnose / Measure / Fix / Verify / Guard / Prevent). The Fix card shows the prompt diff + Apply
button. The Verify card is the climax: eval bar 0/1 → 1/1 and output `healthy ❌` → `paged ✅` —
make this unmissable. Small "Drift" tab is shown, not live. Flat, legible, no decorative noise.

---

## Coding conventions

- Keep the target agent in `target_agent/`, the SRE in `agent_sre/`, the cockpit in `cockpit/`.
- Fixtures/canned data live in `target_agent/fixtures.py` — single source of truth, see `fixtures-and-ground-truth.md`.
- Deterministic everything in the demo path: same incident input → same trace → same diagnosis.
  No randomness in the spine (the intermittent-bug randomness is isolated to the optional 2nd bug).
- Commit often with clear messages — the public commit history is part of the "new work" proof.
- Prefer working-and-simple over clever-and-fragile. This is a 3-day demo, not a product.
