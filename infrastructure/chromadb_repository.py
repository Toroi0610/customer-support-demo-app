"""ChromaDBMemoryRepository - ChromaDB implementation of MemoryRepository."""
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import List

import chromadb

from domain.memory.memory_record import MemoryRecord
from domain.memory.memory_repository import MemoryRepository
from .vertex_ai_embedding import VertexAIEmbeddingService

_chroma_client = None


def _get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        path = os.environ.get("CHROMA_PERSIST_PATH", "./chroma_data")
        if path.startswith("/tmp"):
            print(
                f"⚠️  CHROMA_PERSIST_PATH={path} is ephemeral — "
                "memories will be lost on container restart"
            )
        _chroma_client = chromadb.PersistentClient(path=path)
    return _chroma_client


def _collection_name(user_id: str, persona: str) -> str:
    raw = f"memories_{user_id}_{persona}"
    if len(raw) <= 63:
        return raw
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"mem_{digest}"


def _days_ago(timestamp_iso: str) -> int:
    if not timestamp_iso:
        return 0
    try:
        ts = datetime.fromisoformat(timestamp_iso)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - ts).days)
    except ValueError:
        return 0


def _record_from_row(user_id: str, persona: str, doc: str, meta: dict) -> MemoryRecord:
    return MemoryRecord(
        user_id=user_id,
        persona=persona,
        summary=doc,
        emotion=meta.get("emotion", ""),
        importance=float(meta.get("importance", 0.5)),
        keywords=json.loads(meta.get("keywords", "[]")),
        timestamp=meta.get("timestamp", ""),
        days_ago=_days_ago(meta.get("timestamp", "")),
    )


class ChromaDBMemoryRepository(MemoryRepository):
    """Stores and retrieves MemoryRecords in ChromaDB.

    Semantic search uses Vertex AI embeddings when available;
    falls back to recency-based ordering otherwise.
    """

    def __init__(
        self,
        embedding_service: VertexAIEmbeddingService = None,
        chroma_client=None,
    ) -> None:
        self._embedding = embedding_service or VertexAIEmbeddingService()
        self._client = chroma_client

    def _get_collection(self, user_id: str, persona: str):
        client = self._client or _get_chroma_client()
        return client.get_or_create_collection(
            name=_collection_name(user_id, persona)
        )

    async def save(
        self, record: MemoryRecord, embedding: List[float] = None
    ) -> str:
        """Persist a MemoryRecord and return its memory_id."""
        collection = self._get_collection(record.user_id, record.persona)
        add_kwargs = {
            "ids": [record.memory_id],
            "documents": [record.summary],
            "metadatas": [
                {
                    "emotion": record.emotion or "",
                    "importance": float(record.importance),
                    "keywords": json.dumps(record.keywords or []),
                    "timestamp": record.timestamp,
                }
            ],
        }
        if embedding:
            add_kwargs["embeddings"] = [embedding]

        await asyncio.to_thread(collection.add, **add_kwargs)
        return record.memory_id

    async def recall(
        self,
        user_id: str,
        persona: str,
        context: str = "",
        project_id: str = "",
        limit: int = 3,
    ) -> List[MemoryRecord]:
        """Retrieve relevant memories; uses semantic search when possible."""
        if not user_id or not persona:
            return []

        collection = self._get_collection(user_id, persona)
        count = await asyncio.to_thread(collection.count)
        if count == 0:
            return []

        n = min(limit, count)

        if context and project_id:
            query_embedding = await self._embedding.generate(context, project_id)
            if query_embedding:
                results = await asyncio.to_thread(
                    collection.query,
                    query_embeddings=[query_embedding],
                    n_results=n,
                    include=["documents", "metadatas"],
                )
                return [
                    _record_from_row(user_id, persona, doc, meta)
                    for doc, meta in zip(
                        results["documents"][0], results["metadatas"][0]
                    )
                ]

        # Fallback: most-recent records
        raw = await asyncio.to_thread(
            collection.get, include=["documents", "metadatas"]
        )
        pairs = sorted(
            zip(raw["documents"], raw["metadatas"]),
            key=lambda x: x[1].get("timestamp", ""),
            reverse=True,
        )
        return [_record_from_row(user_id, persona, d, m) for d, m in pairs[:n]]

    async def list_recent(
        self, user_id: str, persona: str, limit: int = 10
    ) -> List[MemoryRecord]:
        """Return memories sorted newest-first."""
        if not user_id or not persona:
            return []

        collection = self._get_collection(user_id, persona)
        raw = await asyncio.to_thread(
            collection.get, include=["documents", "metadatas"]
        )
        records = [
            _record_from_row(user_id, persona, doc, meta)
            for doc, meta in zip(raw["documents"], raw["metadatas"])
        ]
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return records[:limit]

    async def search(
        self,
        user_id: str,
        persona: str,
        query: str,
        project_id: str = "",
        limit: int = 5,
    ) -> List[MemoryRecord]:
        """Semantic search; returns records with relevance scores when available."""
        if not user_id or not persona or not query:
            return []

        collection = self._get_collection(user_id, persona)
        count = await asyncio.to_thread(collection.count)
        if count == 0:
            return []

        n = min(limit, count)

        if project_id:
            query_embedding = await self._embedding.generate(query, project_id)
            if query_embedding:
                results = await asyncio.to_thread(
                    collection.query,
                    query_embeddings=[query_embedding],
                    n_results=n,
                    include=["documents", "metadatas", "distances"],
                )
                records = []
                for doc, meta, dist in zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0],
                ):
                    r = _record_from_row(user_id, persona, doc, meta)
                    r.relevance = round(1.0 - dist, 4)
                    records.append(r)
                return records

        # Fallback: recency-based (no relevance scores)
        return await self.list_recent(user_id, persona, limit=n)

    async def get_stats(self, user_id: str, persona: str) -> dict:
        """Return summary statistics for a user+persona collection."""
        if not user_id or not persona:
            return {"total": 0}

        collection = self._get_collection(user_id, persona)
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
