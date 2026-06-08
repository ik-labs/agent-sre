"""Canned data + mock tools for the target DevOps incident-triage agent.

SINGLE SOURCE OF TRUTH for the demo (see docs/fixtures-and-ground-truth.md). Everything here is
deterministic and offline — no real infrastructure, no network, no I/O. Each tool is a pure lookup
over static literals with a safe default for unknown inputs.

Ground-truth scenario: the `payments` service has repeated "connection refused" errors; the
`platform` team owns it and must be paged. The agent fails because a prompt bug makes it query the
log tool with the singular `"payment"`, which returns no logs, leading to a false "healthy" verdict.
"""

from __future__ import annotations

# --- Canned datastores (the "production" the mock tools read) -----------------------------------

_LOGS = {
    "payments": (
        "[12:01] ERROR connection refused upstream db\n"
        "[12:01] ERROR connection refused upstream db\n"
        "[12:02] ERROR connection refused upstream db"
    ),
    # "payment" (singular) is deliberately absent -> falls through to "no logs found" (the bug path).
}

_METRICS = {
    "payments": {"cpu": 41, "mem": 63, "error_rate": 0.38},
    "checkout": {"cpu": 22, "mem": 50, "error_rate": 0.01},
}

_ONCALL = {
    "platform": "Priya N. (platform on-call)",
    "checkout": "Sam R. (checkout on-call)",
}

# Ground-truth service ownership (which team to page for a given service).
SERVICE_OWNERS = {
    "payments": "platform",
    "checkout": "checkout",
}


# --- Mock tools (registered as ADK FunctionTools) -----------------------------------------------

def get_pod_logs(service: str) -> str:
    """Return recent pod logs for a service.

    Args:
        service: The service name to fetch logs for (e.g. "payments").
    """
    return _LOGS.get(service, "no logs found")


def get_metrics(service: str) -> dict:
    """Return current resource + error-rate metrics for a service.

    Args:
        service: The service name to fetch metrics for (e.g. "payments").
    """
    return _METRICS.get(service, {"cpu": 0, "mem": 0, "error_rate": 0.0})


def get_oncall(team: str) -> str:
    """Return the current on-call engineer for a team.

    Args:
        team: The owning team (e.g. "platform").
    """
    return _ONCALL.get(team, "no on-call found")


def page_oncall(team: str, summary: str) -> str:
    """Page a team's on-call engineer with an incident summary (mock; no side effects).

    Args:
        team: The team to page (e.g. "platform").
        summary: A short incident summary naming the observed errors.
    """
    return f"paged {team}: {summary}"
