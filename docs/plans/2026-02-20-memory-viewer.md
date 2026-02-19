# Memory Viewer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 設定メニューの「記憶を見る」ボタンから過去のセッション記憶を一覧表示するモーダルを追加する。

**Architecture:** バックエンドに `GET /memory/list` エンドポイントを追加し、`memory_mcp.store.list_recent_memories` を呼び出して JSON で返す。フロントエンドは設定ドロップダウンにボタンを追加し、クリックでモーダルを開いてカードリストを表示する。

**Tech Stack:** Python/aiohttp (server.py), React/JSX (LiveAPIDemo.jsx), chromadb (memory_mcp.store)

---

### Task 1: Backend — `GET /memory/list` endpoint

**Files:**
- Modify: `server.py` — `handle_memory_list` 関数の追加 + ルート登録
- Test: `tests/test_memory_list.py` (新規)

**Background: server.py の既存パターン**

全 HTTP エンドポイントは同じ構造に従っている:
1. CORS headers を dict で定義
2. OPTIONS メソッドは即 `web.Response(headers=headers)` で返す
3. `Authorization: Bearer <password>` ヘッダーで `verify_app_password()` を呼ぶ
4. クエリパラメータまたはボディを読む
5. `memory_store.*` を await 呼び出し
6. `web.json_response(result, headers=headers)` で返す

`main()` の `app.router.add_*` でルート登録する（`server.py` 末尾付近 619-623 行）。

---

**Step 1: Write the failing test**

`tests/test_memory_list.py` を新規作成:

```python
"""Tests for GET /memory/list endpoint."""

import pytest
from unittest.mock import AsyncMock, patch
from aiohttp.test_utils import TestClient, TestServer
from aiohttp import web
import server


@pytest.fixture
def app():
    a = web.Application()
    a.router.add_get("/memory/list", server.handle_memory_list)
    a.router.add_options("/memory/list", server.handle_memory_list)
    return a


@pytest.fixture
async def client(aiohttp_client, app):
    return await aiohttp_client(app)


FAKE_MEMORIES = [
    {"summary": "楽しく話した", "emotion": "楽しそう", "importance": 0.8, "days_ago": 3},
    {"summary": "疲れていた", "emotion": "疲れている", "importance": 0.6, "days_ago": 7},
]


class TestHandleMemoryList:
    async def test_returns_memories(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"), \
             patch("server.memory_store.list_recent_memories", new=AsyncMock(return_value=FAKE_MEMORIES)):
            resp = await client.get(
                "/memory/list?user_id=u1&persona=bright_friend",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 200
        data = await resp.json()
        assert data["memories"] == FAKE_MEMORIES

    async def test_missing_user_id_returns_400(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?persona=bright_friend",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 400

    async def test_missing_persona_returns_400(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?user_id=u1",
                headers={"Authorization": "Bearer pw"},
            )
        assert resp.status == 400

    async def test_wrong_password_returns_401(self, client):
        with patch.object(server, "APP_PASSWORD", "pw"):
            resp = await client.get(
                "/memory/list?user_id=u1&persona=bright_friend",
                headers={"Authorization": "Bearer wrong"},
            )
        assert resp.status == 401

    async def test_options_returns_200(self, client):
        resp = await client.options("/memory/list")
        assert resp.status == 200

    async def test_limit_param_passed_to_store(self, client):
        mock = AsyncMock(return_value=[])
        with patch.object(server, "APP_PASSWORD", "pw"), \
             patch("server.memory_store.list_recent_memories", new=mock):
            await client.get(
                "/memory/list?user_id=u1&persona=bright_friend&limit=5",
                headers={"Authorization": "Bearer pw"},
            )
        mock.assert_called_once_with("u1", "bright_friend", 5)
```

**Step 2: Run the test to verify it fails**

```bash
pytest tests/test_memory_list.py -v
```

Expected: `AttributeError: module 'server' has no attribute 'handle_memory_list'` (関数未実装のため)

**Step 3: Implement `handle_memory_list` in server.py**

`handle_memory_save` 関数 (server.py:543) の直前に以下を挿入:

```python
async def handle_memory_list(request):
    """HTTP endpoint to list recent memories for a user+persona."""
    cors_origin = os.environ.get("CORS_ORIGIN", "*")
    headers = {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }

    if request.method == "OPTIONS":
        return web.Response(headers=headers)

    auth_header = request.headers.get("Authorization", "")
    password = auth_header[7:] if auth_header.startswith("Bearer ") else ""
    if not verify_app_password(password):
        return web.json_response({"error": "Unauthorized"}, status=401, headers=headers)

    user_id = request.rel_url.query.get("user_id", "").strip()
    persona = request.rel_url.query.get("persona", "").strip()
    limit = int(request.rel_url.query.get("limit", "10"))

    if not user_id or not persona:
        return web.json_response(
            {"error": "user_id and persona are required"}, status=400, headers=headers
        )

    try:
        memories = await memory_store.list_recent_memories(user_id, persona, limit)
        return web.json_response({"memories": memories}, headers=headers)
    except Exception as e:
        print(f"Error in handle_memory_list: {e}")
        return web.json_response({"error": "Internal server error"}, status=500, headers=headers)
```

**Step 4: Register the route in `main()` (server.py:622-623 付近)**

`app.router.add_post("/memory/save", handle_memory_save)` の直前に追加:

```python
    app.router.add_get("/memory/list", handle_memory_list)
    app.router.add_options("/memory/list", handle_memory_list)
```

