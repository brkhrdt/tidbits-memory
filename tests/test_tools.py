"""Tests for MCP tool registration and invocation via FastMCP."""

import json

import pytest
from mcp.server import FastMCP

from tidbits_memory.adapters.memory import InMemoryAdapter
from tidbits_memory.store import MemoryStore
from tidbits_memory.tools import register_tools


@pytest.fixture
def mcp_server():
    store = MemoryStore(InMemoryAdapter())
    mcp = FastMCP("test-tidbits")
    register_tools(mcp, store)
    return mcp


class TestToolRegistration:
    def test_all_tools_registered(self, mcp_server):
        tool_names = [t.name for t in mcp_server._tool_manager.list_tools()]
        expected = [
            "tidbits_create",
            "tidbits_upvote",
            "tidbits_downvote",
            "tidbits_unvote",
            "tidbits_list",
            "tidbits_get_memories",
            "tidbits_remove",
            "tidbits_create_voter_id",
        ]
        for name in expected:
            assert name in tool_names, f"Tool {name!r} not registered"


class TestToolInvocation:
    @staticmethod
    def _parse(result):
        """Extract JSON from FastMCP call_tool return value."""
        return json.loads(result[0][0].text)

    @pytest.mark.asyncio
    async def test_create(self, mcp_server):
        result = await mcp_server.call_tool(
            "tidbits_create", {"content": "test memory"}
        )
        data = self._parse(result)
        assert data["content"] == "test memory"
        assert data["votes"] == 1

    @pytest.mark.asyncio
    async def test_create_and_list(self, mcp_server):
        await mcp_server.call_tool("tidbits_create", {"content": "m1"})
        await mcp_server.call_tool("tidbits_create", {"content": "m2"})
        result = await mcp_server.call_tool("tidbits_list", {})
        # FastMCP returns one TextContent per list item
        assert len(result[0]) == 2

    @pytest.mark.asyncio
    async def test_upvote(self, mcp_server):
        r = await mcp_server.call_tool("tidbits_create", {"content": "a"})
        mem = self._parse(r)
        r = await mcp_server.call_tool(
            "tidbits_upvote", {"memory_id": mem["id"], "voter_id": "v1"}
        )
        assert self._parse(r)["votes"] == 2

    @pytest.mark.asyncio
    async def test_downvote(self, mcp_server):
        r = await mcp_server.call_tool("tidbits_create", {"content": "a"})
        mem = self._parse(r)
        r = await mcp_server.call_tool(
            "tidbits_downvote", {"memory_id": mem["id"], "voter_id": "v1"}
        )
        assert self._parse(r)["votes"] == 0

    @pytest.mark.asyncio
    async def test_unvote(self, mcp_server):
        r = await mcp_server.call_tool(
            "tidbits_create", {"content": "a", "voter_id": "v1"}
        )
        mem = self._parse(r)
        r = await mcp_server.call_tool(
            "tidbits_unvote", {"memory_id": mem["id"], "voter_id": "v1"}
        )
        assert self._parse(r)["votes"] == 0

    @pytest.mark.asyncio
    async def test_get_memories(self, mcp_server):
        await mcp_server.call_tool("tidbits_create", {"content": "a"})
        r = await mcp_server.call_tool("tidbits_get_memories", {})
        data = self._parse(r)
        assert "memories" in data
        assert "voter_id" in data
        assert "votes" not in data["memories"][0]

    @pytest.mark.asyncio
    async def test_remove(self, mcp_server):
        r = await mcp_server.call_tool("tidbits_create", {"content": "rm"})
        mem = self._parse(r)
        r = await mcp_server.call_tool(
            "tidbits_remove", {"memory_id": mem["id"]}
        )
        assert self._parse(r)["removed"] is True

    @pytest.mark.asyncio
    async def test_create_voter_id(self, mcp_server):
        r = await mcp_server.call_tool("tidbits_create_voter_id", {})
        data = self._parse(r)
        assert "voter_id" in data
