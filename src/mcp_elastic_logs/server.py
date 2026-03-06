"""FastMCP server entrypoint."""

from __future__ import annotations

import argparse
import atexit
import asyncio
import os

from fastmcp import FastMCP

from .elastic_connection import close_elasticsearch_client
from .tools.logs import register_log_tools

mcp = FastMCP(name="elastic-log-diagnosis")
register_log_tools(mcp)


def _shutdown_client() -> None:
    """Best-effort cleanup for the shared async Elasticsearch client."""
    try:
        asyncio.run(close_elasticsearch_client())
    except RuntimeError:
        # Runtime may already be shutting down with an active event loop.
        pass


atexit.register(_shutdown_client)


def main() -> None:
    """Run the MCP server.

    Supports `stdio`, `sse`, and `streamable-http` transports.
    """
    parser = argparse.ArgumentParser(description="MCP Elasticsearch Logs server")
    parser.add_argument(
        "--transport",
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport mode",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "127.0.0.1"),
        help="Bind host for network transports",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8091")),
        help="Bind port for network transports",
    )

    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
