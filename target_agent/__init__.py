"""Target incident-triage agent package.

``root_agent`` is exposed LAZILY (via module ``__getattr__``) so that importing sibling modules
(e.g. ``target_agent.drift_agent``) does NOT pull in ``agent.py`` — which calls ``setup_tracing()``
at import and would lock the process's global tracer to the ``incident-agent`` project. The drift
trace generator needs to register its own ``drift-watch`` project first.
"""


def __getattr__(name):
    if name == "root_agent":
        from target_agent.agent import root_agent

        return root_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
