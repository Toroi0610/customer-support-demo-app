# Memory System Design

Date: 2026-02-19

## Overview

Add long-term memory to the AI companion app so each persona can remember past conversations with the user. Memories persist across sessions using Firestore vector search and Vertex AI embeddings.

## Goals

- AI automatically recalls relevant past conversations at session start
- Memories are scoped per persona (lover_female memories are separate from bright_friend memories)
- Semantic (vector) search, not keyword matching
- Metadata: emotion, importance, keywords, timestamp

## Architecture

```
[Browser]
  Session start ─────────────────────────────────────────────▶ [Cloud Run: server.py]
               setup message {user_id, persona, app_password}     │
                                                                   ├─▶ Query Firestore for relevant memories (vector search)
                                                                   ├─▶ Inject memories into system prompt
                                                                   └─▶ Forward modified setup to [Gemini Live API]

  Session end ───────────────────────────────────────────────▶ POST /memory/save
              {transcript, persona, user_id, emotions[]}           │
                                                                   ├─▶ Generate summary via Gemini
                                                                   ├─▶ Embed with Vertex AI text-embedding-004
                                                                   └─▶ Save to Firestore
```

## Data Model

**Firestore schema:**
```
memories (collection)
  └─ {user_id} (document)
       └─ {persona} (sub-collection)
            └─ {memory_id} (document)
                 ├─ summary: string        # 100-300 char session summary in Japanese
                 ├─ embedding: vector      # 768-dim from text-embedding-004
                 ├─ emotion: string        # dominant emotion e.g. "楽しそう", "疲れている"
                 ├─ importance: float      # 0.0–1.0 (Gemini-rated)
                 ├─ keywords: []string     # key topics from conversation
                 └─ timestamp: datetime
```

**User identification:** Since there is no per-user auth (shared app password), a UUID is generated in `localStorage` on first visit and reused as `user_id`.

## API Changes

### New endpoint: `POST /memory/save`

```
Request:
  Authorization: Bearer {app_password}
  {
    "user_id": "uuid-xxx",
    "persona": "lover_female",
    "transcript": [...],        # array of {role, text} messages
    "emotions": ["楽しそう"]    # emotion events observed during session
  }

Response:
  { "memory_id": "...", "summary": "..." }
```

### Modified: WebSocket setup message handling

When the server receives a setup message over `/ws`, before forwarding to Gemini:
1. Extract `user_id` and `persona`
2. Query Firestore: find top-3 most similar memories for this persona (vector search on a query embedding derived from the persona prompt)
3. Format memories as a `[過去の記憶]` block
4. Inject into the system prompt within the setup message
5. Forward modified setup to Gemini

**System prompt injection example:**
```
[過去の記憶]
- 3日前: ユーザーは仕事で疲れていた。一緒に頑張ろうと励ました。（重要度: 0.8）
- 先週: ユーザーが昇進を喜んでいた。一緒に祝った。（重要度: 0.9）
```

## Frontend Changes (LiveAPIDemo.jsx)

1. **user_id**: Generate UUID on first visit, store in `localStorage("user_id")`.
2. **Setup message**: Include `user_id` field.
3. **Session end**: When disconnect button is pressed (or connection closes normally), POST the current `messages` array to `/memory/save`. Run in background — do not block UI.
4. **No major UI changes** required.

## Backend Dependencies to Add

```
google-cloud-firestore>=2.19.0
google-cloud-aiplatform>=1.38.0   # already present; used for Vertex AI embeddings
```

Firestore vector search requires the `google-cloud-firestore` client v2.16+.

## Firestore Index

A vector index must be created on the `embedding` field for each persona sub-collection to enable `find_nearest` queries:

```bash
# Created via gcloud or Firestore console
# Collection: memories/{user_id}/{persona}
# Field: embedding
# Dimensions: 768
# Distance measure: COSINE
```

## Rollout

1. Enable Firestore in GCP project (if not already enabled)
2. Create vector index
3. Add memory endpoints to server.py
4. Modify setup message handling to inject memories
5. Update frontend to send user_id and save memories on disconnect
6. Redeploy backend and frontend

## Out of Scope

- Memory deletion / management UI
- Cross-persona memory sharing
- Per-user auth (UUID device identity is sufficient)
