"""Phase 0 smoke test: prove the Phoenix MCP server starts and lists its tools against our space.

Spawns `npx -y @arizeai/phoenix-mcp@latest --baseUrl <endpoint> --apiKey <key>` over stdio,
performs the MCP JSON-RPC handshake (initialize -> tools/list), prints the tool names, and
optionally calls `list-projects` to confirm the credentials reach the space.

Secrets come from the environment (PHOENIX_COLLECTOR_ENDPOINT, PHOENIX_API_KEY) and are passed to
the subprocess at runtime — never hardcoded. Run: `make mcp-smoke`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_PROTO = "2025-06-18"  # MCP protocol revision; server negotiates down if needed.


def _drain(stream) -> None:
    for _ in iter(stream.readline, ""):
        pass


def main() -> int:
    base_url = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").strip()
    api_key = (os.environ.get("PHOENIX_API_KEY") or "").strip()
    if not base_url or not api_key:
        print("ERROR: set PHOENIX_COLLECTOR_ENDPOINT and PHOENIX_API_KEY in .env", file=sys.stderr)
        return 2

    cmd = ["npx", "-y", "@arizeai/phoenix-mcp@latest", "--baseUrl", base_url, "--apiKey", api_key]
    print(f"spawning: npx -y @arizeai/phoenix-mcp@latest --baseUrl {base_url} --apiKey ***\n")
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdin and proc.stdout and proc.stderr
    # Keep stderr from blocking the pipe (npx is chatty).
    threading.Thread(target=_drain, args=(proc.stderr,), daemon=True).start()

    def send(obj: dict) -> None:
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    def read() -> dict | None:
        line = proc.stdout.readline()
        while line and not line.strip():
            line = proc.stdout.readline()
        return json.loads(line) if line else None

    try:
        send({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": _PROTO,
                "capabilities": {},
                "clientInfo": {"name": "phase0-smoke", "version": "0.1.0"},
            },
        })
        init = read()
        if not init or "result" not in init:
            print(f"initialize failed: {init}", file=sys.stderr)
            return 1
        server = init["result"].get("serverInfo", {})
        print(f"connected to MCP server: {server.get('name')} v{server.get('version')}")

        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listing = read()
        tools = (listing or {}).get("result", {}).get("tools", [])
        if not tools:
            print(f"tools/list returned nothing: {listing}", file=sys.stderr)
            return 1
        print(f"\n{len(tools)} tools available:")
        for t in tools:
            print(f"  - {t['name']}")

        # Confirm the credentials actually reach the space.
        send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
              "params": {"name": "list-projects", "arguments": {}}})
        projs = read()
        if projs and "result" in projs:
            print("\nlist-projects OK — credentials reach the Phoenix space ✅")
        else:
            print(f"\nlist-projects did not return a result (check key/endpoint): {projs}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
