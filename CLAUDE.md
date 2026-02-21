# CLAUDE.md — コーディング規則

このファイルはClaude Codeが読み込むプロジェクト固有の指示書です。
**コードを書く際は必ずこの規則に従ってください。**

---

## 1. アーキテクチャ原則：DDD 4層構造

このプロジェクトはドメイン駆動設計 (DDD) に基づく4層アーキテクチャを採用しています。
詳細は `ARCHITECTURE.md` を参照してください。

```
Presentation  →  Application  →  Domain  ←  Infrastructure
```

**依存の方向は内側のみ。外側のレイヤーへの参照は禁止。**

---

## 2. 機能分離の規則（レイヤー規則）

新しいコードを書く際は、**必ず適切なレイヤーに配置**してください。

### Domain層 (`domain/` / `src/domain/`)

**配置するもの:**
- エンティティ（Entity）: `MemoryRecord`, `Conversation`, `UserObservation`
- 値オブジェクト（Value Object）: `EmotionLevel`, `StatusKey`, `Importance`, `PersonaType`
- リポジトリインターフェース（抽象クラス/interface）: `MemoryRepository`
- ドメインサービス: `EmotionClassificationService`, `MemoryFormatService`

**絶対に書いてはいけないもの:**
- `import aiohttp`, `import chromadb`, `import google.auth` など外部ライブラリへの依存
- HTTP リクエスト、データベース操作、ファイルI/O
- React コンポーネント、DOM 操作
- `fetch()`, `websocket`, `localStorage` などブラウザAPI

```python
# ✅ 正しい: ドメインは純粋なPython/JSのみ
@dataclass
class MemoryRecord:
    summary: str
    importance: float

# ❌ 禁止: ドメインからインフラを呼ぶ
import chromadb  # ← Domain層に書いてはいけない
```

---

### Application層 (`application/` / `src/application/`)

**配置するもの:**
- ユースケース（Use Case）: `AnalyzeUserStateUseCase`, `SaveConversationMemoryUseCase`
- DTO（Data Transfer Object）: `SaveMemoryRequest`, `AnalyzeFrameResponse`
- Portインターフェース（`src/application/ports/`）: `AIConversationPort`, `MemoryPort`

**絶対に書いてはいけないもの:**
- ChromaDB / Vertex AI / Gemini APIへの直接呼び出し
- React コンポーネント・DOM 操作
- データベース接続・ファイル操作
- ビジネスロジック（それはDomainに書く）

```python
# ✅ 正しい: ユースケースはドメインとインフラを組み合わせる
class SaveConversationMemoryUseCase:
    def __init__(self, repo: MemoryRepository, auth: AuthService):
        ...  # 依存はインターフェース経由で注入

# ❌ 禁止: ユースケースに直接インフラを書く
class SaveConversationMemoryUseCase:
    def __init__(self):
        self.client = chromadb.PersistentClient(...)  # ← Application層に書いてはいけない
```

---

### Infrastructure層 (`infrastructure/` / `src/infrastructure/`)

**配置するもの:**
- リポジトリの具体実装: `ChromaDBMemoryRepository`
- 外部API クライアント: `GoogleAuthService`, `VertexAIEmbeddingService`, `GeminiProxy`
- Port の具体実装（JS）: `GeminiLiveAPIAdapter`, `BackendAPIClient`
- メディア操作: `AudioStreamer`, `VideoStreamer`

**規則:**
- 必ず Domain のインターフェース（Repository / Port）を実装すること
- Infrastructure から Application / Presentation を参照しないこと

```python
# ✅ 正しい: DomainインターフェースをInfraで実装
class ChromaDBMemoryRepository(MemoryRepository):  # ← 抽象クラスを継承
    async def save(self, record: MemoryRecord, ...) -> str:
        collection.add(...)  # ChromaDB操作はここだけ

# ❌ 禁止: ユースケースの中でDBに直接アクセス
class SaveConversationMemoryUseCase:
    async def execute(self):
        collection = chromadb.PersistentClient(...)  # ← Infrastructure層で書くべき
```

---

### Presentation層 (`server.py` の HTTP/WSハンドラ / `src/presentation/`)

**配置するもの:**
- HTTP/WebSocket ハンドラ: `ws_handler`, `handle_analyze_frame`, `handle_memory_save`
- React コンポーネント・ページ
- 入力バリデーション（フォーマットチェックのみ）
- レスポンス整形

**規則:**
- ビジネスロジックを書かない。ユースケースに委譲すること
- ドメインオブジェクトを直接生成しない
- DBやAPIを直接呼ばない

```python
# ✅ 正しい: Presentationはユースケースを呼ぶだけ
async def handle_memory_save(request):
    req = SaveMemoryRequest(...)
    result = await use_case.execute(req)  # ← ユースケースに委譲
    return web.json_response({"memory_id": result.memory_id})

# ❌ 禁止: ハンドラの中にビジネスロジックを書く
async def handle_memory_save(request):
    transcript_text = "\n".join(...)  # ← これはユースケースで書くべき
    async with aiohttp.ClientSession() as session:  # ← これはInfrastructureで書くべき
        ...
```

---

## 3. 機能別コーディングの規則（コンテキスト規則）

コードは**境界づけられたコンテキスト (Bounded Context) 単位**で整理します。
新機能を追加する際は、**どのコンテキストに属するか**を最初に決めてから実装してください。

### 現在のコンテキスト一覧

| コンテキスト | ディレクトリ | 責務 |
|---|---|---|
| **Conversation** | `domain/conversation/` `src/domain/conversation/` | 会話セッション管理・トランスクリプト |
| **Memory** | `domain/memory/` `src/domain/memory/` | 過去会話の永続化・意味的な想起 |
| **UserObservation** | `domain/user_observation/` `src/domain/userState/` | カメラ解析・感情検出・発話判断 |
| **Persona** | `domain/persona/` `src/domain/persona/` | AIキャラクター設定管理 |

