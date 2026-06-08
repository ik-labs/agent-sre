"""Golden-set incidents for the Guard step (regression gate).

These previously-correct cases must STILL pass after the SRE's fix — proving the fix is precise and
didn't break working behavior. All deterministic (canned fixtures + temperature 0). Expected outcome
is a verifiable fact: whether the agent paged, and which team.
See docs/fixtures-and-ground-truth.md.
"""

from __future__ import annotations

from typing import Optional

GOLDEN = [
    {
        "label": "checkout latency spike",
        "incident": "The checkout service has a latency spike in production. Investigate and page the right team if needed.",
        "expect_page": False,
        "expect_team": None,
    },
    {
        "label": "checkout 500s reported",
        "incident": "Checkout is reporting some 500s. Investigate and page the right team if needed.",
        "expect_page": False,
        "expect_team": None,
    },
    {
        "label": "payments outage (the fixed case)",
        "incident": "Payments service is throwing 500s in production. Investigate and page the right team if needed.",
        "expect_page": True,
        "expect_team": "platform",
    },
    {
        "label": "unknown-service alert",
        "incident": "The billing service alert fired. Investigate and page the right team if needed.",
        "expect_page": False,
        "expect_team": None,
    },
]


def paged_team(calls: list[tuple[str, dict]]) -> Optional[str]:
    """Return the team passed to page_oncall, or None if the agent did not page."""
    for name, args in calls:
        if name == "page_oncall":
            return args.get("team")
    return None


def case_passed(expect_page: bool, expect_team: Optional[str], calls: list[tuple[str, dict]]) -> bool:
    """Deterministic correctness check: paged the expected team, or correctly did not page."""
    team = paged_team(calls)
    if expect_page:
        return team == expect_team
    return team is None
