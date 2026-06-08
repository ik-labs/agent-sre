"""The live spine: Measure -> Fix -> Verify. The non-fakeable beat of the whole demo.

  ① MEASURE  run the (broken) target agent, judge it  -> 0/1 FAIL
  ② FIX      derive the corrected prompt, show the diff, apply via Phoenix MCP `upsert-prompt`
  ③ VERIFY   re-run the SAME case live; the target now pulls the new prompt -> 1/1 PASS
             output flips: healthy ❌ -> paged ✅

Repeatable: resets the Phoenix prompt to the buggy baseline first, so MEASURE is always 0/1.
Run: `make spine`  (or `uv run python -m agent_sre.run_spine`)
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")
sys.path.insert(0, str(_ROOT))

from agent_sre.eval import _print_card, measure  # noqa: E402
from agent_sre.fix import FIX_RULE, apply_fix, compute_fixed_instruction, reset_to_buggy, unified_diff  # noqa: E402
from target_agent.prompt_source import load_instruction  # noqa: E402


def _verdict_word(final: str) -> str:
    line = (final or "").splitlines()[-1] if final else ""
    return "paged ✅" if "paged" in line.lower() else ("healthy ❌" if "healthy" in line.lower() else "?")


def _wait_until(predicate: Callable[[str], bool], timeout: int = 20) -> bool:
    """Poll the Phoenix-sourced instruction until it satisfies predicate (prompt propagation)."""
    for _ in range(timeout):
        if predicate(load_instruction()):
            return True
        time.sleep(1)
    return False


async def main() -> int:
    print("AGENT SRE — LIVE SPINE  (Measure → Fix → Verify)\n" + "=" * 60)

    # Ensure a clean broken baseline (idempotent demo). Buggy prompt lacks the appended FIX_RULE.
    reset_to_buggy()
    _wait_until(lambda t: FIX_RULE not in t, timeout=20)

    # ① MEASURE
    m0 = await measure("① MEASURE — baseline (current Phoenix prompt)")
    _print_card(m0)
    print()

    # ② FIX
    print("② FIX — patch the target's prompt via Phoenix MCP `upsert-prompt`")
    buggy = load_instruction()
    fixed = compute_fixed_instruction(buggy)
    print("  proposed diff:")
    print("".join("    " + ln for ln in unified_diff(buggy, fixed).splitlines(keepends=True)))
    apply_fix(fixed)
    applied = _wait_until(lambda t: FIX_RULE in t, timeout=20)
    print(f"  new prompt version applied via MCP ✅  (visible to agent: {applied})")
    print()

    # ③ VERIFY (live re-run, same case)
    m1 = await measure("③ VERIFY — live re-run (new Phoenix prompt)")
    _print_card(m1)
    print()

    # Result
    print("=" * 60 + "\nRESULT")
    print(f"  eval:   {m0['score']}/1 {m0['verdict']}   →   {m1['score']}/1 {m1['verdict']}")
    print(f"  output: {_verdict_word(m0['final'])}   →   {_verdict_word(m1['final'])}")
    ok = m0["score"] == 0 and m1["score"] == 1
    print(
        "\n✅ SPINE PROVEN — 0/1 → 1/1, healthy → paged, fixed LIVE via Phoenix MCP."
        if ok
        else "\n⚠️  Spine did not flip as expected — inspect the cards above."
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
