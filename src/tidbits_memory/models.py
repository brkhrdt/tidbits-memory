"""Memory data model."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class VoteRecord:
    """A single vote cast by a voter."""

    value: int  # +1 or -1
    timestamp: str  # ISO 8601

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VoteRecord:
        return cls(value=data["value"], timestamp=data["timestamp"])


@dataclass
class Memory:
    """A single memory/tidbit entry."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    votes: int = 1
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    creator: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    voters: dict[str, VoteRecord] = field(default_factory=dict)
    # Timestamp of last anonymous vote (for fallback rate-limiting)
    last_anon_vote_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "votes": self.votes,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "creator": self.creator,
            "tags": self.tags,
            "voters": {k: v.to_dict() for k, v in self.voters.items()},
            "last_anon_vote_at": self.last_anon_vote_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        voters = {
            k: VoteRecord.from_dict(v) for k, v in data.get("voters", {}).items()
        }
        return cls(
            id=data["id"],
            content=data["content"],
            votes=data.get("votes", 1),
            created_at=data.get("created_at", ""),
            last_updated=data.get("last_updated", ""),
            creator=data.get("creator"),
            tags=data.get("tags", []),
            voters=voters,
            last_anon_vote_at=data.get("last_anon_vote_at"),
        )
