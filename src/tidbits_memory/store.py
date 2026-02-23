"""High-level MemoryStore API wrapping a storage adapter."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from tidbits_memory.adapters.base import BaseAdapter
from tidbits_memory.models import Memory, VoteRecord

# Fallback rate-limit window when voter_id is not provided
_ANON_VOTE_COOLDOWN = timedelta(minutes=1)


class DuplicateVoteError(Exception):
    """Raised when a voter_id tries to vote on a memory it already voted on."""


class RateLimitError(Exception):
    """Raised when anonymous voting is rate-limited."""


class MemoryNotFoundError(KeyError):
    """Raised when a memory_id does not exist."""


class MemoryStore:
    """Core API for creating, voting on, and managing memories."""

    def __init__(self, adapter: BaseAdapter) -> None:
        self._adapter = adapter

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def create_voter_id() -> str:
        """Generate a new unique voter_id."""
        return str(uuid.uuid4())

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _get_or_raise(self, memory_id: str) -> Memory:
        m = self._adapter.get(memory_id)
        if m is None:
            raise MemoryNotFoundError(memory_id)
        return m

    # -- public API --------------------------------------------------------

    def create_memory(
        self,
        content: str,
        *,
        creator: Optional[str] = None,
        tags: Optional[list[str]] = None,
        voter_id: Optional[str] = None,
    ) -> Memory:
        if not content or not content.strip():
            raise ValueError("Memory content must not be empty")
        now = self._now_iso()
        mem = Memory(
            content=content,
            votes=1,
            created_at=now,
            last_updated=now,
            creator=creator,
            tags=tags or [],
        )
        if voter_id:
            mem.voters[voter_id] = VoteRecord(value=1, timestamp=now)
        self._adapter.save(mem)
        return mem

    def upvote_memory(
        self,
        memory_id: str,
        *,
        voter_id: Optional[str] = None,
        n: int = 1,
    ) -> Memory:
        return self._vote(memory_id, direction=1, voter_id=voter_id, n=n)

    def downvote_memory(
        self,
        memory_id: str,
        *,
        voter_id: Optional[str] = None,
        n: int = 1,
    ) -> Memory:
        return self._vote(memory_id, direction=-1, voter_id=voter_id, n=n)

    def _vote(
        self,
        memory_id: str,
        *,
        direction: int,
        voter_id: Optional[str],
        n: int,
    ) -> Memory:
        if n < 1:
            raise ValueError(f"n must be >= 1, got {n}")
        mem = self._get_or_raise(memory_id)
        now = self._now_iso()

        if voter_id:
            if voter_id in mem.voters:
                raise DuplicateVoteError(
                    f"voter_id {voter_id!r} already voted on memory {memory_id!r}"
                )
            mem.voters[voter_id] = VoteRecord(
                value=direction * n, timestamp=now
            )
        else:
            # Fallback rate-limit: one anonymous vote per minute per memory
            if mem.last_anon_vote_at:
                last = datetime.fromisoformat(mem.last_anon_vote_at)
                if datetime.now(timezone.utc) - last < _ANON_VOTE_COOLDOWN:
                    raise RateLimitError(
                        f"Anonymous vote on memory {memory_id!r} rate-limited "
                        f"(1 per {_ANON_VOTE_COOLDOWN.total_seconds():.0f}s)"
                    )
            mem.last_anon_vote_at = now

        mem.votes += direction * n
        mem.last_updated = now
        self._adapter.save(mem)
        return mem

    def unvote_memory(self, memory_id: str, voter_id: str) -> Memory:
        mem = self._get_or_raise(memory_id)
        record = mem.voters.pop(voter_id, None)
        if record is None:
            return mem  # nothing to undo
        mem.votes -= record.value
        mem.last_updated = self._now_iso()
        self._adapter.save(mem)
        return mem

    _VALID_ORDER_BY = {"votes", "created_at"}

    def list_memories(
        self,
        *,
        order_by: str = "votes",
        limit: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> list[Memory]:
        if order_by not in self._VALID_ORDER_BY:
            raise ValueError(
                f"Invalid order_by={order_by!r}; must be one of {sorted(self._VALID_ORDER_BY)}"
            )
        memories = self._adapter.list_all()
        if tags:
            tag_set = set(tags)
            memories = [m for m in memories if tag_set & set(m.tags)]
        if order_by == "votes":
            memories.sort(key=lambda m: m.votes, reverse=True)
        elif order_by == "created_at":
            memories.sort(key=lambda m: m.created_at, reverse=True)
        if limit is not None:
            memories = memories[:limit]
        return memories

    def get_memories(
        self, *, voter_id: Optional[str] = None
    ) -> dict[str, Any]:
        """Return all memories in random order without vote counts.

        If *voter_id* is not supplied, a new one is generated and included
        in the response so the caller can use it for subsequent votes.
        """
        generated_voter_id: Optional[str] = None
        if not voter_id:
            generated_voter_id = self.create_voter_id()

        memories = self._adapter.list_all()
        random.shuffle(memories)

        items = [
            {
                "id": m.id,
                "content": m.content,
                "tags": m.tags,
            }
            for m in memories
        ]

        result: dict[str, Any] = {"memories": items}
        if generated_voter_id:
            result["voter_id"] = generated_voter_id
        return result

    def remove_memory(self, memory_id: str) -> bool:
        return self._adapter.delete(memory_id)

    def get_memory(self, memory_id: str) -> Optional[Memory]:
        return self._adapter.get(memory_id)
