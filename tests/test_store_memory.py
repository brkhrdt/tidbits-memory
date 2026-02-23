"""Tests for MemoryStore with in-memory adapter."""

import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest

from tidbits_memory.adapters.memory import InMemoryAdapter
from tidbits_memory.store import (
    DuplicateVoteError,
    MemoryNotFoundError,
    MemoryStore,
    RateLimitError,
)


@pytest.fixture
def store():
    return MemoryStore(InMemoryAdapter())


# -- create ----------------------------------------------------------------


class TestCreate:
    def test_create_basic(self, store: MemoryStore):
        m = store.create_memory("fact 1")
        assert m.content == "fact 1"
        assert m.votes == 1

    def test_create_with_voter_id(self, store: MemoryStore):
        m = store.create_memory("fact 2", voter_id="v1")
        assert "v1" in m.voters
        assert m.voters["v1"].value == 1

    def test_create_with_tags_and_creator(self, store: MemoryStore):
        m = store.create_memory("fact", creator="bot", tags=["py"])
        assert m.creator == "bot"
        assert m.tags == ["py"]

    def test_create_empty_content_raises(self, store: MemoryStore):
        with pytest.raises(ValueError, match="content must not be empty"):
            store.create_memory("")

    def test_create_whitespace_content_raises(self, store: MemoryStore):
        with pytest.raises(ValueError, match="content must not be empty"):
            store.create_memory("   ")


# -- upvote / downvote ----------------------------------------------------


class TestVoting:
    def test_upvote(self, store: MemoryStore):
        m = store.create_memory("a")
        m = store.upvote_memory(m.id, voter_id="v1")
        assert m.votes == 2

    def test_downvote(self, store: MemoryStore):
        m = store.create_memory("a")
        m = store.downvote_memory(m.id, voter_id="v1")
        assert m.votes == 0

    def test_upvote_nonexistent(self, store: MemoryStore):
        with pytest.raises(MemoryNotFoundError):
            store.upvote_memory("bad-id", voter_id="v1")

    def test_downvote_nonexistent(self, store: MemoryStore):
        with pytest.raises(MemoryNotFoundError):
            store.downvote_memory("bad-id", voter_id="v1")

    def test_vote_n_zero_raises(self, store: MemoryStore):
        m = store.create_memory("a")
        with pytest.raises(ValueError, match="n must be >= 1"):
            store.upvote_memory(m.id, voter_id="v1", n=0)

    def test_vote_n_negative_raises(self, store: MemoryStore):
        m = store.create_memory("a")
        with pytest.raises(ValueError, match="n must be >= 1"):
            store.downvote_memory(m.id, voter_id="v1", n=-1)


# -- per-run voting --------------------------------------------------------


class TestPerRunVoting:
    def test_duplicate_vote_raises(self, store: MemoryStore):
        m = store.create_memory("a", voter_id="v1")
        with pytest.raises(DuplicateVoteError):
            store.upvote_memory(m.id, voter_id="v1")

    def test_different_voter_ids_ok(self, store: MemoryStore):
        m = store.create_memory("a", voter_id="v1")
        m = store.upvote_memory(m.id, voter_id="v2")
        assert m.votes == 2

    def test_duplicate_downvote_raises(self, store: MemoryStore):
        m = store.create_memory("a", voter_id="v1")
        with pytest.raises(DuplicateVoteError):
            store.downvote_memory(m.id, voter_id="v1")


# -- unvote ----------------------------------------------------------------


class TestUnvote:
    def test_unvote_removes_vote(self, store: MemoryStore):
        m = store.create_memory("a", voter_id="v1")
        m = store.upvote_memory(m.id, voter_id="v2")
        assert m.votes == 2
        m = store.unvote_memory(m.id, "v2")
        assert m.votes == 1
        assert "v2" not in m.voters

    def test_unvote_nonexistent_voter(self, store: MemoryStore):
        m = store.create_memory("a")
        m2 = store.unvote_memory(m.id, "nobody")
        assert m2.votes == m.votes

    def test_unvote_nonexistent_memory(self, store: MemoryStore):
        with pytest.raises(MemoryNotFoundError):
            store.unvote_memory("bad-id", "v1")


# -- anonymous rate-limiting -----------------------------------------------


class TestRateLimiting:
    def test_anon_vote_rate_limited(self, store: MemoryStore):
        m = store.create_memory("a")
        store.upvote_memory(m.id)  # first anon vote ok
        with pytest.raises(RateLimitError):
            store.upvote_memory(m.id)  # second anon vote within 1 min

    def test_anon_vote_allowed_after_cooldown(self, store: MemoryStore):
        m = store.create_memory("a")
        store.upvote_memory(m.id)

        past = (datetime.now(timezone.utc) - timedelta(seconds=61)).isoformat()
        mem = store._adapter.get(m.id)
        mem.last_anon_vote_at = past
        store._adapter.save(mem)

        m2 = store.upvote_memory(m.id)
        assert m2.votes == 3  # 1 (create) + 1 + 1


