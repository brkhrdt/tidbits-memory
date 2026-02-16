"""Tests for the CLI entry-point (build_mcp_server)."""

import json

import pytest

from tidbits_memory.cli import build_mcp_server


class TestBuildMcpServer:
    def test_memory_backend(self):
        mcp = build_mcp_server(backend="memory", db="")
        tool_names = [t.name for t in mcp._tool_manager.list_tools()]
        assert "create_memory" in tool_names

    def test_sqlite_backend(self, tmp_path):
        db = str(tmp_path / "test.db")
        mcp = build_mcp_server(backend="sqlite", db=db)
        tool_names = [t.name for t in mcp._tool_manager.list_tools()]
        assert "create_memory" in tool_names

    def test_json_backend(self, tmp_path):
        db = str(tmp_path / "test.json")
        mcp = build_mcp_server(backend="json", db=db)
        tool_names = [t.name for t in mcp._tool_manager.list_tools()]
        assert "create_memory" in tool_names

    @pytest.mark.asyncio
    async def test_end_to_end_sqlite(self, tmp_path):
        db = str(tmp_path / "test.db")
        mcp = build_mcp_server(backend="sqlite", db=db)
        r = await mcp.call_tool("create_memory", {"content": "via cli"})
        data = json.loads(r[0][0].text)
        assert data["content"] == "via cli"
