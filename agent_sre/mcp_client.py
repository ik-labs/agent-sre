"""A tiny synchronous Phoenix MCP stdio client (for programmatic SRE actions).

Used by the Fix step to call ``upsert-prompt`` (and later Prevent's ``add-dataset-examples``)
deterministically. The agentic, LLM-driven MCP usage lives in sre_agent.py; this is the
deterministic action path for the spine.

Secrets: the Phoenix API key is passed to the npx subprocess via the environment (never argv).
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from typing import Any, Optional

_PROTO = "2025-06-18"


class PhoenixMCP:
    """Context manager that spawns @arizeai/phoenix-mcp over stdio and calls its tools."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None
        self._id = 0

    def __enter__(self) -> "PhoenixMCP":
        base_url = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").strip()
        api_key = (os.environ.get("PHOENIX_API_KEY") or "").strip()
        if not base_url or not api_key:
            raise RuntimeError("PHOENIX_COLLECTOR_ENDPOINT and PHOENIX_API_KEY must be set")
        self._proc = subprocess.Popen(
            ["npx", "-y", "@arizeai/phoenix-mcp@latest", "--baseUrl", base_url],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env={**os.environ, "PHOENIX_API_KEY": api_key},
        )
        threading.Thread(target=self._drain, args=(self._proc.stderr,), daemon=True).start()
        self._send({"jsonrpc": "2.0", "id": self._next(), "method": "initialize", "params": {
            "protocolVersion": _PROTO, "capabilities": {},
            "clientInfo": {"name": "agent-sre", "version": "0.1.0"}}})
        self._recv()
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        return self

    def __exit__(self, *exc) -> None:
        if self._proc:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()

    def call(self, name: str, arguments: dict) -> Any:
        """Call an MCP tool. Returns parsed JSON if the text content is JSON, else the raw text."""
        self._send({"jsonrpc": "2.0", "id": self._next(), "method": "tools/call",
                    "params": {"name": name, "arguments": arguments}})
        resp = self._recv()
        if not resp or "result" not in resp:
            raise RuntimeError(f"MCP call {name} failed: {resp}")
        content = resp["result"].get("content", [])
        text = content[0]["text"] if content and "text" in content[0] else json.dumps(resp["result"])
        try:
            return json.loads(text)
        except Exception:
            return text

    # --- plumbing ---
    def _next(self) -> int:
        self._id += 1
        return self._id

    def _send(self, obj: dict) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(obj) + "\n")
        self._proc.stdin.flush()

    def _recv(self) -> Optional[dict]:
        assert self._proc and self._proc.stdout
        line = self._proc.stdout.readline()
        while line and not line.strip():
            line = self._proc.stdout.readline()
        return json.loads(line) if line else None

    @staticmethod
    def _drain(stream) -> None:
        for _ in iter(stream.readline, ""):
            pass
