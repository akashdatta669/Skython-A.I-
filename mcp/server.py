"""
mcp/server.py — MCP Server as FastAPI sub-application
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

log = logging.getLogger(__name__)

# ─────────────────────────── Request log ─────────────────────────────────────

_request_log: deque[dict[str, Any]] = deque(maxlen=100)


def log_mcp_request(tool_name: str, success: bool) -> None:
    _request_log.appendleft(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "success": success,
        }
    )


def get_recent_requests(n: int = 10) -> list[dict[str, Any]]:
    return list(_request_log)[:n]


# ─────────────────────────── Pydantic models ──────────────────────────────────

class MCPExecuteRequest(BaseModel):
    tool: str
    parameters: dict[str, Any] = {}


# ─────────────────────────── Factory ──────────────────────────────────────────

def create_mcp_app(executor: Any) -> FastAPI:
    """Create the MCP FastAPI sub-application."""
    from mcp.tools import MCP_TOOLS

    app = FastAPI(
        title="Skython MCP Server",
        description="Model Context Protocol interface for Skython AI",
        version="1.0.0",
    )

    @app.get("/mcp/tools")
    async def list_tools() -> dict[str, Any]:
        """List all available MCP tools."""
        return {"tools": MCP_TOOLS, "count": len(MCP_TOOLS)}

    @app.post("/mcp/execute")
    async def execute_tool(request: MCPExecuteRequest) -> dict[str, Any]:
        """Execute an MCP tool."""
        try:
            result = executor.execute(request.tool, request.parameters)
            success = result.get("success", True)
            log_mcp_request(request.tool, success)
            return result
        except Exception as exc:
            log.error("MCP execute error: %s", exc)
            log_mcp_request(request.tool, False)
            return {"error": str(exc), "success": False}

    @app.get("/mcp/logs")
    async def get_logs(n: int = 10) -> dict[str, Any]:
        """Get the last N MCP request logs."""
        return {"logs": get_recent_requests(n)}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "mcp"}

    return app
