# memory-mcp Design

Date: 2026-02-19

## Overview

Create a `memory-mcp/` package inside the repository that provides ChromaDB-based persistent memory for the app's AI (Gemini). This replaces the existing Firestore-based memory system in `server.py`.

The package serves two purposes:
1. **App integration**: `server.py` imports `memory_mcp.store` directly to save/recall memories
2. **MCP server**: A stdio MCP server for use with Claude Code or other MCP clients

## Goals

- AI remembers past conversations with each user, per persona
- Semantic (vector) search using Vertex AI text-embedding-004
- ChromaDB replaces Firestore as the vector store
- 5 focused tools (not the 21 in the reference implementation)

## Directory Structure

```
customer-support-demo-app/
├── memory-mcp/
│   ├── src/memory_mcp/
│   │   ├── __init__.py
│   │   ├── store.py        # ChromaDB + Vertex AI embedding operations
│   │   └── server.py       # MCP stdio server
│   ├── pyproject.toml
│   └── .env.example
├── server.py               # Modified: use memory_mcp.store instead of Firestore
```

## Data Flow

```
Session start:
  Browser → server.py(setup msg intercept)
           → memory_mcp.store.recall(user_id, persona, context)
           → ChromaDB (vector similarity search)
           → inject memories into system prompt
           → Gemini Live API

Session end:
  Browser → POST /memory/save
           → Gemini generates summary
           → memory_mcp.store.remember(summary, user_id, persona, metadata)
           → Vertex AI text-embedding-004 (768-dim)
           → ChromaDB save
```

## Data Model

**ChromaDB collection**: `memories_{user_id}_{persona}`

| Field | Type | Description |
|---|---|---|
| id | string | UUID |
| document | string | Session summary (100-300 chars) |
| embedding | vector[768] | Vertex AI text-embedding-004 |
| metadata.emotion | string | Dominant emotion (e.g. "楽しそう") |
| metadata.importance | float | 0.0–1.0 |
| metadata.keywords | string | JSON array of key topics |
| metadata.timestamp | string | ISO8601 |

## MCP Tools (5 total)

| Tool | Purpose | Called by |
|---|---|---|
| `remember` | Save session memory | server.py at session end |
| `recall` | Retrieve relevant memories | server.py at session start |
| `search_memories` | Semantic search | MCP clients |
| `list_recent_memories` | List recent memories | MCP clients |
| `get_memory_stats` | Memory statistics | MCP clients |

## server.py Changes

### Remove
- `google.cloud.firestore` import and Firestore client initialization
- `fetch_memories()` function (Firestore query)
- Firestore write in `handle_memory_save()`

### Add
- `from memory_mcp.store import recall_memories, save_memory` import
- Replace `fetch_memories()` call with `recall_memories(user_id, persona, context)`
- Replace Firestore write with `save_memory(user_id, persona, summary, metadata)`

## Dependencies

```toml
# memory-mcp/pyproject.toml
[project]
name = "memory-mcp"
version = "0.1.0"
requires-python = ">=3.10"

[project.dependencies]
mcp = ">=1.0.0"
chromadb = ">=0.5.0"
google-cloud-aiplatform = ">=1.38.0"
python-dotenv = ">=1.0.0"
```

## Configuration

```ini
# memory-mcp/.env.example
CHROMA_PERSIST_PATH=./chroma_data
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

## ChromaDB Persistence

- **Local dev**: persist to `./chroma_data/` (relative to memory-mcp/)
- **Cloud Run**: persist to `/tmp/chroma_data/` (ephemeral — consider mounting a volume or migrating to ChromaDB Cloud for production)

## Out of Scope

- Memory deletion UI
- Cross-persona memory sharing
- Advanced features from reference (episodes, sensory, theory of mind)
- ChromaDB Cloud / persistent Cloud Run storage (future work)
