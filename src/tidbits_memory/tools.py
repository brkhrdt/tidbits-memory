"""MCP tool definitions for tidbits-memory.

Provides ``register_tools(mcp, store)`` to attach all tidbits tools to a
FastMCP server instance.
"""

from __future__ import annotations

from typing import Any, Optional

from mcp.server import FastMCP

from tidbits_memory.store import MemoryStore


def register_tools(mcp: FastMCP, store: MemoryStore) -> None:
    """Register all tidbits MCP tools on *mcp* backed by *store*."""

    @mcp.tool(
        name="create_memory",
        description="Create a new memory/tidbit. Returns the created memory with its id.",
    )
    def create_memory(
        content: str,
        creator: Optional[str] = None,
        tags: Optional[list[str]] = None,
        voter_id: Optional[str] = None,
    ) -> dict[str, Any]:
        mem = store.create_memory(
            content, creator=creator, tags=tags, voter_id=voter_id
        )
        return mem.to_dict()

    @mcp.tool(
        name="upvote_memory",
        description="Upvote a memory. Provide voter_id to enforce one vote per session.",
    )
    def upvote_memory(
        memory_id: str,
        voter_id: Optional[str] = None,
    ) -> dict[str, Any]:
        mem = store.upvote_memory(memory_id, voter_id=voter_id)
        return mem.to_dict()

    @mcp.tool(
        name="downvote_memory",
        description="Downvote a memory. Provide voter_id to enforce one vote per session.",
    )
    def downvote_memory(
        memory_id: str,
        voter_id: Optional[str] = None,
    ) -> dict[str, Any]:
        mem = store.downvote_memory(memory_id, voter_id=voter_id)
        return mem.to_dict()

    @mcp.tool(
        name="unvote_memory",
        description="Remove a prior vote from a memory by voter_id.",
    )
    def unvote_memory(
        memory_id: str,
        voter_id: str,
    ) -> dict[str, Any]:
        mem = store.unvote_memory(memory_id, voter_id)
        return mem.to_dict()

    @mcp.tool(
        name="list_memory",
        description="List all memories sorted by votes descending (most upvoted first). Optionally filter by tags.",
    )
    def list_memory(
        order_by: str = "votes",
        limit: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        return [
            m.to_dict()
            for m in store.list_memories(order_by=order_by, limit=limit, tags=tags)
        ]

    @mcp.tool(
        name="get_memories",
        description=(
            "Get the list of memories. "
            "If voter_id is not provided, a new one is generated and "
            "included in the response for use in subsequent votes."
        ),
    )
    def get_memories(
        voter_id: Optional[str] = None,
    ) -> dict[str, Any]:
        return store.get_memories(voter_id=voter_id)

    @mcp.tool(
        name="remove_memory",
        description="Remove a memory by id.",
    )
    def remove_memory(memory_id: str) -> dict[str, Any]:
        return {"removed": store.remove_memory(memory_id), "id": memory_id}

    @mcp.tool(
        name="create_voter_id",
        description="Generate a new unique voter_id for this agent session.",
    )
    def create_voter_id() -> dict[str, str]:
        return {"voter_id": store.create_voter_id()}