### コンテキストをまたぐ参照の禁止

**異なるコンテキストのDomainオブジェクトを直接参照しないこと。**
コンテキスト間の連携はApplication層のユースケースで行います。

```python
# ❌ 禁止: Memoryコンテキストが直接Conversationを参照
class MemoryRecord:
    conversation: Conversation  # ← コンテキスト越境参照

# ✅ 正しい: Application層でコンテキストを繋ぐ
class SaveConversationMemoryUseCase:
    async def execute(self, request: SaveMemoryRequest):
        # ConversationコンテキストのデータをMemoryコンテキストに変換
        record = MemoryRecord(summary=..., emotion=...)
```

### 新しいコンテキストを追加する手順

新しい機能ドメインが必要な場合、以下の順で作成してください。

```
1. domain/<new_context>/         # エンティティ・値オブジェクト・インターフェース
2. application/                  # ユースケース・DTO
3. infrastructure/               # 具体実装（DB・外部API）
4. Presentation (server.py/JSX)  # ハンドラ・コンポーネント
```

**既存コンテキストのディレクトリに異なるドメインのコードを追加しないこと。**

---

## 4. ファイル配置チェックリスト

コードを書く前に以下を確認してください。

### 新しいクラス・関数を作る前に

- [ ] どのレイヤーに属するか？（Domain / Application / Infrastructure / Presentation）
- [ ] どのコンテキストに属するか？（Conversation / Memory / UserObservation / Persona / 新規）
- [ ] ファイルを作る場所は正しいか？
- [ ] 外部ライブラリをインポートしているなら、Infrastructure層か？
- [ ] HTTPリクエストを送るなら、Infrastructure層か？
- [ ] ビジネスロジックを書くなら、Domain層かApplication層か？

### コードレビューの観点

- [ ] Domain層に `import aiohttp / chromadb / google.auth / fetch()` がないか
- [ ] Application層にDB操作・HTTP通信が直接書かれていないか
- [ ] Presentation層にビジネスロジック（条件分岐・計算）が書かれていないか
- [ ] コンテキストをまたぐDomain直接参照がないか
- [ ] 新しいユースケースはApplicationに、新しいドメインロジックはDomainに書かれているか

---

## 5. 命名規則

### Python (バックエンド)

| 種別 | 命名規則 | 例 |
|---|---|---|
| エンティティ | `PascalCase` | `MemoryRecord`, `UserObservation` |
| 値オブジェクト | `PascalCase` | `EmotionLevel`, `StatusKey` |
| ユースケース | `PascalCase + UseCase` | `SaveConversationMemoryUseCase` |
| リポジトリ抽象 | `PascalCase + Repository` | `MemoryRepository` |
| リポジトリ実装 | `技術名 + Repository` | `ChromaDBMemoryRepository` |
| サービス | `PascalCase + Service` | `GoogleAuthService`, `MemoryFormatService` |
| DTO | `PascalCase + Request/Response` | `SaveMemoryRequest`, `AnalyzeFrameResponse` |

### JavaScript (フロントエンド)

| 種別 | 命名規則 | 例 |
|---|---|---|
| エンティティ | `PascalCase.js` | `Conversation.js`, `MemoryRecord.js` |
| 値オブジェクト | `PascalCase.js` | `EmotionLevel.js`, `PersonaType.js` |
| ユースケース | `PascalCase + UseCase.js` | `AnalyzeUserStateUseCase.js` |
| Port（インターフェース） | `PascalCase + Port.js` | `AIConversationPort.js` |
| Adapter（実装） | `PascalCase + Adapter.js` | `GeminiLiveAPIAdapter.js` |
| Reactコンポーネント | `PascalCase.jsx` | `ConversationPanel.jsx` |

---

## 6. やってはいけないこと（Anti-patterns）

### ❌ God Object / God Component
1500行超の単一ファイル（例: `LiveAPIDemo.jsx`）に複数の責務を詰め込まない。
機能ごとにクラス・コンポーネントを分割すること。

### ❌ レイヤー越境
```python
# 禁止: server.py（Presentation）から直接ChromaDBを操作
async def handle_memory_save(request):
    client = chromadb.PersistentClient(...)  # ← Infrastructure層で書くべき
```

### ❌ コンテキスト混在
```python
# 禁止: memoryのファイルにuserObservationのロジックを書く
# domain/memory/memory_record.py
class MemoryRecord:
    def classify_emotion(self): ...  # ← これはUserObservationコンテキストの責務
```

### ❌ ユースケースのバイパス
```jsx
// 禁止: コンポーネントから直接バックエンドAPIを呼ぶ
async function saveMemory() {
    await fetch('/memory/save', ...)  // ← BackendAPIClient → UseCase 経由で呼ぶべき
}
```

### ❌ ビジネスロジックのPresentation混入
```python
# 禁止: ハンドラの中に感情判定ロジックを書く
async def handle_analyze_frame(request):
    if emotion in ["困っている", "悲しい"]:  # ← EmotionClassificationServiceで書くべき
        level = "HIGH"
```

---

## 7. 既存コードとの関係

現在、`src/utils/` と `memory-mcp/` には移行前の既存コードが残っています。

- **既存コードには手を加えない**（後方互換を維持）
- **新機能は必ずDDDレイヤー構造に従って追加**
- 既存コードのロジックを移植する場合は適切なレイヤーに配置し直す
- `src/utils/user-state-manager.js` の後継は `src/domain/userState/SpeechDecisionService.js`
- `memory-mcp/src/memory_mcp/store.py` の後継は `infrastructure/chromadb_repository.py`
