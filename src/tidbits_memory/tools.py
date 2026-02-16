"""MCP tool wrappers for tidbits-memory.

Each function returns a JSON-serializable dict suitable for agent consumption.
"""

from __future__ import annotations

from typing import Any, Optional

from tidbits_memory.store import MemoryStore


def _memory_to_dict(mem: Any) -> dict[str, Any]:
    return mem.to_dict()


def tidbits_create(
    store: MemoryStore,
    content: str,
    *,
    creator: Optional[str] = None,
    tags: Optional[list[str]] = None,
    voter_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create a new memory entry."""
    mem = store.create_memory(
        content, creator=creator, tags=tags, voter_id=voter_id
    )
    return _memory_to_dict(mem)


def tidbits_upvote(
    store: MemoryStore,
    memory_id: str,
    *,
    voter_id: Optional[str] = None,
    n: int = 1,
) -> dict[str, Any]:
    """Upvote a memory."""
    mem = store.upvote_memory(memory_id, voter_id=voter_id, n=n)
    return _memory_to_dict(mem)


def tidbits_downvote(
    store: MemoryStore,
    memory_id: str,
    *,
    voter_id: Optional[str] = None,
    n: int = 1,
) -> dict[str, Any]:
    """Downvote a memory."""
    mem = store.downvote_memory(memory_id, voter_id=voter_id, n=n)
    return _memory_to_dict(mem)


def tidbits_unvote(
    store: MemoryStore,
    memory_id: str,
    voter_id: str,
) -> dict[str, Any]:
    """Remove a prior vote from a memory."""
    mem = store.unvote_memory(memory_id, voter_id)
    return _memory_to_dict(mem)


def tidbits_list(
    store: MemoryStore,
    *,
    order_by: str = "votes",
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    """List memories sorted by votes descending."""
    return [_memory_to_dict(m) for m in store.list_memories(order_by=order_by, limit=limit)]


def tidbits_get_memories(
    store: MemoryStore,
    *,
    voter_id: Optional[str] = None,
) -> dict[str, Any]:
    """Get memories in random order without vote counts."""
    return store.get_memories(voter_id=voter_id)


def tidbits_remove(
    store: MemoryStore,
    memory_id: str,
) -> dict[str, Any]:
    """Remove a memory entry."""
    return {"removed": store.remove_memory(memory_id), "id": memory_id}


def tidbits_create_voter_id() -> dict[str, str]:
    """Generate a new voter_id for an agent session."""
    return {"voter_id": MemoryStore.create_voter_id()}
