"""Tests for MCP tool wrappers."""

import pytest

from tidbits_memory.adapters.memory import InMemoryAdapter
from tidbits_memory.store import MemoryStore
from tidbits_memory.tools import (
    tidbits_create,
    tidbits_create_voter_id,
    tidbits_downvote,
    tidbits_get_memories,
    tidbits_list,
    tidbits_remove,
    tidbits_unvote,
    tidbits_upvote,
)


@pytest.fixture
def store():
    return MemoryStore(InMemoryAdapter())


class TestToolWrappers:
    def test_create(self, store: MemoryStore):
        result = tidbits_create(store, "hello", creator="bot")
        assert result["content"] == "hello"
        assert result["votes"] == 1

    def test_upvote(self, store: MemoryStore):
        m = tidbits_create(store, "a")
        result = tidbits_upvote(store, m["id"], voter_id="v1")
        assert result["votes"] == 2

    def test_downvote(self, store: MemoryStore):
        m = tidbits_create(store, "a")
        result = tidbits_downvote(store, m["id"], voter_id="v1")
        assert result["votes"] == 0

    def test_unvote(self, store: MemoryStore):
        m = tidbits_create(store, "a", voter_id="v1")
        result = tidbits_unvote(store, m["id"], "v1")
        assert result["votes"] == 0

    def test_list(self, store: MemoryStore):
        tidbits_create(store, "a")
        tidbits_create(store, "b")
        result = tidbits_list(store)
        assert len(result) == 2

    def test_get_memories(self, store: MemoryStore):
        tidbits_create(store, "a")
        result = tidbits_get_memories(store)
        assert "memories" in result
        assert "voter_id" in result
        assert "votes" not in result["memories"][0]

    def test_remove(self, store: MemoryStore):
        m = tidbits_create(store, "a")
        result = tidbits_remove(store, m["id"])
        assert result["removed"] is True

    def test_create_voter_id(self):
        result = tidbits_create_voter_id()
        assert "voter_id" in result
        assert len(result["voter_id"]) > 0
