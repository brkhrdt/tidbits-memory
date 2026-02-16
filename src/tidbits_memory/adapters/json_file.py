"""JSON file adapter with atomic writes and file locking."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from pathlib import Path
from typing import Optional

from tidbits_memory.adapters.base import BaseAdapter
from tidbits_memory.models import Memory


class JsonFileAdapter(BaseAdapter):
    """Persists memories to a JSON file with atomic writes."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    # -- internal helpers --------------------------------------------------

    def _read(self) -> dict[str, dict]:
        if not self._path.exists():
            return {}
        with open(self._path, "r") as fh:
            fcntl.flock(fh, fcntl.LOCK_SH)
            try:
                data = json.load(fh)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
        return data

    def _write(self, data: dict[str, dict]) -> None:
        dir_fd = None
        try:
            fd, tmp = tempfile.mkstemp(
                dir=str(self._path.parent), suffix=".tmp"
            )
            with os.fdopen(fd, "w") as fh:
                fcntl.flock(fh, fcntl.LOCK_EX)
                json.dump(data, fh, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
                fcntl.flock(fh, fcntl.LOCK_UN)
            os.replace(tmp, str(self._path))
        finally:
            if dir_fd is not None:
                os.close(dir_fd)

    # -- public interface ---------------------------------------------------

    def save(self, memory: Memory) -> None:
        data = self._read()
        data[memory.id] = memory.to_dict()
        self._write(data)

    def get(self, memory_id: str) -> Optional[Memory]:
        data = self._read()
        raw = data.get(memory_id)
        return Memory.from_dict(raw) if raw else None

    def delete(self, memory_id: str) -> bool:
        data = self._read()
        if memory_id not in data:
            return False
        del data[memory_id]
        self._write(data)
        return True

    def list_all(self) -> list[Memory]:
        data = self._read()
        return [Memory.from_dict(v) for v in data.values()]
