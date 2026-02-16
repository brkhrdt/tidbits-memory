"""In-memory adapter for MemoryStore (used in tests and fast local runs)."""

from __future__ import annotations

import copy
from typing import Optional

from tidbits_memory.adapters.base import BaseAdapter
from tidbits_memory.models import Memory


class InMemoryAdapter(BaseAdapter):
    """Stores memories in a plain dict; no persistence."""

    def __init__(self) -> None:
        self._data: dict[str, Memory] = {}

    def save(self, memory: Memory) -> None:
        self._data[memory.id] = copy.deepcopy(memory)

    def get(self, memory_id: str) -> Optional[Memory]:
        m = self._data.get(memory_id)
        return copy.deepcopy(m) if m else None

    def delete(self, memory_id: str) -> bool:
        return self._data.pop(memory_id, None) is not None

    def list_all(self) -> list[Memory]:
        return [copy.deepcopy(m) for m in self._data.values()]
