# memory-mcp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the Firestore-based memory system in `server.py` with a ChromaDB-based `memory-mcp` package so the app's AI (Gemini) can retain memories across sessions using semantic search.

**Architecture:** Create `memory-mcp/` as a Python package in the repo. `server.py` imports `memory_mcp.store` directly (no HTTP/MCP process boundary). The package also exposes an MCP stdio server for Claude Code use. Vertex AI text-embedding-004 embeddings are preserved; ChromaDB replaces Firestore as the vector store.

**Tech Stack:** Python 3.12, chromadb>=0.5.0, aiohttp (existing), Vertex AI text-embedding-004 (existing), mcp>=1.0.0, pytest-asyncio

---

## Task 1: Scaffold memory-mcp package

**Files:**
- Create: `memory-mcp/pyproject.toml`
- Create: `memory-mcp/.env.example`
- Create: `memory-mcp/src/memory_mcp/__init__.py`

**Step 1: Create pyproject.toml**

```toml
# memory-mcp/pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "memory-mcp"
version = "0.1.0"
description = "ChromaDB memory store for AI companion app"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
    "chromadb>=0.5.0",
    "google-cloud-aiplatform>=1.38.0",
    "aiohttp>=3.9.0",
    "certifi>=2023.7.22",
    "google-auth>=2.23.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]

[project.scripts]
memory-mcp = "memory_mcp.server:main"

[tool.hatch.build.targets.wheel]
packages = ["src/memory_mcp"]

[tool.pytest.ini_options]
asyncio_mode = "auto"

[tool.ruff]
line-length = 120
target-version = "py310"
```

**Step 2: Create .env.example**

```ini
# memory-mcp/.env.example
CHROMA_PERSIST_PATH=./chroma_data
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

**Step 3: Create __init__.py**

```python
# memory-mcp/src/memory_mcp/__init__.py
```

(empty file — just marks it as a package)

**Step 4: Verify structure**

```
memory-mcp/
├── pyproject.toml
├── .env.example
└── src/
    └── memory_mcp/
        └── __init__.py
```

**Step 5: Commit**

```bash
git add memory-mcp/
git commit -m "feat: scaffold memory-mcp package structure"
```

---

## Task 2: Write failing tests for store.py

**Files:**
- Create: `tests/test_memory_store.py`

**Step 1: Create test file**

```python
# tests/test_memory_store.py
"""Tests for memory_mcp.store — ChromaDB memory operations."""

import pytest
import chromadb
from unittest.mock import patch, AsyncMock

from memory_mcp.store import (
    save_memory,
    recall_memories,
    search_memories,
    list_recent_memories,
    get_memory_stats,
    _days_ago,
)

FAKE_EMBEDDING = [0.1] * 768


@pytest.fixture
def mem():
    """Ephemeral (in-memory) ChromaDB client for test isolation."""
    return chromadb.EphemeralClient()


# ─── _days_ago ────────────────────────────────────────────────────────────────

def test_days_ago_today():
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    assert _days_ago(ts) == 0


def test_days_ago_empty_string():
    assert _days_ago("") == 0


def test_days_ago_invalid_string():
    assert _days_ago("not-a-date") == 0


# ─── save_memory ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_memory_returns_uuid(mem):
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=FAKE_EMBEDDING)):
        memory_id = await save_memory(
            "user1", "lover_female", "楽しく話した", "楽しそう", 0.8, ["仕事"],
            chroma_client=mem,
        )
    assert isinstance(memory_id, str)
    assert len(memory_id) == 36  # UUID format


@pytest.mark.asyncio
async def test_save_memory_stores_document(mem):
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=FAKE_EMBEDDING)):
        await save_memory("u1", "p1", "テスト記憶", "穏やか", 0.5, [], chroma_client=mem)
        results = await list_recent_memories("u1", "p1", chroma_client=mem)
    assert len(results) == 1
    assert results[0]["summary"] == "テスト記憶"


@pytest.mark.asyncio
async def test_save_memory_raises_on_missing_user_id(mem):
    with pytest.raises(ValueError, match="user_id"):
        await save_memory("", "p1", "summary", "emotion", 0.5, [], chroma_client=mem)


