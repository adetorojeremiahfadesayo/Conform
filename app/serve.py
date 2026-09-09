"""Launch the API and authenticated official MCP sidecar; infrastructure only."""
from __future__ import annotations

import os
import secrets
import subprocess
import sys


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()
    os.environ.setdefault("CLICKHOUSE_MCP_AUTH_TOKEN", secrets.token_urlsafe(32))
    if not os.environ["CLICKHOUSE_MCP_AUTH_TOKEN"]:
        os.environ["CLICKHOUSE_MCP_AUTH_TOKEN"] = secrets.token_urlsafe(32)
    os.environ["CLICKHOUSE_MCP_URL"] = "http://127.0.0.1:8000"
    os.environ["CLICKHOUSE_MCP_SERVER_TRANSPORT"] = "http"
    os.environ["CLICKHOUSE_ALLOW_WRITE_ACCESS"] = "false"
    os.environ["CLICKHOUSE_MCP_AUTH_DISABLED"] = "false"
    sidecar = subprocess.Popen([sys.executable, "-m", "mcp_clickhouse.main"])
    try:
        import uvicorn
        uvicorn.run("app.api.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
    finally:
        sidecar.terminate()
        sidecar.wait(timeout=10)


if __name__ == "__main__":
    main()
