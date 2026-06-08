# Devpost Writeup — Agent SRE (skeleton)

> Fill on Day 3. Drafting the skeleton now is a forcing function: if a section won't write
> crisply, the idea has a hole — find it before building, not after.

---

## Inspiration

Every team is shipping AI agents, and when an agent gives a wrong answer in production, nobody can
quickly say *why*. Debugging means a human manually reading hidden trace logs, guessing a fix, and
re-testing — slow, manual, expert-only. We asked: what if an agent could do that job itself?

## What it does

Agent SRE is an autonomous reliability agent that debugs **other** AI agents. Point it at a failing
agent and a complaint, and it:
1. **Diagnoses** the root cause by reading the agent's Phoenix traces and walking the spans.
2. **Measures** the failure by generating an eval and establishing a baseline (it proves the bug exists before fixing it).
3. **Fixes** the agent by patching its prompt.
4. **Verifies** the fix by re-running the failing case live and watching the eval pass.
5. **Guards** against regressions by replaying a golden set.
6. **Prevents** recurrence by saving the failure as a permanent test.

All without a human touching the target agent's code.

## Demo

We show Agent SRE debugging a DevOps incident-triage agent that falsely reported a production
service "healthy" when it was actually failing — because it queried the wrong service name. Agent
SRE finds the root cause across spans, proves the failure with a generated eval (0/1), fixes the
prompt, and re-runs live to 1/1 — the agent now correctly pages the right team. Accuracy on that
failure class goes from 0% to 100%, verified on camera.

## How we built it

- **Gemini (2.5 Flash) via Vertex AI** as the reasoning brain for both the target agent and Agent
  SRE, pinned at temperature 0 so the demo spine is deterministic.
- **Google ADK** for code-owned agent runtimes (required for full OpenInference instrumentation).
- **Arize Phoenix** for tracing (OpenInference auto-instrumentation) and the eval/experiment engine.
- **Phoenix MCP server** as Agent SRE's action layer — it reads traces/spans (Diagnose), updates the
  target's prompt via `upsert-prompt` (Fix), and saves regression examples via `add-dataset-examples`
  (Prevent). The eval and experiment *execution* run in the `arize-phoenix` Python client (the one
  thing the MCP server doesn't do) — a deliberate hybrid.
- **React + Vite** cockpit that streams each step of the SRE's work as a live card over SSE.
- **Cloud Run** for public hosting (one container running both the Python app and the npx MCP server).

## What makes it novel

Most "self-correcting" agents check their own work internally. Agent SRE is *external and general* —
a separate agent that debugs *any* Gemini agent via its observability data, finds root causes the
original agent can't see about itself, and proves every fix with a measurable before/after. The
eval-before-fix step makes the improvement non-fakeable.

## Challenges

- **Cross-span causal diagnosis.** The bug's *cause* (a `get_pod_logs("payment")` call with the
  wrong arg) and its *symptom* (a false "healthy" verdict) live in different spans. Getting the SRE
  to walk the trace via MCP and name the cause — not just restate the symptom — was the core problem.
- **Keeping the re-run truly live.** For Verify to be non-fakeable, the target agent had to load its
  instruction *from Phoenix* and rebuild per run, so the MCP `upsert-prompt` fix takes effect on the
  very next invocation (even in the same process). Several beats hinged on getting this right.
- **MCP prompt-name normalization.** `upsert-prompt` silently strips separators from prompt names
  (`incident-triage-agent` → `incidenttriageagent`), so the SRE was patching a *different* prompt
  than the agent read — Verify wouldn't flip until we switched to a separator-free identifier.
- **Guard exposed a sloppy fix.** Our first prompt hard-coded the payments service, so the golden set
  was meaningless. Guard caught it and forced a *general* agent + a contradiction-conditional rule —
  the regression gate doing exactly its job.
- **One container, two runtimes.** The SRE spawns the Phoenix MCP server via `npx`, so the Cloud Run
  image needed both Python and Node, with the MCP package pre-warmed and Vertex auth via the runtime
  service account.

## Accomplishments we're proud of

- **The live 0→100% verification.** On camera, the same failing case goes `0/1 → 1/1` and the output
  flips `healthy ❌ → paged ✅` — fixed by an agent, proven by an eval, with nothing pre-recorded.
- **The full diagnose→prevent loop closes autonomously** — Diagnose and Fix and Prevent all through
  the Phoenix MCP server; Measure/Guard through the Phoenix experiment engine; Guard is a real 4/4.
- **A live second bug.** Beyond the scripted spine, the SRE triages an intermittently-buggy agent
  from real traces — showing it handles a messy backlog, not just one staged failure.
- **Deterministic where it matters, real everywhere else.** The spine is pinned; the drift number is
  read live from actual traces and honestly varies.

## What we learned

- **Observability is a control surface, not just a dashboard.** Once an agent's traces and prompts
  are first-class objects (Phoenix + MCP), a *second* agent can close the loop on them — read, judge,
  patch, verify — without touching the first agent's code.
- **MCP is the right action layer, but not the measurement engine.** Reads, prompt updates, and
  dataset writes belong in MCP; running an eval/experiment belongs in the Python client. The hybrid
  is a feature, not a workaround.
- **A regression gate changes the design, not just the test suite.** Guard forced a more honest,
  general agent — proof that "prove the fix didn't break anything" pays for itself immediately.

## What's next

- Generalize beyond prompt fixes to tool-schema and routing fixes.
- Continuous mode: watch production traces and open fixes proactively (the Drift capability).
- Support multiple target-agent frameworks.

## Built with

`gemini-2.5-flash` · `google-adk` · `vertex-ai` · `arize-phoenix` · `phoenix-mcp` · `react` · `vite` · `cloud-run` · `python`

## Track

Arize.

---

### Submission checklist (Day 3)
- [x] Public hosted URL (Cloud Run), runs for judges →
      **https://agent-sre-389498242223.us-central1.run.app** (cold-visit verified)
- [~] Repo created (private `ik-labs/agent-sre`, Apache-2.0) — **flip to public before submitting**
      so the license is detectable in GitHub "About".
- [ ] ~3-min demo video on YouTube/Vimeo, English/subtitled (shot list in README) — **user records**
- [x] This writeup completed (fill any final polish before submitting)
- [ ] Track selected (Arize) + Devpost form submitted — **user submits**
- [ ] Submitted with buffer before June 11, 2:00 PM PDT