@pytest.mark.asyncio
async def test_save_memory_raises_on_missing_persona(mem):
    with pytest.raises(ValueError, match="persona"):
        await save_memory("u1", "", "summary", "emotion", 0.5, [], chroma_client=mem)


@pytest.mark.asyncio
async def test_save_memory_raises_on_missing_summary(mem):
    with pytest.raises(ValueError, match="summary"):
        await save_memory("u1", "p1", "", "emotion", 0.5, [], chroma_client=mem)


@pytest.mark.asyncio
async def test_save_memory_works_without_embedding(mem):
    """Falls back gracefully when embedding returns empty (no Vertex AI)."""
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=[])):
        memory_id = await save_memory(
            "u1", "p1", "記憶", "楽しそう", 0.7, [], chroma_client=mem
        )
    assert isinstance(memory_id, str)


# ─── recall_memories ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_recall_returns_saved_memory(mem):
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=FAKE_EMBEDDING)):
        await save_memory("u1", "p1", "疲れていた", "疲れている", 0.7, [], chroma_client=mem)
        results = await recall_memories("u1", "p1", "今日の状態", chroma_client=mem)
    assert len(results) == 1
    assert results[0]["summary"] == "疲れていた"
    assert results[0]["emotion"] == "疲れている"
    assert "importance" in results[0]
    assert "days_ago" in results[0]


@pytest.mark.asyncio
async def test_recall_empty_collection_returns_empty(mem):
    results = await recall_memories("u1", "p1", "context", chroma_client=mem)
    assert results == []


@pytest.mark.asyncio
async def test_recall_returns_empty_on_missing_user_id(mem):
    results = await recall_memories("", "p1", chroma_client=mem)
    assert results == []


@pytest.mark.asyncio
async def test_recall_respects_limit(mem):
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=FAKE_EMBEDDING)):
        for i in range(5):
            await save_memory("u1", "p1", f"記憶{i}", "楽しそう", 0.5, [], chroma_client=mem)
        results = await recall_memories("u1", "p1", "context", limit=2, chroma_client=mem)
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_recall_falls_back_when_no_embedding(mem):
    """Returns recent memories when embedding generation fails."""
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=[])):
        await save_memory("u1", "p1", "古い話", "穏やか", 0.5, [], chroma_client=mem)
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=[])):
        results = await recall_memories("u1", "p1", "context", chroma_client=mem)
    assert len(results) == 1


# ─── list_recent_memories ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_recent_newest_first(mem):
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=FAKE_EMBEDDING)):
        await save_memory("u2", "p2", "古い記憶", "穏やか", 0.5, [], chroma_client=mem)
        await save_memory("u2", "p2", "新しい記憶", "楽しそう", 0.8, [], chroma_client=mem)
        results = await list_recent_memories("u2", "p2", chroma_client=mem)
    assert results[0]["summary"] == "新しい記憶"


@pytest.mark.asyncio
async def test_list_recent_respects_limit(mem):
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=FAKE_EMBEDDING)):
        for i in range(5):
            await save_memory("u3", "p3", f"記憶{i}", "楽しそう", 0.5, [], chroma_client=mem)
        results = await list_recent_memories("u3", "p3", limit=3, chroma_client=mem)
    assert len(results) == 3


# ─── get_memory_stats ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_stats_empty_returns_zero(mem):
    stats = await get_memory_stats("u4", "p4", chroma_client=mem)
    assert stats["total"] == 0


@pytest.mark.asyncio
async def test_stats_counts_correctly(mem):
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=FAKE_EMBEDDING)):
        await save_memory("u5", "p5", "話した", "楽しそう", 0.9, [], chroma_client=mem)
        await save_memory("u5", "p5", "疲れた", "疲れている", 0.6, [], chroma_client=mem)
        stats = await get_memory_stats("u5", "p5", chroma_client=mem)
    assert stats["total"] == 2
    assert "emotions" in stats
    assert stats["emotions"]["楽しそう"] == 1
    assert stats["emotions"]["疲れている"] == 1
    assert "avg_importance" in stats


