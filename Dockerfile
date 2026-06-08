# Agent SRE — single container that serves the cockpit, calls Gemini (Vertex), and spawns the
# Phoenix MCP server via npx. Needs BOTH Python and Node, so this is a custom image (not adk deploy).

# --- Stage 1: build the React cockpit -----------------------------------------------------------
FROM node:20-slim AS cockpit-build
WORKDIR /cockpit
COPY cockpit/package.json cockpit/package-lock.json ./
RUN npm ci
COPY cockpit/ ./
RUN npm run build

# --- Stage 2: Python + Node runtime -------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Node 20 (for the npx-spawned Phoenix MCP server) + curl for the NodeSource setup.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && apt-get purge -y gnupg && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# uv (fast, reproducible Python deps)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install Python deps first (cached layer). package=false => deps only, app runs from cwd.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Application code + the built cockpit.
COPY agent_sre/ ./agent_sre/
COPY target_agent/ ./target_agent/
COPY --from=cockpit-build /cockpit/dist ./cockpit/dist

# Pre-warm the pinned Phoenix MCP server into the npx cache so runtime spawns don't hit the registry.
RUN npx -y @arizeai/phoenix-mcp@4.0.13 --help > /dev/null 2>&1 || true

ENV PYTHONUNBUFFERED=1 PORT=8080
# Cloud Run injects $PORT. `python -m uvicorn` puts cwd (/app) on sys.path so agent_sre is importable.
CMD ["sh", "-c", "uv run python -m uvicorn agent_sre.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
