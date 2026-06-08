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

- **Gemini 3** via Vertex AI as the reasoning brain for both the target agent and Agent SRE.
- **Google ADK** for code-owned agent runtimes (required for full instrumentation).
- **Arize Phoenix** for tracing (OpenInference auto-instrumentation) and evals.
- **Phoenix MCP server** as Agent SRE's toolset — it reads traces, runs evals, updates prompts, and
  runs experiments entirely through MCP. This is the "action layer."
- **React + Vite** cockpit that streams each step of the SRE's work as a live card.
- **Cloud Run** for public hosting.

## What makes it novel

Most "self-correcting" agents check their own work internally. Agent SRE is *external and general* —
a separate agent that debugs *any* Gemini agent via its observability data, finds root causes the
original agent can't see about itself, and proves every fix with a measurable before/after. The
eval-before-fix step makes the improvement non-fakeable.

## Challenges

<!-- fill on Day 3: e.g. cross-span causal tracing, keeping the re-run truly live, MCP client wiring -->

## Accomplishments we're proud of

<!-- fill: the live 0→100% verification; the full diagnose→prevent loop closing autonomously -->

## What we learned

<!-- fill -->

## What's next

- Generalize beyond prompt fixes to tool-schema and routing fixes.
- Continuous mode: watch production traces and open fixes proactively (the Drift capability).
- Support multiple target-agent frameworks.

## Built with

`gemini-3` · `google-adk` · `vertex-ai` · `arize-phoenix` · `phoenix-mcp` · `react` · `vite` · `cloud-run` · `python`

## Track

Arize.

---

### Submission checklist (Day 3)
- [ ] Public hosted URL (Cloud Run), runs for judges
- [ ] Public repo, OSS license detectable in GitHub "About"
- [ ] ~3-min demo video on YouTube/Vimeo, English/subtitled, shows it functioning
- [ ] This writeup completed
- [ ] Track selected (Arize) + Devpost form submitted
- [ ] Submitted with buffer before June 11, 2:00 PM PDT
