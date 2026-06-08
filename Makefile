.PHONY: help setup model-probe smoke-trace mcp-smoke verify incident seed-prompt diagnose measure spine server cockpit guard prevent drift-seed

help:
	@echo "Agent SRE targets:"
	@echo "  make setup        - uv sync (resolve deps on pinned Python 3.12)"
	@echo "  make model-probe  - find a callable Gemini model via Vertex; prints GEMINI_MODEL"
	@echo "  make smoke-trace  - run one ADK turn; emits a trace to Phoenix (MESSAGE=...)"
	@echo "  make mcp-smoke    - start @arizeai/phoenix-mcp and list its tools"
	@echo "  make verify       - model-probe + smoke-trace + mcp-smoke in sequence"
	@echo "  make incident     - run the broken target agent; print the failure chain"
	@echo "  make seed-prompt  - seed the agent instruction into the Phoenix prompt store"
	@echo "  make diagnose     - run the SRE's Diagnose step (reads target traces via Phoenix MCP)"
	@echo "  make measure      - run the LLM-judge over the target's current behavior (0/1 or 1/1)"
	@echo "  make spine        - the live spine: Measure -> Fix (MCP) -> Verify (0/1 -> 1/1)"
	@echo "  make server       - run the cockpit FastAPI/SSE backend on :8000"
	@echo "  make cockpit      - run the React/Vite cockpit dev server on :5173"

incident:
	uv run python -m target_agent.run_incident

seed-prompt:
	uv run python scripts/seed_prompt.py

diagnose:
	uv run python -m agent_sre.run_diagnose

measure:
	uv run python -m agent_sre.eval

spine:
	uv run python -m agent_sre.run_spine

guard:
	uv run python -m agent_sre.guard

prevent:
	uv run python -m agent_sre.prevent

drift-seed:
	uv run python scripts/generate_drift_traces.py

server:
	uv run uvicorn agent_sre.server:app --reload --port 8000

cockpit:
	cd cockpit && npm install && npm run dev

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
