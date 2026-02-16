"""Tests for the Memory data model."""

import uuid

from tidbits_memory.models import Memory, VoteRecord


class TestVoteRecord:
    def test_roundtrip(self):
        vr = VoteRecord(value=1, timestamp="2026-01-01T00:00:00+00:00")
        d = vr.to_dict()
        assert d == {"value": 1, "timestamp": "2026-01-01T00:00:00+00:00"}
        assert VoteRecord.from_dict(d) == vr

    def test_negative_value(self):
        vr = VoteRecord(value=-1, timestamp="2026-01-01T00:00:00+00:00")
        assert VoteRecord.from_dict(vr.to_dict()) == vr


class TestMemory:
    def test_defaults(self):
        m = Memory(content="hello")
        assert m.content == "hello"
        assert m.votes == 1
        assert uuid.UUID(m.id)  # valid uuid
        assert m.tags == []
        assert m.voters == {}
        assert m.creator is None

    def test_roundtrip(self):
        m = Memory(
            content="test",
            creator="agent-1",
            tags=["python"],
            voters={"vid": VoteRecord(value=1, timestamp="2026-01-01T00:00:00+00:00")},
        )
        d = m.to_dict()
        m2 = Memory.from_dict(d)
        assert m2.content == m.content
        assert m2.creator == m.creator
        assert m2.tags == m.tags
        assert m2.voters["vid"].value == 1

    def test_to_dict_contains_all_fields(self):
        m = Memory(content="x")
        d = m.to_dict()
        expected_keys = {
            "id", "content", "votes", "created_at", "last_updated",
            "creator", "tags", "voters", "last_anon_vote_at",
        }
        assert set(d.keys()) == expected_keys
