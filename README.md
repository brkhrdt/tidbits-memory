# tidbits-memory

A memory/tidbits voting framework for AI agents. Agents can record learnings (facts, methods, gotchas) and vote on them to surface the most useful tidbits.

## Installation

```bash
uv pip install -e ".[dev]"
```

## Quick start

```python
from tidbits_memory.adapters.memory import InMemoryAdapter
from tidbits_memory.store import MemoryStore

store = MemoryStore(InMemoryAdapter())

# Create a voter id for this session
voter_id = store.create_voter_id()

# Create a memory
mem = store.create_memory("Python dicts preserve insertion order since 3.7", voter_id=voter_id)

# Get memories (random order, no vote counts) — ideal for agent consumption
result = store.get_memories(voter_id=voter_id)
print(result["memories"])

# Upvote a useful memory
store.upvote_memory(mem.id, voter_id="another-session-id")

# List memories sorted by votes (most upvoted first)
for m in store.list_memories():
    print(f"[{m.votes}] {m.content}")

# Downvote an erroneous memory
store.downvote_memory(mem.id, voter_id="yet-another-session")

# Unvote (remove a prior vote)
store.unvote_memory(mem.id, "another-session-id")

# Remove a memory
store.remove_memory(mem.id)
```

### Persistent storage (JSON file)

```python
from tidbits_memory.adapters.json_file import JsonFileAdapter
from tidbits_memory.store import MemoryStore

store = MemoryStore(JsonFileAdapter("memories.json"))
store.create_memory("Use `uv` for fast Python packaging")
```

### Voter ID generation

When an agent doesn't have a session/conversation ID, use `create_voter_id`:

```python
voter_id = store.create_voter_id()
# Use this voter_id for all votes in this session
```

If no `voter_id` is provided when calling `get_memories`, one is automatically generated and returned in the response.

## MCP Tool Wrappers

```python
from mcp.server import FastMCP
from tidbits_memory.adapters.memory import InMemoryAdapter
from tidbits_memory.store import MemoryStore
from tidbits_memory.tools import register_tools

store = MemoryStore(InMemoryAdapter())
mcp = FastMCP("tidbits")
register_tools(mcp, store)

# Registered tool names:
# create_memory, upvote_memory, downvote_memory, unvote_memory,
# list_memory, get_memories, remove_memory, create_voter_id
```

## Running tests

```bash
uv run pytest
```
