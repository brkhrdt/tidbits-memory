"""Tests for the CLI entry-point."""

import json
import subprocess
import sys
from pathlib import Path

import pytest


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "tidbits_memory.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


class TestCliCommands:
    def test_create_voter_id(self, tmp_path: Path):
        r = _run_cli("--backend", "memory", "create-voter-id", cwd=tmp_path)
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "voter_id" in data

    def test_create_and_list_json(self, tmp_path: Path):
        db = str(tmp_path / "mem.json")
        r = _run_cli("--backend", "json", "--db", db, "create", "hello world")
        assert r.returncode == 0
        created = json.loads(r.stdout)
        assert created["content"] == "hello world"

        r = _run_cli("--backend", "json", "--db", db, "list")
        assert r.returncode == 0
        items = json.loads(r.stdout)
        assert len(items) == 1

    def test_create_and_list_sqlite(self, tmp_path: Path):
        db = str(tmp_path / "mem.db")
        r = _run_cli("--backend", "sqlite", "--db", db, "create", "sqlite test")
        assert r.returncode == 0

        r = _run_cli("--backend", "sqlite", "--db", db, "list")
        assert r.returncode == 0
        items = json.loads(r.stdout)
        assert len(items) == 1
        assert items[0]["content"] == "sqlite test"

    def test_upvote_downvote_remove(self, tmp_path: Path):
        db = str(tmp_path / "mem.db")
        r = _run_cli("--backend", "sqlite", "--db", db, "create", "voteable")
        mid = json.loads(r.stdout)["id"]

        r = _run_cli("--backend", "sqlite", "--db", db, "upvote", mid, "--voter-id", "v1")
        assert r.returncode == 0
        assert json.loads(r.stdout)["votes"] == 2

        r = _run_cli("--backend", "sqlite", "--db", db, "downvote", mid, "--voter-id", "v2")
        assert r.returncode == 0
        assert json.loads(r.stdout)["votes"] == 1

        r = _run_cli("--backend", "sqlite", "--db", db, "remove", mid)
        assert r.returncode == 0
        assert json.loads(r.stdout)["removed"] is True

    def test_get_memories(self, tmp_path: Path):
        db = str(tmp_path / "mem.db")
        _run_cli("--backend", "sqlite", "--db", db, "create", "a")
        r = _run_cli("--backend", "sqlite", "--db", db, "get-memories")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "memories" in data
        assert "voter_id" in data

    def test_serve_processes_request(self, tmp_path: Path):
        db = str(tmp_path / "mem.db")
        req = json.dumps({"id": 1, "method": "tidbits.create", "params": {"content": "from server"}})
        proc = subprocess.run(
            [sys.executable, "-m", "tidbits_memory.cli", "--backend", "sqlite", "--db", db, "serve"],
            input=req + "\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert proc.returncode == 0
        resp = json.loads(proc.stdout.strip())
        assert resp["id"] == 1
        assert resp["result"]["content"] == "from server"
