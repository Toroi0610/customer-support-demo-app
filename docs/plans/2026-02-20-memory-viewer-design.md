# Memory Viewer Design

## Goal

設定メニューから過去の記憶を一覧表示できるモーダルを追加する。

## Architecture

既存の ChromaDB メモリストア (`memory_mcp.store.list_recent_memories`) を使い、バックエンドに `GET /memory/list` エンドポイントを追加する。フロントエンドの設定ドロップダウンにボタンを追加し、クリックで専用モーダルを表示する。

## Tech Stack

- Backend: Python/aiohttp (server.py) + memory_mcp.store
- Frontend: React (LiveAPIDemo.jsx)

---

## Design

### Backend

**New endpoint:** `GET /memory/list`

- Query params: `user_id` (required), `persona` (required), `limit` (optional, default 10)
- Auth: `APP_PASSWORD` ヘッダー（既存パターンと同様）
- Calls: `await memory_store.list_recent_memories(user_id, persona, limit)`
- Response: `{"memories": [{"summary": "...", "emotion": "...", "importance": 0.8, "days_ago": 3}, ...]}`
- Error: `user_id` or `persona` 未指定は 400、サーバーエラーは 500

### Frontend

**State additions to LiveAPIDemo.jsx:**
- `showMemoriesModal` (bool, default false)
- `memoriesList` (array, default [])
- `memoriesLoading` (bool, default false)

**New function `fetchMemories()`:**
- Builds URL with `user_id`, `persona`, `limit=10`
- Sets `memoriesLoading = true`, fetches endpoint
- On success: `memoriesList = data.memories`, `showMemoriesModal = true`
- On error: shows alert

**Settings dropdown addition:**
- 設定ドロップダウン (`config-dropdown`) の先頭に「🧠 記憶を見る」ボタン

**New modal JSX:**
- `showMemoriesModal` フラグで制御（既存 `modalVisible` とは独立）
- カードリスト: days_ago ラベル・emotion バッジ・summary テキスト
- 記憶ゼロ時: 「まだ記憶がありません」メッセージ
- 「閉じる」ボタン

### Data Flow

```
クリック
  → fetchMemories()
  → GET /memory/list?user_id=...&persona=...&limit=10
  → list_recent_memories(user_id, persona, limit=10)  [ChromaDB]
  → JSON レスポンス
  → モーダル表示
```