# ─── search_memories ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_empty_query_returns_empty(mem):
    results = await search_memories("u1", "p1", "", chroma_client=mem)
    assert results == []


@pytest.mark.asyncio
async def test_search_returns_results_with_relevance(mem):
    with patch("memory_mcp.store._generate_embedding", AsyncMock(return_value=FAKE_EMBEDDING)):
        await save_memory("u6", "p6", "仕事の話", "穏やか", 0.6, ["仕事"], chroma_client=mem)
        results = await search_memories("u6", "p6", "仕事", chroma_client=mem)
    assert len(results) == 1
    assert results[0]["summary"] == "仕事の話"
```

**Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_memory_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'memory_mcp'`

**Step 3: Commit**

```bash
git add tests/test_memory_store.py
git commit -m "test: add failing tests for memory_mcp.store"
```

---

## Task 3: Implement store.py

**Files:**
- Create: `memory-mcp/src/memory_mcp/store.py`

**Step 1: Install chromadb**

```bash
pip install chromadb>=0.5.0
```

Also add to `requirements.txt`:
```
chromadb>=0.5.0
```

**Step 2: Install memory-mcp in editable mode**

```bash
pip install -e ./memory-mcp
```

**Step 3: Create store.py**

```python
# memory-mcp/src/memory_mcp/store.py
"""ChromaDB memory store with Vertex AI embeddings."""

import asyncio
import json
import os
import ssl
import uuid
from datetime import datetime, timezone

import aiohttp
import certifi
import chromadb
import google.auth
from google.auth.transport.requests import Request

CHROMA_PERSIST_PATH = os.environ.get("CHROMA_PERSIST_PATH", "./chroma_data")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

_chroma_client = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)
    return _chroma_client


def _get_collection(user_id: str, persona: str, client=None):
    """Get or create a ChromaDB collection for user+persona."""
    if client is None:
        client = _get_chroma_client()
    name = f"memories_{user_id}_{persona}"[:63]
    return client.get_or_create_collection(name=name)


def _days_ago(timestamp_iso: str) -> int:
    """Return number of days since the given ISO timestamp. Returns 0 on invalid input."""
    if not timestamp_iso:
        return 0
    try:
        ts = datetime.fromisoformat(timestamp_iso)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - ts).days)
    except ValueError:
        return 0


def _get_access_token() -> str:
    """Get Google Cloud access token using application default credentials."""
    try:
        creds, _ = google.auth.default()
        if not creds.valid:
            creds.refresh(Request())
        return creds.token
    except Exception as e:
        print(f"Error getting access token: {e}")
        return ""


async def _generate_embedding(text: str, project_id: str = "") -> list:
    """Generate 768-dim embedding using Vertex AI text-embedding-004."""
    project_id = project_id or GOOGLE_CLOUD_PROJECT
    token = _get_access_token()
    if not token or not project_id:
        return []
    url = (
        f"https://us-central1-aiplatform.googleapis.com/v1/projects/{project_id}"
        f"/locations/us-central1/publishers/google/models/text-embedding-004:predict"
    )
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"instances": [{"content": text}]},
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                ssl=ssl_context,
            ) as resp:
                if resp.status != 200:
                    print(f"Embedding API error: {resp.status}")
                    return []
                data = await resp.json()
                return data["predictions"][0]["embeddings"]["values"]
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []


async def save_memory(
    user_id: str,
    persona: str,
    summary: str,
    emotion: str,
    importance: float,
    keywords: list,
    project_id: str = "",
    *,
    chroma_client=None,
) -> str:
    """Save a session memory to ChromaDB. Returns memory_id (UUID)."""
    if not user_id:
        raise ValueError("user_id is required")
    if not persona:
        raise ValueError("persona is required")
    if not summary:
        raise ValueError("summary is required")

    embedding = await _generate_embedding(summary, project_id)

    memory_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    collection = _get_collection(user_id, persona, client=chroma_client)
    add_kwargs = {
        "ids": [memory_id],
        "documents": [summary],
        "metadatas": [{
            "emotion": emotion or "",
            "importance": float(importance),
            "keywords": json.dumps(keywords or []),
            "timestamp": now,
        }],
    }
    if embedding:
        add_kwargs["embeddings"] = [embedding]

    await asyncio.to_thread(collection.add, **add_kwargs)
    return memory_id


async def recall_memories(
    user_id: str,
    persona: str,
    context: str = "",
    project_id: str = "",
    limit: int = 3,
    *,
    chroma_client=None,
) -> list:
    """Retrieve relevant memories for the given context via semantic search.

    Returns list of dicts: {summary, emotion, importance, days_ago}.
    Falls back to most-recent when embedding generation fails.
    """
    if not user_id or not persona:
        return []

    collection = _get_collection(user_id, persona, client=chroma_client)
    count = await asyncio.to_thread(collection.count)
    if count == 0:
        return []

    n = min(limit, count)

    if context:
        query_embedding = await _generate_embedding(context, project_id)
        if query_embedding:
            results = await asyncio.to_thread(
                collection.query,
                query_embeddings=[query_embedding],
                n_results=n,
                include=["documents", "metadatas"],
            )
            docs = results["documents"][0]
            metas = results["metadatas"][0]
        else:
            raw = await asyncio.to_thread(collection.get, include=["documents", "metadatas"])
            docs = raw["documents"][:n]
            metas = raw["metadatas"][:n]
    else:
        raw = await asyncio.to_thread(collection.get, include=["documents", "metadatas"])
        docs = raw["documents"][:n]
        metas = raw["metadatas"][:n]

    return [
        {
            "summary": doc,
            "emotion": meta.get("emotion", ""),
            "importance": float(meta.get("importance", 0.5)),
            "days_ago": _days_ago(meta.get("timestamp", "")),
        }
        for doc, meta in zip(docs, metas)
    ]


async def search_memories(
    user_id: str,
    persona: str,
    query: str,
    project_id: str = "",
    limit: int = 5,
    *,
    chroma_client=None,
) -> list:
    """Search memories semantically. Returns results with relevance score."""
    if not user_id or not persona or not query:
        return []

    collection = _get_collection(user_id, persona, client=chroma_client)
    count = await asyncio.to_thread(collection.count)
    if count == 0:
        return []

    n = min(limit, count)
    query_embedding = await _generate_embedding(query, project_id)

    if query_embedding:
        results = await asyncio.to_thread(
            collection.query,
            query_embeddings=[query_embedding],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]
    else:
        raw = await asyncio.to_thread(collection.get, limit=n, include=["documents", "metadatas"])
        docs = raw["documents"]
        metas = raw["metadatas"]
        distances = [None] * len(docs)

    return [
        {
            "summary": doc,
            "emotion": meta.get("emotion", ""),
            "importance": float(meta.get("importance", 0.5)),
            "days_ago": _days_ago(meta.get("timestamp", "")),
            "relevance": round(1.0 - dist, 4) if dist is not None else None,
        }
        for doc, meta, dist in zip(docs, metas, distances)
    ]


async def list_recent_memories(
    user_id: str,
    persona: str,
    limit: int = 10,
    *,
    chroma_client=None,
) -> list:
    """List memories sorted by timestamp descending (newest first)."""
    if not user_id or not persona:
        return []

    collection = _get_collection(user_id, persona, client=chroma_client)
    raw = await asyncio.to_thread(collection.get, include=["documents", "metadatas"])

    items = [
        {
            "summary": doc,
            "emotion": meta.get("emotion", ""),
            "importance": float(meta.get("importance", 0.5)),
            "days_ago": _days_ago(meta.get("timestamp", "")),
            "timestamp": meta.get("timestamp", ""),
        }
        for doc, meta in zip(raw["documents"], raw["metadatas"])
    ]
    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items[:limit]


async def get_memory_stats(
    user_id: str,
    persona: str,
    *,
    chroma_client=None,
) -> dict:
    """Return memory statistics: total count, emotion breakdown, avg importance."""
    if not user_id or not persona:
        return {"total": 0}

    collection = _get_collection(user_id, persona, client=chroma_client)
    count = await asyncio.to_thread(collection.count)
    if count == 0:
        return {"total": 0}

    raw = await asyncio.to_thread(collection.get, include=["metadatas"])

    emotions: dict[str, int] = {}
    importances: list[float] = []
    for meta in raw["metadatas"]:
        e = meta.get("emotion", "unknown")
        emotions[e] = emotions.get(e, 0) + 1
        importances.append(float(meta.get("importance", 0.5)))

    return {
        "total": count,
        "emotions": emotions,
        "avg_importance": round(sum(importances) / len(importances), 2),
    }
```

