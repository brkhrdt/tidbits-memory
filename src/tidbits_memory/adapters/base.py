"""Abstract base adapter for memory storage."""

from __future__ import annotations

import abc
from typing import Optional

from tidbits_memory.models import Memory


class BaseAdapter(abc.ABC):
    """Interface that all storage adapters must implement."""

    @abc.abstractmethod
    def save(self, memory: Memory) -> None:
        """Save or update a memory entry."""

    @abc.abstractmethod
    def get(self, memory_id: str) -> Optional[Memory]:
        """Return a memory by id, or None."""

    @abc.abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a memory by id. Return True if it existed."""

    @abc.abstractmethod
    def list_all(self) -> list[Memory]:
        """Return all stored memories."""
