# Fixtures & Ground Truth — Agent SRE

Single source of truth for the target agent's canned data, the injected bug, and the eval answer key.
Implement this in `target_agent/fixtures.py`. **Everything in the demo spine must be deterministic.**

---

## The scenario

Incident input (what the user/operator types to the target agent):

> "Payments service is throwing 500s in production. Investigate and page the right team if needed."

Ground-truth correct outcome: the `payments` service has repeated `connection refused` errors;
the **platform** team owns it and **must be paged** with a summary naming the connection errors.

---

## Mock tool behavior (canned)

### `get_pod_logs(service: str) -> str`
| arg | returns |
|---|---|
| `"payments"` (correct) | `"[12:01] ERROR connection refused upstream db\n[12:01] ERROR connection refused upstream db\n[12:02] ERROR connection refused upstream db"` |
| `"payment"` (the bug — singular) | `"no logs found"` |
| any other unknown service | `"no logs found"` |

### `get_metrics(service: str) -> dict`
| arg | returns |
|---|---|
| `"payments"` | `{"cpu": 41, "mem": 63, "error_rate": 0.38}` |
| `"checkout"` | `{"cpu": 22, "mem": 50, "error_rate": 0.01}` |
| unknown | `{"cpu": 0, "mem": 0, "error_rate": 0.0}` |

### `get_oncall(team: str) -> str`
| arg | returns |
|---|---|
| `"platform"` | `"Priya N. (platform on-call)"` |
| `"checkout"` | `"Sam R. (checkout on-call)"` |
| unknown | `"no on-call found"` |

### `page_oncall(team: str, summary: str) -> str`
Returns `f"paged {team}: {summary}"`. No side effects (mock).

### Service → team ownership map (ground truth)
- `payments` → `platform`
- `checkout` → `checkout`

---

## The injected bug (the spine)

**Location:** the target agent's system prompt refers to the service as `payment` (singular) in its
reasoning/instructions, OR a hardcoded constant `SERVICE = "payment"` used when building the
`get_pod_logs` call.

**Failure chain:**
1. Step 1 — agent reads `get_metrics("payments")` → sees `error_rate: 0.38` (high). So far correct.
2. Step 2/3 — agent calls `get_pod_logs("payment")` (singular, the bug) → `"no logs found"`.
3. Final — agent concludes **"No errors in logs — system healthy, no page needed."** ❌

**Symptom span:** the final "healthy" conclusion.
**Cause span:** the earlier `get_pod_logs("payment")` call with the wrong argument.
They are different spans — this is the "can't eyeball it" property.

**Correct behavior after fix:** `get_pod_logs("payments")` → finds connection-refused errors →
`get_oncall("platform")` → `page_oncall("platform", "payments: repeated connection refused to upstream db")` ✅

---

## The fix (what the SRE applies in step 3)

Prompt patch (diff the SRE proposes and applies via Phoenix MCP prompt-update):
- Correct `payment` → `payments`.
- Add rule: *"If a tool returns no data, do NOT conclude healthy. Re-check the service name against
  the metrics you already retrieved before concluding."*

---

## Eval rubric (step 2 — the fact-check)

LLM-as-judge prompt:
```
You are grading a DevOps incident-triage agent's handling of an incident.
GROUND TRUTH: the "payments" service had repeated "connection refused" errors; the platform team
SHOULD have been paged with a summary mentioning the connection errors.
Given the agent's final action, output PASS only if BOTH:
  (a) it identified the connection-refused errors, AND
  (b) it paged the "platform" team.
Otherwise output FAIL.
Return JSON only: {"verdict":"PASS|FAIL","reason":"<one sentence>"}
```

Expected verdicts:
- **Before fix:** `{"verdict":"FAIL","reason":"Concluded healthy; never found errors; paged no one."}` → **0/1**
- **After fix:** `{"verdict":"PASS","reason":"Found connection-refused errors and paged platform."}` → **1/1**

---

## Golden set (step 5 — regression gate)

Previously-passing incidents that must STILL pass after the fix. Keep ~4–5, all deterministic:

| incident | correct outcome |
|---|---|
| "checkout latency spike" | metrics show low error_rate → conclude healthy, no page ✅ |
| "checkout 500s reported" | logs clean for checkout → page checkout team only if errors; here conclude monitor ✅ |
| "payments healthy check" | (post-fix) correctly investigates payments, finds errors, pages platform ✅ |
| "unknown-service alert" | gracefully reports "service not found", no false page ✅ |

The gate replays these against the **patched** agent and confirms all green — proving the fix didn't
break the cases that already worked.

---

## Optional second bug (breadth only — diagnose, don't fix live)

**Intermittent wrong-tool selection.** ~30% of runs, the agent calls `get_metrics` when it should
call `get_pod_logs`. Isolate the randomness here only (the spine stays deterministic). The SRE
surfaces this in its triage list ("detected an intermittent tool-selection issue across 14 traces")
to show it handles a realistic mess — but does NOT run the full fix→verify loop on it live.

---

## Determinism checklist

- [ ] Same incident input → identical tool-call sequence → identical trace (spine only).
- [ ] Eval verdict is stable across runs (pin the judge model + temperature 0).
- [ ] Golden-set outcomes are fixed and reproducible.
- [ ] Randomness exists ONLY in the optional 2nd bug, never in the demoed spine.
