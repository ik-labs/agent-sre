"""Prevent step — save the just-fixed failing case as a permanent dataset example via Phoenix MCP.

Uses the `add-dataset-examples` MCP tool (the MCP *write* path) so the exact failure that was
diagnosed becomes a permanent regression test. This is what stops the bug from silently returning.
"""

from __future__ import annotations

from agent_sre.mcp_client import PhoenixMCP
from target_agent.prompt import INCIDENT_INPUT

DATASET_NAME = "sre-regressions"

# The failing case the SRE diagnosed + fixed, captured as a permanent expectation.
FAILING_EXAMPLE = {
    "input": {"incident": INCIDENT_INPUT},
    "output": {
        "expect_page": True,
        "expect_team": "platform",
        "expect_errors": True,
        "expected_summary": "payments: repeated connection refused to upstream db",
    },
    "metadata": {
        "bug": 'wrong tool argument: get_pod_logs("payment") instead of "payments"',
        "root_cause": "prompt note used singular internal label 'payment'",
        "captured_by": "Agent SRE (diagnose -> fix -> prevent)",
        "service": "payments",
    },
}


def save_failing_case() -> dict:
    """Append the failing case to the `sre-regressions` dataset via MCP. Returns the MCP result."""
    with PhoenixMCP() as mcp:
        result = mcp.call(
            "add-dataset-examples",
            {"dataset_name": DATASET_NAME, "examples": [FAILING_EXAMPLE]},
        )
    return {"dataset": DATASET_NAME, "result": result}


def count_examples() -> int:
    """Best-effort read-back: how many examples are now in the regression dataset (via MCP)."""
    try:
        with PhoenixMCP() as mcp:
            data = mcp.call("get-dataset-examples", {"dataset_name": DATASET_NAME})
        if isinstance(data, dict):
            ex = data.get("data", {}).get("examples") or data.get("examples")
            if isinstance(ex, list):
                return len(ex)
        if isinstance(data, str):
            return data.count('"input"')
    except Exception:
        pass
    return -1


if __name__ == "__main__":
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    out = save_failing_case()
    print("=== PREVENT — save failing case via MCP add-dataset-examples ===")
    print(f"  dataset: {out['dataset']}")
    print(f"  result : {str(out['result'])[:160]}")
    n = count_examples()
    print(f"  read-back: {n if n >= 0 else 'n/a'} example(s) now in '{DATASET_NAME}' ✅")