**Step 5: Install pytest-aiohttp (テスト実行に必要)**

```bash
/tmp/test-env-312/bin/pip install pytest-aiohttp
```

**Step 6: Run the tests**

```bash
/tmp/test-env-312/bin/pytest tests/test_memory_list.py -v
```

Expected: 6 tests PASS

Also run the full test suite to confirm no regression:

```bash
/tmp/test-env-312/bin/pytest tests/ -v
```

Expected: all existing tests still pass.

**Step 7: Commit**

```bash
git add server.py tests/test_memory_list.py
git commit -m "feat: add GET /memory/list endpoint"
```

---

### Task 2: Frontend — Memory viewer UI

**Files:**
- Modify: `src/components/LiveAPIDemo.jsx`

フロントエンドのテストは JSX コンポーネントのインタラクションテストになるため、既存プロジェクトのパターン（純粋関数のみテスト）と一致させ、ここでは追加しない。

**Background: LiveAPIDemo.jsx の既存パターン**

- State 定義は `forwardRef` コールバック内の先頭部分 (190行〜)
- Modal state: `modalVisible` (209行), `modalContent` (210行) — 既存 tool-use モーダル用
- Settings dropdown: `config-dropdown` クラスの `div` (926行〜)、 先頭は `<div className="control-group"><h3>接続設定</h3>` (928行)
- `proxyUrl` state で baseUrl を構築する fetch パターン (516行) を使う
- `appPassword` state が Authorization ヘッダーに入る (521行)
- 既存モーダル overlay: `modal-overlay` / `modal-content` クラスを使用 (1282行〜)

---

**Step 1: Add state variables**

LiveAPIDemo.jsx の「Modal State」ブロック (208-213行) に以下を追加:

```jsx
    // Memories Modal State
    const [showMemoriesModal, setShowMemoriesModal] = useState(false);
    const [memoriesList, setMemoriesList] = useState([]);
    const [memoriesLoading, setMemoriesLoading] = useState(false);
```

**Step 2: Add `fetchMemories` function**

`saveMemory` 関数 (504行) の直後に追加:

```jsx
    const fetchMemories = async () => {
      setMemoriesLoading(true);
      try {
        const baseUrl = proxyUrl.replace("wss://", "https://").replace("ws://", "http://").replace("/ws", "");
        const response = await fetch(
          `${baseUrl}/memory/list?user_id=${encodeURIComponent(userId)}&persona=${encodeURIComponent(persona)}&limit=10`,
          { headers: { Authorization: `Bearer ${appPassword}` } }
        );
        if (!response.ok) {
          alert(`記憶の取得に失敗しました (${response.status})`);
          return;
        }
        const data = await response.json();
        setMemoriesList(data.memories || []);
        setShowMemoriesModal(true);
      } catch (e) {
        alert(`記憶の取得に失敗しました: ${e.message}`);
      } finally {
        setMemoriesLoading(false);
      }
    };
```

**Step 3: Add button to settings dropdown**

`config-dropdown` div の中の最初の `control-group` (928行、`<div className="control-group"><h3>接続設定</h3>`) の直前に挿入:

```jsx
                <div className="control-group">
                  <button
                    onClick={fetchMemories}
                    disabled={memoriesLoading}
                    style={{ width: "100%" }}
                  >
                    {memoriesLoading ? "読み込み中..." : "🧠 記憶を見る"}
                  </button>
                </div>
```

**Step 4: Add memories modal JSX**

既存 modal dialog ブロック (1281-1290行) の直後に追加:

```jsx
        {/* Memories Modal */}
        {showMemoriesModal && (
          <div className="modal-overlay" onClick={() => setShowMemoriesModal(false)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxHeight: "70vh", overflowY: "auto", minWidth: "320px" }}>
              <h2>🧠 過去の記憶</h2>
              {memoriesList.length === 0 ? (
                <p>まだ記憶がありません。</p>
              ) : (
                memoriesList.map((m, i) => {
                  const when = m.days_ago === 0 ? "今日" : m.days_ago === 1 ? "昨日" : `${m.days_ago}日前`;
                  return (
                    <div key={i} style={{ borderTop: i > 0 ? "1px solid #eee" : "none", paddingTop: i > 0 ? "0.75rem" : 0, marginTop: i > 0 ? "0.75rem" : 0 }}>
                      <div style={{ fontSize: "0.8rem", color: "#888", marginBottom: "0.25rem" }}>
                        📌 {when}　<span style={{ background: "#f0f0f0", borderRadius: "4px", padding: "1px 6px" }}>{m.emotion}</span>
                      </div>
                      <div>{m.summary}</div>
                    </div>
                  );
                })
              )}
              <button onClick={() => setShowMemoriesModal(false)} style={{ marginTop: "1rem" }}>閉じる</button>
            </div>
          </div>
        )}
```

**Step 5: Run frontend tests**

```bash
npm run test
```

Expected: all existing tests pass (変更は state/JSX のみで既存ロジック不変)

**Step 6: Manual smoke test (optional)**

1. `python server.py` を起動 (別ターミナル)
2. `npm run dev` を起動
3. ブラウザで `http://localhost:5173` を開く
4. パスワードを入力してログイン
5. 「設定 ▾」をクリック → 「🧠 記憶を見る」ボタンが表示されることを確認
6. ボタンをクリック → モーダルが開き記憶リスト（または「まだ記憶がありません」）が表示されることを確認

**Step 7: Commit**

```bash
git add src/components/LiveAPIDemo.jsx
git commit -m "feat: add memory viewer modal in settings menu"
```