**Step 4: Run tests**

```bash
pytest tests/test_memory_store.py -v
```

Expected: All tests PASS.

**Step 5: Commit**

```bash
git add memory-mcp/src/memory_mcp/store.py requirements.txt
git commit -m "feat: implement memory_mcp.store with ChromaDB and Vertex AI embeddings"
```

---

## Task 4: Implement MCP server

**Files:**
- Create: `memory-mcp/src/memory_mcp/server.py`

**Step 1: Create MCP server**

```python
# memory-mcp/src/memory_mcp/server.py
"""MCP stdio server exposing memory_mcp.store as tools."""

import asyncio
import json
import os
import sys

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
```

**Step 2: Verify import works**

```bash
python -c "from memory_mcp.server import app; print('OK')"
```

Expected: `OK`

**Step 3: Commit**

```bash
git add memory-mcp/src/memory_mcp/server.py
git commit -m "feat: add MCP stdio server for memory-mcp"
```

---

## Task 5: Update server.py to use memory_mcp.store

**Files:**
- Modify: `server.py`

This task replaces Firestore memory with ChromaDB. The non-memory parts of server.py (WebSocket proxy, frame analysis, auth, summary generation) are unchanged.

**Step 1: Remove Firestore import and client**

In `server.py`, remove lines 29 and 37-44:

