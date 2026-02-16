"""CLI entry-point for the tidbits-memory MCP server."""

from __future__ import annotations

import argparse
import sys
from typing import Optional

from mcp.server import FastMCP

from tidbits_memory.store import MemoryStore
from tidbits_memory.tools import register_tools


def _build_store(backend: str, db: str) -> MemoryStore:
    if backend == "json":
        from tidbits_memory.adapters.json_file import JsonFileAdapter

        return MemoryStore(JsonFileAdapter(db))
    elif backend == "sqlite":
        from tidbits_memory.adapters.sqlite import SqliteAdapter

        return MemoryStore(SqliteAdapter(db))
    elif backend == "memory":
        from tidbits_memory.adapters.memory import InMemoryAdapter

        return MemoryStore(InMemoryAdapter())
    else:
        print(f"Unknown backend: {backend}", file=sys.stderr)
        sys.exit(1)


def build_mcp_server(
    backend: str = "json",
    db: str = "memories.json",
) -> FastMCP:
    """Build and return a FastMCP server with all tidbits tools registered."""
    store = _build_store(backend, db)
    mcp = FastMCP("tidbits-memory")
    register_tools(mcp, store)
    return mcp


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tidbits-memory",
        description="tidbits-memory MCP server: a memory/tidbits voting framework for AI agents",
    )
    parser.add_argument(
        "--backend",
        choices=["json", "sqlite", "memory"],
        default="json",
        help="Storage backend (default: json)",
    )
    parser.add_argument(
        "--db",
        default="memories.json",
        help="Path to storage file (JSON file or SQLite database, default: memories.json)",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    args = parser.parse_args(argv)

    mcp = build_mcp_server(backend=args.backend, db=args.db)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
