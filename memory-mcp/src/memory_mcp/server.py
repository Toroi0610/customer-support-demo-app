# memory-mcp/src/memory_mcp/server.py
"""MCP stdio server exposing memory_mcp.store as tools."""

import asyncio
import json
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from memory_mcp.store import (
    save_memory,
    recall_memories,
    search_memories,
    list_recent_memories,
    get_memory_stats,
)

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

app = Server("memory-mcp")


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="remember",
            description="Save a session memory. Call at session end with the conversation summary.",
            inputSchema={
                "type": "object",
                "required": ["user_id", "persona", "summary"],
                "properties": {
                    "user_id": {"type": "string", "description": "User identifier"},
                    "persona": {"type": "string", "description": "Persona name (e.g. lover_female)"},
                    "summary": {"type": "string", "description": "Session summary in Japanese (100-300 chars)"},
                    "emotion": {"type": "string", "description": "Dominant emotion in Japanese"},
                    "importance": {"type": "number", "description": "Importance score 0.0-1.0"},
                    "keywords": {"type": "array", "items": {"type": "string"}, "description": "Key topics"},
                },
            },
        ),
        Tool(
            name="recall",
            description="Retrieve relevant memories for a given context. Call at session start.",
            inputSchema={
                "type": "object",
                "required": ["user_id", "persona"],
                "properties": {
                    "user_id": {"type": "string"},
                    "persona": {"type": "string"},
                    "context": {"type": "string", "description": "Context text for semantic search"},
                    "limit": {"type": "integer", "default": 3},
                },
            },
        ),
        Tool(
            name="search_memories",
            description="Search memories by semantic similarity.",
            inputSchema={
                "type": "object",
                "required": ["user_id", "persona", "query"],
                "properties": {
                    "user_id": {"type": "string"},
                    "persona": {"type": "string"},
                    "query": {"type": "string"},
                    "limit": {"type": "integer", "default": 5},
                },
            },
        ),
        Tool(
            name="list_recent_memories",
            description="List most recent memories, newest first.",
            inputSchema={
                "type": "object",
                "required": ["user_id", "persona"],
                "properties": {
                    "user_id": {"type": "string"},
                    "persona": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="get_memory_stats",
            description="Get memory statistics: total count, emotion breakdown, avg importance.",
            inputSchema={
                "type": "object",
                "required": ["user_id", "persona"],
                "properties": {
                    "user_id": {"type": "string"},
                    "persona": {"type": "string"},
                },
            },
        ),
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "remember":
            memory_id = await save_memory(
                user_id=arguments["user_id"],
                persona=arguments["persona"],
                summary=arguments["summary"],
                emotion=arguments.get("emotion", ""),
                importance=float(arguments.get("importance", 0.5)),
                keywords=arguments.get("keywords", []),
                project_id=GOOGLE_CLOUD_PROJECT,
            )
            result = {"memory_id": memory_id, "status": "saved"}

        elif name == "recall":
            memories = await recall_memories(
                user_id=arguments["user_id"],
                persona=arguments["persona"],
                context=arguments.get("context", ""),
                project_id=GOOGLE_CLOUD_PROJECT,
                limit=int(arguments.get("limit", 3)),
            )
            result = {"memories": memories}

        elif name == "search_memories":
            memories = await search_memories(
                user_id=arguments["user_id"],
                persona=arguments["persona"],
                query=arguments["query"],
                project_id=GOOGLE_CLOUD_PROJECT,
                limit=int(arguments.get("limit", 5)),
            )
            result = {"memories": memories}

        elif name == "list_recent_memories":
            memories = await list_recent_memories(
                user_id=arguments["user_id"],
                persona=arguments["persona"],
                limit=int(arguments.get("limit", 10)),
            )
            result = {"memories": memories}

        elif name == "get_memory_stats":
            result = await get_memory_stats(
                user_id=arguments["user_id"],
                persona=arguments["persona"],
            )

        else:
            result = {"error": f"Unknown tool: {name}"}

    except Exception as e:
        result = {"error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def main():
    asyncio.run(stdio_server(app))


if __name__ == "__main__":
    main()