```python
# REMOVE this line:
from google.cloud import firestore

# REMOVE these lines:
_db = None

def get_db():
    global _db
    if _db is None:
        _db = firestore.AsyncClient()
    return _db
```

**Step 2: Add memory_mcp import**

After the existing imports block (after `from datetime import datetime, timezone`), add:

```python
from memory_mcp import store as memory_store
```

**Step 3: Remove cosine_similarity function**

Remove lines 49-56 (the `cosine_similarity` function). It was only used internally and is no longer needed.

**Step 4: Remove generate_embedding function**

Remove lines 97-126 (the `generate_embedding` function). It has been moved to `memory_mcp/store.py`.

**Step 5: Replace get_memories() with memory_store.recall_memories()**

Remove the existing `get_memories()` function (lines 194-226) and replace with:

```python
async def get_memories(user_id: str, persona: str, limit: int = 3) -> list:
    """Fetch relevant memories for a user+persona from ChromaDB."""
    return await memory_store.recall_memories(user_id, persona, limit=limit)
```

**Step 6: Replace Firestore write in handle_memory_save()**

In `handle_memory_save()`, replace the block that calls `generate_embedding` and writes to Firestore (approximately lines 659-676):

**Remove:**
```python
        # Embedding stored for future semantic search (not yet used for retrieval).
        # Currently get_memories() retrieves by importance + recency.
        embedding = await generate_embedding(summary_data.get("summary", ""), project_id)

        db = get_db()
        memory_id = str(uuid.uuid4())
        doc_ref = db.collection("memories").document(user_id).collection(persona).document(memory_id)
        await doc_ref.set({
            "summary": summary_data.get("summary", ""),
            "emotion": summary_data.get("emotion", ""),
            "importance": float(summary_data.get("importance", 0.5)),
            "keywords": summary_data.get("keywords", []),
            "embedding": embedding,
            "persona": persona,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
```

**Add:**
```python
        memory_id = await memory_store.save_memory(
            user_id=user_id,
            persona=persona,
            summary=summary_data.get("summary", ""),
            emotion=summary_data.get("emotion", ""),
            importance=float(summary_data.get("importance", 0.5)),
            keywords=summary_data.get("keywords", []),
            project_id=project_id,
        )
```

**Step 7: Remove uuid import (now handled in store.py)**

