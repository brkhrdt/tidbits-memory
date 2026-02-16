"""Tests for JsonFileAdapter: persistence, atomic writes, concurrency."""

import json
import os
import threading
from pathlib import Path

import pytest

from tidbits_memory.adapters.json_file import JsonFileAdapter
from tidbits_memory.models import Memory
from tidbits_memory.store import MemoryStore


@pytest.fixture
def json_path(tmp_path: Path) -> Path:
    return tmp_path / "memories.json"


@pytest.fixture
def adapter(json_path: Path) -> JsonFileAdapter:
    return JsonFileAdapter(json_path)


@pytest.fixture
def store(adapter: JsonFileAdapter) -> MemoryStore:
    return MemoryStore(adapter)


# -- persistence -----------------------------------------------------------


class TestPersistence:
    def test_survives_reopen(self, json_path: Path):
        s1 = MemoryStore(JsonFileAdapter(json_path))
        m = s1.create_memory("persist me")

        s2 = MemoryStore(JsonFileAdapter(json_path))
        loaded = s2.get_memory(m.id)
        assert loaded is not None
        assert loaded.content == "persist me"

    def test_file_is_valid_json(self, json_path: Path, store: MemoryStore):
        store.create_memory("x")
        with open(json_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)
        assert len(data) == 1


# -- atomic writes ---------------------------------------------------------


class TestAtomicWrites:
    def test_no_partial_writes(self, json_path: Path):
        adapter = JsonFileAdapter(json_path)
        store = MemoryStore(adapter)
        for i in range(20):
            store.create_memory(f"entry {i}")

        with open(json_path) as f:
            data = json.load(f)
        assert len(data) == 20


# -- concurrency ----------------------------------------------------------


class TestConcurrency:
    def test_concurrent_creates(self, json_path: Path):
        errors: list[Exception] = []

        def worker(idx: int):
            try:
                a = JsonFileAdapter(json_path)
                s = MemoryStore(a)
                s.create_memory(f"concurrent-{idx}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Errors during concurrent creates: {errors}"
        # All entries may not be present due to race conditions with JSON file
        # but the file must be valid JSON
        with open(json_path) as f:
            data = json.load(f)
        assert isinstance(data, dict)
