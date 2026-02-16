"""Tests for SqliteAdapter: persistence, schema, roundtrip."""

import json
from pathlib import Path

import pytest

from tidbits_memory.adapters.sqlite import SqliteAdapter
from tidbits_memory.models import Memory
from tidbits_memory.store import MemoryStore, DuplicateVoteError


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def adapter(db_path: Path) -> SqliteAdapter:
    return SqliteAdapter(db_path)


@pytest.fixture
def store(adapter: SqliteAdapter) -> MemoryStore:
    return MemoryStore(adapter)


# -- basic CRUD ------------------------------------------------------------


class TestSqliteCRUD:
    def test_create_and_get(self, store: MemoryStore):
        m = store.create_memory("hello sqlite")
        loaded = store.get_memory(m.id)
        assert loaded is not None
        assert loaded.content == "hello sqlite"
        assert loaded.votes == 1

    def test_list_all(self, store: MemoryStore):
        store.create_memory("a")
        store.create_memory("b")
        assert len(store.list_memories()) == 2

    def test_remove(self, store: MemoryStore):
        m = store.create_memory("x")
        assert store.remove_memory(m.id) is True
        assert store.get_memory(m.id) is None

    def test_remove_nonexistent(self, store: MemoryStore):
        assert store.remove_memory("bad") is False


# -- persistence -----------------------------------------------------------


class TestSqlitePersistence:
    def test_survives_reopen(self, db_path: Path):
        s1 = MemoryStore(SqliteAdapter(db_path))
        m = s1.create_memory("persist me")

        s2 = MemoryStore(SqliteAdapter(db_path))
        loaded = s2.get_memory(m.id)
        assert loaded is not None
        assert loaded.content == "persist me"

    def test_voters_persist(self, db_path: Path):
        s1 = MemoryStore(SqliteAdapter(db_path))
        m = s1.create_memory("voted", voter_id="v1")
        s1.upvote_memory(m.id, voter_id="v2")

        s2 = MemoryStore(SqliteAdapter(db_path))
        loaded = s2.get_memory(m.id)
        assert loaded is not None
        assert "v1" in loaded.voters
        assert "v2" in loaded.voters
        assert loaded.votes == 2

    def test_tags_persist(self, db_path: Path):
        s1 = MemoryStore(SqliteAdapter(db_path))
        s1.create_memory("tagged", tags=["python", "tips"])

        s2 = MemoryStore(SqliteAdapter(db_path))
        mems = s2.list_memories()
        assert mems[0].tags == ["python", "tips"]


# -- voting ----------------------------------------------------------------


class TestSqliteVoting:
    def test_upvote_downvote(self, store: MemoryStore):
        m = store.create_memory("a")
        m = store.upvote_memory(m.id, voter_id="v1")
        assert m.votes == 2
        m = store.downvote_memory(m.id, voter_id="v2")
        assert m.votes == 1

    def test_duplicate_vote_raises(self, store: MemoryStore):
        m = store.create_memory("a", voter_id="v1")
        with pytest.raises(DuplicateVoteError):
            store.upvote_memory(m.id, voter_id="v1")

    def test_unvote(self, store: MemoryStore):
        m = store.create_memory("a", voter_id="v1")
        m = store.upvote_memory(m.id, voter_id="v2")
        assert m.votes == 2
        m = store.unvote_memory(m.id, "v2")
        assert m.votes == 1
        assert "v2" not in m.voters


# -- list ordering ---------------------------------------------------------


class TestSqliteListOrder:
    def test_sorted_by_votes_desc(self, store: MemoryStore):
        store.create_memory("low")
        m2 = store.create_memory("high")
        store.upvote_memory(m2.id, voter_id="v1")

        result = store.list_memories()
        assert result[0].id == m2.id

    def test_limit(self, store: MemoryStore):
        for i in range(5):
            store.create_memory(f"m{i}")
        assert len(store.list_memories(limit=2)) == 2


# -- get_memories ----------------------------------------------------------


class TestSqliteGetMemories:
    def test_omits_votes(self, store: MemoryStore):
        store.create_memory("a")
        result = store.get_memories()
        for item in result["memories"]:
            assert "votes" not in item
            assert "voters" not in item

    def test_includes_voter_id_when_none_provided(self, store: MemoryStore):
        store.create_memory("a")
        result = store.get_memories()
        assert "voter_id" in result