Check if `uuid` is still used elsewhere in server.py. If not, remove `import uuid` from line 28.

(Confirm: `uuid` is only used in the old Firestore block. Remove it.)

**Step 8: Verify server.py starts without errors**

```bash
python -c "import server; print('OK')"
```

Expected: `OK` (no ImportError)

**Step 9: Commit**

```bash
git add server.py
git commit -m "feat: replace Firestore memory with memory_mcp.store (ChromaDB)"
```

---

## Task 6: Update server.py tests

**Files:**
- Modify: `tests/test_memory.py`

**Step 1: Remove TestCosimeSimilarity class**

`cosine_similarity` has been removed from server.py. Delete the entire `TestCosimeSimilarity` class (lines 8-19).

**Step 2: Run the remaining tests to confirm they still pass**

```bash
pytest tests/test_memory.py tests/test_auth.py -v
```

Expected: All tests PASS. The `TestFormatMemoriesForPrompt` and `TestInjectMemoriesIntoSetup` tests should continue to pass since those functions remain in server.py unchanged.

**Step 3: Commit**

```bash
git add tests/test_memory.py
git commit -m "test: remove cosine_similarity tests (function moved to memory_mcp.store)"
```

---

## Task 7: Update Dockerfile and requirements.txt

**Files:**
- Modify: `Dockerfile`
- Modify: `requirements.txt`

**Step 1: Update requirements.txt**

Add chromadb, remove firestore:

```
websockets>=12.0
google-auth>=2.23.0
certifi>=2023.7.22
aiohttp>=3.9.0
google-cloud-aiplatform>=1.38.0
chromadb>=0.5.0
```

(Remove `google-cloud-firestore>=2.19.0`)

**Step 2: Update Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy memory-mcp source so it's importable as memory_mcp
COPY memory-mcp/src/memory_mcp/ ./memory_mcp/

COPY server.py .

ENV PORT=8080
ENV CHROMA_PERSIST_PATH=/tmp/chroma_data
EXPOSE 8080

CMD ["python", "server.py"]
```

Note: `CHROMA_PERSIST_PATH=/tmp/chroma_data` is ephemeral on Cloud Run. For production persistence, mount a Cloud Storage FUSE volume or migrate to ChromaDB Cloud.

**Step 3: Run full test suite to confirm nothing is broken**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add Dockerfile requirements.txt
git commit -m "feat: update Dockerfile and requirements for ChromaDB memory"
```

---

## Task 8: Manual smoke test

**Step 1: Start server locally**

```bash
APP_PASSWORD=test GOOGLE_CLOUD_PROJECT=your-project python server.py
```

Expected: Server starts on port 8080 without errors.

**Step 2: Test memory save endpoint**

```bash
curl -X POST http://localhost:8080/memory/save \
  -H "Authorization: Bearer test" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-001",
    "persona": "lover_female",
    "transcript": [{"role": "user", "text": "今日は疲れた"}, {"role": "model", "text": "お疲れ様！"}],
    "emotions": ["疲れている"],
    "project_id": "your-project"
  }'
```

Expected: `{"memory_id": "...", "summary": "..."}`

**Step 3: Confirm ChromaDB file created**

```bash
ls ./chroma_data/
```

Expected: ChromaDB files present.

**Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete memory-mcp integration — ChromaDB replaces Firestore for session memory"
```

---

## Summary of Changes

| File | Change |
|---|---|
| `memory-mcp/pyproject.toml` | New — package config |
| `memory-mcp/src/memory_mcp/__init__.py` | New — package marker |
| `memory-mcp/src/memory_mcp/store.py` | New — ChromaDB + Vertex AI store |
| `memory-mcp/src/memory_mcp/server.py` | New — MCP stdio server |
| `memory-mcp/.env.example` | New — config template |
| `tests/test_memory_store.py` | New — store tests |
| `server.py` | Modified — remove Firestore, use memory_mcp.store |
| `tests/test_memory.py` | Modified — remove cosine_similarity tests |
| `requirements.txt` | Modified — add chromadb, remove firestore |
| `Dockerfile` | Modified — copy memory_mcp/, set CHROMA_PERSIST_PATH |
