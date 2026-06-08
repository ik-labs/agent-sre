.PHONY: help setup model-probe smoke-trace mcp-smoke verify incident

help:
	@echo "Agent SRE targets:"
	@echo "  make setup        - uv sync (resolve deps on pinned Python 3.12)"
	@echo "  make model-probe  - find a callable Gemini model via Vertex; prints GEMINI_MODEL"
	@echo "  make smoke-trace  - run one ADK turn; emits a trace to Phoenix (MESSAGE=...)"
	@echo "  make mcp-smoke    - start @arizeai/phoenix-mcp and list its tools"
	@echo "  make verify       - model-probe + smoke-trace + mcp-smoke in sequence"
	@echo "  make incident     - run the broken target agent; print the failure chain"
	@echo "  make seed-prompt  - seed the agent instruction into the Phoenix prompt store"

incident:
	uv run python -m target_agent.run_incident

seed-prompt:
	uv run python scripts/seed_prompt.py

setup:
	uv sync
	@test -f .env || echo "Tip: cp .env.example .env and fill in keys."

model-probe:
	uv run python scripts/model_probe.py

smoke-trace:
	uv run python scripts/smoke_trace.py "$(if $(MESSAGE),$(MESSAGE),Please ping the message 'hello phoenix'.)"

mcp-smoke:
	uv run python scripts/mcp_smoke.py

verify: model-probe smoke-trace mcp-smoke
	@echo "\nPhase 0 verification complete — confirm the trace is visible in the Phoenix UI."
