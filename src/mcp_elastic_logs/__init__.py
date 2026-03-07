"""MCP server package for Elasticsearch log diagnosis."""

from __future__ import annotations

from typing import Any

__all__ = ["mcp"]


def __getattr__(name: str) -> Any:
    """Lazily expose package-level attributes with deferred imports."""
    if name == "mcp":
        from .server import mcp

        return mcp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
