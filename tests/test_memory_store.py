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
