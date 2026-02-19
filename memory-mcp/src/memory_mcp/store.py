# memory-mcp/src/memory_mcp/store.py
"""ChromaDB memory store with Vertex AI embeddings."""

import asyncio
import hashlib
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

GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

_chroma_client = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        path = os.environ.get("CHROMA_PERSIST_PATH", "./chroma_data")
        if path.startswith("/tmp"):
            print(f"⚠️  CHROMA_PERSIST_PATH={path} is ephemeral — memories will be lost on container restart")
        _chroma_client = chromadb.PersistentClient(path=path)
    return _chroma_client


def _collection_name(user_id: str, persona: str) -> str:
    """Build a ChromaDB-safe collection name (max 63 chars, no collisions)."""
    raw = f"memories_{user_id}_{persona}"
    if len(raw) <= 63:
        return raw
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"mem_{digest}"


def _get_collection(user_id: str, persona: str, client=None):
    """Get or create a ChromaDB collection for user+persona."""
    if client is None:
        client = _get_chroma_client()
    return client.get_or_create_collection(name=_collection_name(user_id, persona))


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
            return [
                {
                    "summary": doc,
                    "emotion": meta.get("emotion", ""),
                    "importance": float(meta.get("importance", 0.5)),
                    "days_ago": _days_ago(meta.get("timestamp", "")),
                }
                for doc, meta in zip(docs, metas)
            ]

    # Fallback: return most-recent memories sorted by timestamp descending
    raw = await asyncio.to_thread(collection.get, include=["documents", "metadatas"])
    pairs = sorted(
        zip(raw["documents"], raw["metadatas"]),
        key=lambda x: x[1].get("timestamp", ""),
        reverse=True,
    )
    return [
        {
            "summary": doc,
            "emotion": meta.get("emotion", ""),
            "importance": float(meta.get("importance", 0.5)),
            "days_ago": _days_ago(meta.get("timestamp", "")),
        }
        for doc, meta in pairs[:n]
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
