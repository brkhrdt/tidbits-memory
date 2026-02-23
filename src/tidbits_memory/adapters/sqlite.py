"""SQLite adapter for MemoryStore."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from tidbits_memory.adapters.base import BaseAdapter
from tidbits_memory.models import Memory, VoteRecord

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS memories (
    id              TEXT PRIMARY KEY,
    content         TEXT NOT NULL,
    votes           INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    last_updated    TEXT NOT NULL,
    creator         TEXT,
    tags            TEXT NOT NULL DEFAULT '[]',
    voters          TEXT NOT NULL DEFAULT '{}',
    last_anon_vote_at TEXT
);
"""


class SqliteAdapter(BaseAdapter):
    """Persists memories in a SQLite database."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self._path = str(path)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    # -- serialisation helpers ---------------------------------------------

    @staticmethod
    def _row_to_memory(row: tuple) -> Memory:
        (
            id_,
            content,
            votes,
            created_at,
            last_updated,
            creator,
            tags_json,
            voters_json,
            last_anon_vote_at,
        ) = row
        voters = {
            k: VoteRecord.from_dict(v)
            for k, v in json.loads(voters_json).items()
        }
        return Memory(
            id=id_,
            content=content,
            votes=votes,
            created_at=created_at,
            last_updated=last_updated,
            creator=creator,
            tags=json.loads(tags_json),
            voters=voters,
            last_anon_vote_at=last_anon_vote_at,
        )

    @staticmethod
    def _memory_to_params(memory: Memory) -> tuple:
        return (
            memory.id,
            memory.content,
            memory.votes,
            memory.created_at,
            memory.last_updated,
            memory.creator,
            json.dumps(memory.tags),
            json.dumps({k: v.to_dict() for k, v in memory.voters.items()}),
            memory.last_anon_vote_at,
        )

    # -- public interface ---------------------------------------------------

    def save(self, memory: Memory) -> None:
        params = self._memory_to_params(memory)
        self._conn.execute(
            """INSERT INTO memories
                   (id, content, votes, created_at, last_updated,
                    creator, tags, voters, last_anon_vote_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                   content=excluded.content,
                   votes=excluded.votes,
                   last_updated=excluded.last_updated,
                   creator=excluded.creator,
                   tags=excluded.tags,
                   voters=excluded.voters,
                   last_anon_vote_at=excluded.last_anon_vote_at
            """,
            params,
        )
        self._conn.commit()

    def get(self, memory_id: str) -> Optional[Memory]:
        cur = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        )
        row = cur.fetchone()
        return self._row_to_memory(row) if row else None

    def delete(self, memory_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM memories WHERE id = ?", (memory_id,)
        )
        self._conn.commit()
        return cur.rowcount > 0

    def list_all(self) -> list[Memory]:
        cur = self._conn.execute("SELECT * FROM memories")
        return [self._row_to_memory(row) for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteAdapter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
