"""CLI entry-point for the tidbits-memory MCP server."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from tidbits_memory.store import (
    DuplicateVoteError,
    MemoryNotFoundError,
    MemoryStore,
    RateLimitError,
)
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


def _build_store(args: argparse.Namespace) -> MemoryStore:
    backend = args.backend
    path = args.db

    if backend == "json":
        from tidbits_memory.adapters.json_file import JsonFileAdapter

        return MemoryStore(JsonFileAdapter(path))
    elif backend == "sqlite":
        from tidbits_memory.adapters.sqlite import SqliteAdapter

        return MemoryStore(SqliteAdapter(path))
    elif backend == "memory":
        from tidbits_memory.adapters.memory import InMemoryAdapter

        return MemoryStore(InMemoryAdapter())
    else:
        print(f"Unknown backend: {backend}", file=sys.stderr)
        sys.exit(1)


def _json_out(data: object) -> None:
    print(json.dumps(data, indent=2))


def cmd_create(args: argparse.Namespace) -> None:
    store = _build_store(args)
    tags = args.tags.split(",") if args.tags else None
    result = tidbits_create(
        store, args.content, creator=args.creator, tags=tags, voter_id=args.voter_id
    )
    _json_out(result)


def cmd_upvote(args: argparse.Namespace) -> None:
    store = _build_store(args)
    result = tidbits_upvote(store, args.memory_id, voter_id=args.voter_id)
    _json_out(result)


def cmd_downvote(args: argparse.Namespace) -> None:
    store = _build_store(args)
    result = tidbits_downvote(store, args.memory_id, voter_id=args.voter_id)
    _json_out(result)


def cmd_unvote(args: argparse.Namespace) -> None:
    store = _build_store(args)
    result = tidbits_unvote(store, args.memory_id, args.voter_id)
    _json_out(result)


def cmd_list(args: argparse.Namespace) -> None:
    store = _build_store(args)
    result = tidbits_list(store, order_by=args.order_by, limit=args.limit)
    _json_out(result)


def cmd_get_memories(args: argparse.Namespace) -> None:
    store = _build_store(args)
    result = tidbits_get_memories(store, voter_id=args.voter_id)
    _json_out(result)


def cmd_remove(args: argparse.Namespace) -> None:
    store = _build_store(args)
    result = tidbits_remove(store, args.memory_id)
    _json_out(result)


def cmd_create_voter_id(args: argparse.Namespace) -> None:
    result = tidbits_create_voter_id()
    _json_out(result)


def cmd_serve(args: argparse.Namespace) -> None:
    """Run a JSON-RPC style stdin/stdout server for MCP tool calls."""
    store = _build_store(args)

    dispatch = {
        "tidbits.create": lambda p: tidbits_create(
            store, p["content"],
            creator=p.get("creator"), tags=p.get("tags"), voter_id=p.get("voter_id"),
        ),
        "tidbits.upvote": lambda p: tidbits_upvote(
            store, p["memory_id"], voter_id=p.get("voter_id"),
        ),
        "tidbits.downvote": lambda p: tidbits_downvote(
            store, p["memory_id"], voter_id=p.get("voter_id"),
        ),
        "tidbits.unvote": lambda p: tidbits_unvote(
            store, p["memory_id"], p["voter_id"],
        ),
        "tidbits.list": lambda p: tidbits_list(
            store, order_by=p.get("order_by", "votes"), limit=p.get("limit"),
        ),
        "tidbits.get_memories": lambda p: tidbits_get_memories(
            store, voter_id=p.get("voter_id"),
        ),
        "tidbits.remove": lambda p: tidbits_remove(store, p["memory_id"]),
        "tidbits.create_voter_id": lambda p: tidbits_create_voter_id(),
    }

    print("tidbits-memory server ready (stdin/stdout JSON-RPC)", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            _json_out({"error": f"invalid JSON: {e}"})
            sys.stdout.flush()
            continue

        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        handler = dispatch.get(method)
        if handler is None:
            resp = {"id": req_id, "error": f"unknown method: {method}"}
        else:
            try:
                result = handler(params)
                resp = {"id": req_id, "result": result}
            except (DuplicateVoteError, RateLimitError) as e:
                resp = {"id": req_id, "error": str(e)}
            except MemoryNotFoundError as e:
                resp = {"id": req_id, "error": f"not found: {e}"}
            except Exception as e:
                resp = {"id": req_id, "error": f"internal error: {e}"}

        print(json.dumps(resp), flush=True)


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        prog="tidbits-memory",
        description="tidbits-memory: a memory/tidbits voting framework for AI agents",
    )
    parser.add_argument(
        "--backend",
        choices=["json", "sqlite", "memory"],
        default="json",
        help="Storage backend (default: json)",
    )
    parser.add_argument(
        "--db",
        default="memories.json",
        help="Path to storage file (JSON file or SQLite database, default: memories.json)",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # -- serve -------------------------------------------------------------
    p_serve = sub.add_parser("serve", help="Start stdin/stdout JSON-RPC server")

    # -- create ------------------------------------------------------------
    p_create = sub.add_parser("create", help="Create a new memory")
    p_create.add_argument("content", help="Memory content text")
    p_create.add_argument("--creator", default=None)
    p_create.add_argument("--tags", default=None, help="Comma-separated tags")
    p_create.add_argument("--voter-id", default=None)

    # -- upvote ------------------------------------------------------------
    p_upvote = sub.add_parser("upvote", help="Upvote a memory")
    p_upvote.add_argument("memory_id")
    p_upvote.add_argument("--voter-id", default=None)

    # -- downvote ----------------------------------------------------------
    p_downvote = sub.add_parser("downvote", help="Downvote a memory")
    p_downvote.add_argument("memory_id")
    p_downvote.add_argument("--voter-id", default=None)

    # -- unvote ------------------------------------------------------------
    p_unvote = sub.add_parser("unvote", help="Remove a prior vote")
    p_unvote.add_argument("memory_id")
    p_unvote.add_argument("voter_id")

    # -- list --------------------------------------------------------------
    p_list = sub.add_parser("list", help="List memories (sorted by votes desc)")
    p_list.add_argument("--order-by", default="votes", choices=["votes", "created_at"])
    p_list.add_argument("--limit", type=int, default=None)

    # -- get-memories ------------------------------------------------------
    p_get = sub.add_parser("get-memories", help="Get memories (random order, no votes)")
    p_get.add_argument("--voter-id", default=None)

    # -- remove ------------------------------------------------------------
    p_remove = sub.add_parser("remove", help="Remove a memory")
    p_remove.add_argument("memory_id")

    # -- create-voter-id ---------------------------------------------------
    sub.add_parser("create-voter-id", help="Generate a new voter_id")

    args = parser.parse_args(argv)

    commands = {
        "serve": cmd_serve,
        "create": cmd_create,
        "upvote": cmd_upvote,
        "downvote": cmd_downvote,
        "unvote": cmd_unvote,
        "list": cmd_list,
        "get-memories": cmd_get_memories,
        "remove": cmd_remove,
        "create-voter-id": cmd_create_voter_id,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
