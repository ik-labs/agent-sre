"""Guard step — replay the golden set through the PATCHED agent and prove no regressions.

Source of truth = a deterministic async replay of each golden incident (clean, reliable). We then
log those results to Phoenix as a real **experiment** over a golden-incidents **dataset** (so the
gate is visible in Phoenix and readable via MCP). The experiment task returns the precomputed result
(instant, sync) — this avoids re-running the agent and any event-loop conflict with run_experiment.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Optional

from agent_sre.fix import FIX_RULE, apply_fix, compute_fixed_instruction
from agent_sre.golden import GOLDEN, case_passed, paged_team
from target_agent.prompt_source import PROMPT_IDENTIFIER, load_instruction
from target_agent.run_incident import run as run_incident

DATASET_NAME = "golden-incidents"


def _is_fixed(text: str) -> bool:
    # FIX_RULE is only present once the SRE has applied the fix (the reset/buggy prompt lacks it).
    return FIX_RULE in text


def ensure_fixed() -> None:
    """Guard tests the patched agent — apply the fix if the current Phoenix prompt lacks it."""
    text = load_instruction()
    if _is_fixed(text):
        return
    apply_fix(compute_fixed_instruction(text))
    for _ in range(20):
        if _is_fixed(load_instruction()):
            return
        time.sleep(1)


async def _replay() -> list[dict]:
    """Run every golden incident through the patched agent. Authoritative pass/fail."""
    rows: list[dict] = []
    for case in GOLDEN:
        res = await run_incident(case["incident"])
        team = paged_team(res["calls"])
        passed = case_passed(case["expect_page"], case["expect_team"], res["calls"])
        rows.append(
            {
                "label": case["label"],
                "incident": case["incident"],
                "expect_page": case["expect_page"],
                "expect_team": case["expect_team"],
                "paged_team": team,
                "passed": passed,
                "final": res["final"],
            }
        )
    return rows


def _log_experiment(rows: list[dict]) -> Optional[str]:
    """Best-effort: record the replay as a Phoenix dataset + experiment. Returns the experiment URL."""
    try:
        from phoenix.client import Client

        client = Client(
            base_url=os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or None,
            api_key=os.environ.get("PHOENIX_API_KEY") or None,
        )
        examples = [
            {
                "input": {"incident": r["incident"]},
                "output": {"expect_page": r["expect_page"], "expect_team": r["expect_team"]},
                "metadata": {"label": r["label"]},
            }
            for r in rows
        ]
        dataset = client.datasets.create_dataset(
            name=DATASET_NAME, examples=examples, input_keys=["incident"], output_keys=["expect_page", "expect_team"]
        )

        by_incident = {r["incident"]: r for r in rows}

        def task(example) -> dict:
            r = by_incident[example["input"]["incident"]]
            return {"paged_team": r["paged_team"], "final": r["final"]}

        def correctness(output, expected) -> float:
            team = (output or {}).get("paged_team")
            if expected.get("expect_page"):
                return 1.0 if team == expected.get("expect_team") else 0.0
            return 1.0 if team is None else 0.0

        experiment = client.experiments.run_experiment(
            dataset=dataset, task=task, evaluators=[correctness], experiment_name="guard-replay"
        )
        try:
            return client.experiments.get_experiment_url(
                dataset_id=experiment["dataset_id"], experiment_id=experiment["experiment_id"]
            )
        except Exception:
            return None
    except Exception as e:  # noqa: BLE001 — the experiment is the "nice to have"; replay is the truth
        print(f"[guard] Phoenix experiment logging skipped ({e!r})")
        return None


async def run_guard() -> dict:
    """Ensure patched, replay the golden set, log a Phoenix experiment. Returns rows + all_pass + url."""
    await asyncio.to_thread(ensure_fixed)
    rows = await _replay()
    all_pass = all(r["passed"] for r in rows)
    url = await asyncio.to_thread(_log_experiment, rows)
    return {"rows": rows, "all_pass": all_pass, "experiment_url": url, "total": len(rows),
            "passed": sum(1 for r in rows if r["passed"])}


if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    result = asyncio.run(run_guard())
    print("=== GUARD — golden-set replay (patched agent) ===")
    for r in result["rows"]:
        mark = "✅" if r["passed"] else "❌"
        paged = r["paged_team"] or "no page"
        print(f"  {mark} {r['label']:<32} -> {paged}")
    print(f"\n  {result['passed']}/{result['total']} PASS  ({'all green ✅' if result['all_pass'] else 'REGRESSION ❌'})")
    if result["experiment_url"]:
        print(f"  Phoenix experiment: {result['experiment_url']}")
    raise SystemExit(0 if result["all_pass"] else 1)