# -- list ------------------------------------------------------------------


class TestList:
    def test_list_sorted_by_votes(self, store: MemoryStore):
        store.create_memory("low")
        m2 = store.create_memory("high")
        store.upvote_memory(m2.id, voter_id="v1")

        result = store.list_memories()
        assert result[0].id == m2.id

    def test_list_with_limit(self, store: MemoryStore):
        for i in range(5):
            store.create_memory(f"m{i}")
        assert len(store.list_memories(limit=3)) == 3

    def test_list_empty(self, store: MemoryStore):
        assert store.list_memories() == []

    def test_list_invalid_order_by(self, store: MemoryStore):
        with pytest.raises(ValueError, match="Invalid order_by"):
            store.list_memories(order_by="invalid")

    def test_list_filter_by_tags(self, store: MemoryStore):
        store.create_memory("py fact", tags=["python"])
        store.create_memory("js fact", tags=["javascript"])
        store.create_memory("both", tags=["python", "javascript"])

        result = store.list_memories(tags=["python"])
        assert len(result) == 2
        contents = {m.content for m in result}
        assert contents == {"py fact", "both"}

    def test_list_filter_by_tags_no_match(self, store: MemoryStore):
        store.create_memory("py fact", tags=["python"])
        result = store.list_memories(tags=["rust"])
        assert result == []

    def test_list_filter_by_tags_none(self, store: MemoryStore):
        store.create_memory("a")
        store.create_memory("b")
        assert len(store.list_memories(tags=None)) == 2


# -- get_memories ----------------------------------------------------------


class TestGetMemories:
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

    def test_no_voter_id_when_provided(self, store: MemoryStore):
        store.create_memory("a")
        result = store.get_memories(voter_id="existing")
        assert "voter_id" not in result

    def test_randomized_order(self, store: MemoryStore):
        for i in range(20):
            store.create_memory(f"m{i}")
        ids1 = [m["id"] for m in store.get_memories(voter_id="x")["memories"]]
        # Run multiple times; at least one should differ (probabilistic but safe with 20 items)
        any_different = False
        for _ in range(10):
            ids2 = [m["id"] for m in store.get_memories(voter_id="x")["memories"]]
            if ids1 != ids2:
                any_different = True
                break
        assert any_different, "get_memories should return items in random order"


# -- remove ----------------------------------------------------------------


class TestRemove:
    def test_remove(self, store: MemoryStore):
        m = store.create_memory("a")
        assert store.remove_memory(m.id) is True
        assert store.get_memory(m.id) is None

    def test_remove_nonexistent(self, store: MemoryStore):
        assert store.remove_memory("bad-id") is False


# -- get_memory ------------------------------------------------------------


class TestGetMemory:
    def test_get_existing(self, store: MemoryStore):
        m = store.create_memory("a")
        assert store.get_memory(m.id) is not None

    def test_get_nonexistent(self, store: MemoryStore):
        assert store.get_memory("nope") is None


# -- create_voter_id -------------------------------------------------------


class TestCreateVoterId:
    def test_returns_unique_uuids(self):
        ids = {MemoryStore.create_voter_id() for _ in range(100)}
        assert len(ids) == 100


# -- update_memory ---------------------------------------------------------


class TestUpdateMemory:
    def test_update_content(self, store: MemoryStore):
        m = store.create_memory("old content")
        m2 = store.update_memory(m.id, content="new content")
        assert m2.content == "new content"
        assert store.get_memory(m.id).content == "new content"

    def test_update_tags(self, store: MemoryStore):
        m = store.create_memory("fact", tags=["python"])
        m2 = store.update_memory(m.id, tags=["python", "tips"])
        assert m2.tags == ["python", "tips"]

    def test_update_preserves_votes(self, store: MemoryStore):
        m = store.create_memory("fact", voter_id="v1")
        store.upvote_memory(m.id, voter_id="v2")
        m2 = store.update_memory(m.id, content="updated fact")
        assert m2.votes == 2
        assert "v1" in m2.voters

    def test_update_nonexistent_raises(self, store: MemoryStore):
        with pytest.raises(MemoryNotFoundError):
            store.update_memory("bad-id", content="x")

    def test_update_empty_content_raises(self, store: MemoryStore):
        m = store.create_memory("fact")
        with pytest.raises(ValueError, match="content must not be empty"):
            store.update_memory(m.id, content="  ")
